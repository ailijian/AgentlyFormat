"""流式JSON解析器模块

基于Agently框架的StreamingJSONParser优化实现，
用于异步逐块解析流式JSON数据，支持增量更新和事件通知。

核心稳定性增强功能：
- 跨块缓冲与软裁剪：环形缓冲保留最近 N 字节，括号/引号平衡统计
- 结构化差分引擎：幂等事件派发，事件去重与合并
- chunk 超时自适应与 backoff 机制
- 增量 Schema 验证器集成（可选启用）
- 扩展事件字段：seq、path_hash、confidence、repair_trace、timing
- 增强统计信息：TTF-FIELD、完成时间、修复次数等
"""

import json
import json5
import asyncio
import hashlib
import time
from typing import Any, Dict, List, Optional, Callable, AsyncGenerator, Union
from datetime import datetime, timedelta
from dataclasses import dataclass, field
import uuid
import copy
from collections import deque
import re

from ..types.events import (
    StreamingEvent, EventType, EventData,
    create_delta_event, create_done_event, create_error_event
)
from .path_builder import PathBuilder, PathStyle
from .json_completer import JSONCompleter, CompletionStrategy
from .diff_engine import StructuredDiffEngine, DiffMode, CoalescingConfig, create_diff_engine
from .schemas import SchemaValidator, ValidationContext, ValidationLevel
from ..exceptions import (
    AgentlyFormatError, ParsingError, ValidationError, FieldFilteringError,
    TimeoutError, BufferOverflowError, ErrorHandler, ErrorSeverity, ErrorCategory
)
from .performance_optimizer import PerformanceOptimizer
from .memory_manager import MemoryManager


@dataclass
class ChunkBuffer:
    """跨块缓冲器
    
    实现环形缓冲保留最近 N 字节，支持括号/引号平衡统计和软裁剪。
    """
    max_size: int = 8192  # 最大缓冲区大小
    buffer: deque = field(default_factory=deque)
    total_size: int = 0
    bracket_balance: Dict[str, int] = field(default_factory=lambda: {
        '{': 0, '}': 0, '[': 0, ']': 0, '"': 0, "'": 0
    })
    in_string: bool = False
    string_char: Optional[str] = None
    escape_next: bool = False
    
    def add_chunk(self, chunk: str) -> str:
        """添加新块到缓冲区
        
        Args:
            chunk: 新的数据块
            
        Returns:
            str: 完整的缓冲区内容
        """
        # 更新括号/引号平衡统计
        self._update_balance_stats(chunk)
        
        # 添加到缓冲区
        self.buffer.append(chunk)
        self.total_size += len(chunk)
        
        # 如果超过最大大小，移除旧块
        while self.total_size > self.max_size and self.buffer:
            old_chunk = self.buffer.popleft()
            self.total_size -= len(old_chunk)
        
        return self.get_content()
    
    def get_content(self) -> str:
        """获取缓冲区完整内容"""
        return ''.join(self.buffer)
    
    def get_soft_trimmed_content(self) -> str:
        """获取软裁剪后的内容
        
        尾部不完整的 token 会被延迟拼接，确保 JSON 解析的完整性。
        智能分块：在JSON结构边界处分块，避免破坏语法结构。
        """
        content = self.get_content()
        
        # 如果内容为空，直接返回
        if not content.strip():
            return content
        
        # 如果在字符串中，保留到字符串结束
        if self.in_string:
            return content
        
        # 智能分块：查找安全的分块点
        safe_content = self._find_safe_chunk_boundary(content)
        return safe_content
    
    def _update_balance_stats(self, chunk: str):
        """更新括号/引号平衡统计"""
        for char in chunk:
            if self.escape_next:
                self.escape_next = False
                continue
            
            if char == '\\':
                self.escape_next = True
                continue
            
            if self.in_string:
                if char == self.string_char:
                    self.in_string = False
                    self.string_char = None
                    self.bracket_balance[char] += 1
            else:
                if char in ['"', "'"]:
                    self.in_string = True
                    self.string_char = char
                    self.bracket_balance[char] += 1
                elif char in ['{', '[']:
                    self.bracket_balance[char] += 1
                elif char in ['}', ']']:
                    self.bracket_balance[char] += 1
    
    def _is_balanced(self) -> bool:
        """检查括号是否平衡"""
        return (
            self.bracket_balance['{'] == self.bracket_balance['}'] and
            self.bracket_balance['['] == self.bracket_balance[']'] and
            self.bracket_balance['"'] % 2 == 0 and
            self.bracket_balance["'"] % 2 == 0
        )
    
    def _find_safe_chunk_boundary(self, content: str) -> str:
        """查找安全的分块边界
        
        智能分块策略：
        1. 在完整的JSON对象/数组边界处分块
        2. 避免在字符串中间分块
        3. 确保括号平衡
        4. 保留完整的键值对
        """
        if not content.strip():
            return content
            
        # 查找最后一个安全的分块点
        safe_pos = self._find_last_safe_position(content)
        
        # 如果找不到安全位置，返回完整内容而不是强制分块
        # 这样可以避免破坏JSON结构，让后续的JSON解析器处理完整的内容
        if safe_pos <= 0:
            return content
            
        return content[:safe_pos]
    
    def _find_last_safe_position(self, content: str) -> int:
        """查找最后一个安全的分块位置"""
        brace_count = 0
        bracket_count = 0
        in_string = False
        string_char = None
        escape_next = False
        last_safe_pos = 0
        
        for i, char in enumerate(content):
            if escape_next:
                escape_next = False
                continue
            
            if char == '\\':
                escape_next = True
                continue
            
            if in_string:
                if char == string_char:
                    in_string = False
                    string_char = None
            else:
                if char in ['"', "'"]:
                    in_string = True
                    string_char = char
                elif char == '{':
                    brace_count += 1
                elif char == '}':
                    brace_count -= 1
                    # 完整对象结束，这是一个安全的分块点
                    if brace_count == 0 and bracket_count == 0:
                        last_safe_pos = i + 1
                elif char == '[':
                    bracket_count += 1
                elif char == ']':
                    bracket_count -= 1
                    # 完整数组结束，这是一个安全的分块点
                    if brace_count == 0 and bracket_count == 0:
                        last_safe_pos = i + 1
                elif char == ',' and brace_count <= 1 and bracket_count == 0:
                    # 在对象的顶层逗号处，这也是一个相对安全的分块点
                    last_safe_pos = i + 1
        
        return last_safe_pos
    
    def _is_in_string_at_position(self, content: str, pos: int) -> bool:
        """检查指定位置是否在字符串内部"""
        in_string = False
        string_char = None
        escape_next = False
        
        for i, char in enumerate(content[:pos + 1]):
            if escape_next:
                escape_next = False
                continue
            
            if char == '\\':
                escape_next = True
                continue
            
            if in_string:
                if char == string_char:
                    in_string = False
                    string_char = None
            else:
                if char in ['"', "'"]:
                    in_string = True
                    string_char = char
        
        return in_string
    
    def _find_last_complete_token(self, content: str) -> str:
        """查找最后一个完整的 JSON token（保留用于兼容性）"""
        return self._find_safe_chunk_boundary(content)
    
    def clear(self):
        """清空缓冲区"""
        self.buffer.clear()
        self.total_size = 0
        self.bracket_balance = {'{': 0, '}': 0, '[': 0, ']': 0, '"': 0, "'": 0}
        self.in_string = False
        self.string_char = None
        self.escape_next = False


@dataclass
class AdaptiveTimeout:
    """自适应超时机制
    
    实现 chunk 超时自适应与 backoff 机制。
    """
    base_timeout: float = 5.0  # 基础超时时间（秒）
    max_timeout: float = 30.0  # 最大超时时间（秒）
    backoff_factor: float = 1.5  # 退避因子
    success_decay: float = 0.9  # 成功时的衰减因子
    current_timeout: float = field(init=False)
    consecutive_timeouts: int = 0
    consecutive_successes: int = 0
    last_chunk_time: Optional[datetime] = None
    
    def __post_init__(self):
        self.current_timeout = self.base_timeout
    
    def on_chunk_received(self):
        """收到块时调用"""
        self.last_chunk_time = datetime.now()
        self.consecutive_successes += 1
        self.consecutive_timeouts = 0
        
        # 成功时逐渐降低超时时间
        if self.consecutive_successes > 3:
            self.current_timeout = max(
                self.base_timeout,
                self.current_timeout * self.success_decay
            )
    
    def on_timeout(self):
        """超时时调用"""
        self.consecutive_timeouts += 1
        self.consecutive_successes = 0
        
        # 超时时增加超时时间
        self.current_timeout = min(
            self.max_timeout,
            self.current_timeout * self.backoff_factor
        )
    
    def is_timeout(self) -> bool:
        """检查是否超时"""
        if self.last_chunk_time is None:
            return False
        
        elapsed = (datetime.now() - self.last_chunk_time).total_seconds()
        return elapsed > self.current_timeout
    
    def get_timeout_remaining(self) -> float:
        """获取剩余超时时间"""
        if self.last_chunk_time is None:
            return self.current_timeout
        
        elapsed = (datetime.now() - self.last_chunk_time).total_seconds()
        return max(0, self.current_timeout - elapsed)


@dataclass
class EnhancedStats:
    """增强统计信息
    
    包含 TTF-FIELD（Time To First Field）、完成时间、修复次数等。
    """
    session_id: str
    start_time: datetime = field(default_factory=datetime.now)
    first_field_time: Optional[datetime] = None
    completion_time: Optional[datetime] = None
    total_chunks: int = 0
    processed_chunks: int = 0
    failed_chunks: int = 0
    repair_attempts: int = 0
    successful_repairs: int = 0
    validation_errors: int = 0
    timeout_events: int = 0
    buffer_overflows: int = 0
    json_decode_errors: int = 0
    json5_fallback_success: int = 0
    json5_fallback_errors: int = 0
    completion_errors: int = 0
    completion_success: int = 0
    completion_failures: int = 0
    event_generation_errors: int = 0
    total_parse_failures: int = 0
    field_completion_times: Dict[str, datetime] = field(default_factory=dict)
    
    def record_first_field(self):
        """记录第一个字段的时间"""
        if self.first_field_time is None:
            self.first_field_time = datetime.now()
    
    def record_field_completion(self, path: str):
        """记录字段完成时间"""
        self.field_completion_times[path] = time.time()
    
    def record_first_field(self):
        """记录第一个字段时间"""
        if not self.first_field_time:
            self.first_field_time = time.time()
    
    def record_completion(self):
        """记录会话完成时间"""
        self.completion_time = time.time()
    
    def get_ttf_field_ms(self) -> Optional[float]:
        """获取 TTF-FIELD（毫秒）"""
        if self.first_field_time is None:
            return None
        return (self.first_field_time - self.start_time).total_seconds() * 1000
    
    def get_total_duration_ms(self) -> Optional[float]:
        """获取总持续时间（毫秒）"""
        end_time = self.completion_time or datetime.now()
        return (end_time - self.start_time).total_seconds() * 1000
    
    def get_field_completion_time_ms(self, path: str) -> Optional[float]:
        """获取字段完成时间（毫秒）"""
        if path not in self.field_completion_times:
            return None
        return (self.field_completion_times[path] - self.start_time).total_seconds() * 1000


@dataclass
class ParsingState:
    """解析状态"""
    session_id: str
    current_data: Dict[str, Any] = field(default_factory=dict)
    previous_data: Dict[str, Any] = field(default_factory=dict)
    completed_fields: set = field(default_factory=set)
    parsing_paths: List[str] = field(default_factory=list)
    sequence_number: int = 0
    total_chunks: int = 0
    processed_chunks: int = 0
    start_time: datetime = field(default_factory=datetime.now)
    last_update_time: datetime = field(default_factory=datetime.now)
    errors: List[str] = field(default_factory=list)
    parsing_errors: List[str] = field(default_factory=list)
    
    # 新增字段
    chunk_buffer: ChunkBuffer = field(default_factory=ChunkBuffer)
    adaptive_timeout: AdaptiveTimeout = field(default_factory=AdaptiveTimeout)
    enhanced_stats: EnhancedStats = field(init=False)
    validation_context: Optional[ValidationContext] = None
    path_hashes: Dict[str, str] = field(default_factory=dict)  # 路径值哈希缓存
    
    def __post_init__(self):
        self.enhanced_stats = EnhancedStats(session_id=self.session_id)
    
    def increment_sequence(self) -> int:
        """递增序列号"""
        self.sequence_number += 1
        return self.sequence_number
    
    def update_timestamp(self):
        """更新时间戳"""
        self.last_update_time = datetime.now()
    
    def calculate_path_hash(self, path: str, value: Any) -> str:
        """计算路径值的哈希
        
        Args:
            path: 路径
            value: 值
            
        Returns:
            str: 哈希值
        """
        value_str = json.dumps(value, sort_keys=True, ensure_ascii=False)
        path_hash = hashlib.md5(f"{path}:{value_str}".encode('utf-8')).hexdigest()
        self.path_hashes[path] = path_hash
        return path_hash


@dataclass
class FieldFilter:
    """字段过滤器配置
    
    支持路径匹配和字段选择性输出功能。
    """
    enabled: bool = False
    include_paths: List[str] = field(default_factory=list)  # 包含的路径列表
    exclude_paths: List[str] = field(default_factory=list)  # 排除的路径列表
    mode: str = "include"  # "include" 或 "exclude"
    exact_match: bool = False  # 是否精确匹配路径
    performance_optimizer: Optional['PerformanceOptimizer'] = None  # 性能优化器引用
    
    def __post_init__(self):
        """初始化后验证配置
        
        Raises:
            FieldFilteringError: 当配置无效时
        """
        try:
            self._validate_configuration()
        except Exception as e:
            if isinstance(e, FieldFilteringError):
                raise
            raise FieldFilteringError(
                f"Failed to validate FieldFilter configuration: {str(e)}",
                severity=ErrorSeverity.HIGH
            ) from e
    
    def _validate_configuration(self):
        """验证字段过滤器配置
        
        Raises:
            FieldFilteringError: 当配置无效时
        """
        # 验证模式
        if self.mode not in ["include", "exclude"]:
            raise FieldFilteringError(
                f"Invalid mode '{self.mode}'. Must be 'include' or 'exclude'",
                severity=ErrorSeverity.HIGH
            )
        
        # 验证路径列表
        if not isinstance(self.include_paths, list):
            raise FieldFilteringError(
                "include_paths must be a list",
                severity=ErrorSeverity.HIGH
            )
        
        if not isinstance(self.exclude_paths, list):
            raise FieldFilteringError(
                "exclude_paths must be a list",
                severity=ErrorSeverity.HIGH
            )
        
        # 验证路径格式
        for path in self.include_paths + self.exclude_paths:
            if not isinstance(path, str):
                raise FieldFilteringError(
                    f"Path must be a string, got {type(path)}: {path}",
                    severity=ErrorSeverity.HIGH
                )
            
            if not path.strip():
                raise FieldFilteringError(
                    "Path cannot be empty or whitespace only",
                    severity=ErrorSeverity.HIGH
                )
        
        # 检查路径冲突
        if self.include_paths and self.exclude_paths:
            conflicts = set(self.include_paths) & set(self.exclude_paths)
            if conflicts:
                raise FieldFilteringError(
                    f"Paths cannot be both included and excluded: {conflicts}",
                    severity=ErrorSeverity.HIGH
                )
        
        # 如果启用但没有配置路径，发出警告
        if self.enabled and not self.include_paths and not self.exclude_paths:
            # 这里可以记录警告日志，但不抛出异常
            pass
    
    def should_include_path(self, path: str) -> bool:
        """判断路径是否应该包含在输出中
        
        Args:
            path: 要检查的路径
            
        Returns:
            bool: 是否应该包含
            
        Raises:
            FieldFilteringError: 当路径匹配过程中发生错误时
        """
        try:
            # 验证输入参数
            if not isinstance(path, str):
                raise FieldFilteringError(
                    f"Path must be a string, got {type(path)}: {path}",
                    field_path=str(path),
                    severity=ErrorSeverity.MEDIUM
                )
            
            if not self.enabled:
                return True
            
            # 支持同时使用include和exclude的组合过滤逻辑
            # 1. 如果有include_paths，首先检查路径是否在包含列表中
            if self.include_paths:
                if not self._path_matches(path, self.include_paths):
                    return False  # 不在包含列表中，直接排除
            
            # 2. 如果有exclude_paths，检查路径是否在排除列表中
            if self.exclude_paths:
                if self._path_matches(path, self.exclude_paths):
                    return False  # 在排除列表中，排除该路径
            
            # 3. 如果既没有include_paths也没有exclude_paths，默认包含
            if not self.include_paths and not self.exclude_paths:
                return True
            
            # 4. 通过了所有检查，包含该路径
            return True
            
        except FieldFilteringError:
            raise
        except Exception as e:
            raise FieldFilteringError(
                f"Error during path filtering for '{path}': {str(e)}",
                field_path=path,
                severity=ErrorSeverity.MEDIUM
            ) from e
    
    def _path_matches(self, path: str, patterns: List[str]) -> bool:
        """检查路径是否匹配任一模式
        
        参考agently的实现，改进路径匹配逻辑：
        1. 支持精确字段名匹配
        2. 支持数组索引后的字段匹配
        3. 支持嵌套路径匹配
        4. 支持通配符匹配
        
        Args:
            path: 要检查的路径
            patterns: 模式列表
            
        Returns:
            bool: 是否匹配
            
        Raises:
            FieldFilteringError: 当路径匹配过程中发生错误时
        """
        # 直接实现路径匹配逻辑，不使用性能优化器缓存
        # 因为性能优化器的缓存逻辑不支持同时处理include和exclude模式
        try:
            import re
            
            for pattern in patterns:
                try:
                    if self.exact_match:
                        if path == pattern:
                            return True
                    else:
                        # 1. 精确匹配完整路径
                        if path == pattern:
                            return True
                        
                        # 2. 通配符匹配 - 优先处理
                        if '*' in pattern:
                            if self._wildcard_match(path, pattern):
                                return True
                            # 特殊处理：对于 xxx.* 模式，也匹配 xxx 本身
                            if pattern.endswith('.*') and path == pattern[:-2]:
                                return True
                        
                        # 3. 字段名匹配：检查路径末尾是否为指定字段名
                        # 支持 .fieldname 和 [index].fieldname 格式
                        if path.endswith('.' + pattern):
                            return True
                        
                        # 4. 数组索引后的字段名匹配
                        # 匹配 xxx[数字].pattern 的格式，如 languages[0].description
                        if re.search(r'\[\d+\]\.' + re.escape(pattern) + r'$', path):
                            return True
                        
                        # 5. 根级数组元素字段匹配
                        # 匹配 pattern[数字].xxx 的格式，如 languages[0] 匹配 languages
                        if re.search(r'^' + re.escape(pattern) + r'\[\d+\]', path):
                            return True
                        
                        # 6. 嵌套字段匹配
                        # 如果pattern包含点，进行更精确的路径匹配
                        if '.' in pattern and '*' not in pattern:
                            # 支持部分路径匹配，如 languages.description 匹配 languages[0].description
                            pattern_parts = pattern.split('.')
                            path_normalized = re.sub(r'\[\d+\]', '', path)  # 移除数组索引
                            if path_normalized == '.'.join(pattern_parts):
                                return True
                        
                        # 7. 敏感信息字段匹配 - 特别处理包含敏感信息的字段名
                        # 检查路径中是否包含敏感信息模式
                        if pattern in path:
                            # 检查是否为完整的字段名匹配
                            # 例如：secret123 应该匹配 data.secret123 或 users[0].secret123
                            if ('.' + pattern in path or 
                                path.startswith(pattern) or 
                                ('[' in path and '].' + pattern in path)):
                                return True
                            
                except re.error as e:
                    raise FieldFilteringError(
                        f"Invalid regex pattern '{pattern}' for path '{path}': {str(e)}",
                        field_path=path,
                        severity=ErrorSeverity.MEDIUM
                    ) from e
                except Exception as e:
                    raise FieldFilteringError(
                        f"Error matching pattern '{pattern}' against path '{path}': {str(e)}",
                        field_path=path,
                        severity=ErrorSeverity.LOW
                    ) from e
                    
            return False
            
        except FieldFilteringError:
            raise
        except Exception as e:
            raise FieldFilteringError(
                f"Error during path matching for '{path}': {str(e)}",
                field_path=path,
                severity=ErrorSeverity.MEDIUM
            ) from e
    
    def _wildcard_match(self, path: str, pattern: str) -> bool:
        """简单的通配符匹配
        
        Args:
            path: 路径
            pattern: 模式（支持 * 通配符）
            
        Returns:
            bool: 是否匹配
            
        Raises:
            FieldFilteringError: 当通配符匹配过程中发生错误时
        """
        try:
            import re
            # 将通配符转换为正则表达式
            regex_pattern = pattern.replace("*", ".*")
            return bool(re.match(f"^{regex_pattern}$", path))
            
        except re.error as e:
            raise FieldFilteringError(
                f"Invalid wildcard pattern '{pattern}' for path '{path}': {str(e)}",
                field_path=path,
                severity=ErrorSeverity.MEDIUM
            ) from e
        except Exception as e:
            raise FieldFilteringError(
                f"Error during wildcard matching for pattern '{pattern}' and path '{path}': {str(e)}",
                field_path=path,
                severity=ErrorSeverity.LOW
            ) from e


class StreamingParser:
    """流式JSON解析器
    
    异步逐块解析流式JSON数据，维护解析状态，
    并为每个字段在结构构建过程中发出增量和完成事件。
    支持字段过滤功能，可以选择性输出特定字段。
    """
    
    def __init__(
        self,
        enable_completion: bool = True,
        completion_strategy: CompletionStrategy = CompletionStrategy.SMART,
        path_style: PathStyle = PathStyle.DOT,
        max_depth: int = 10,
        chunk_timeout: float = 5.0,
        enable_diff_engine: bool = True,
        diff_mode: str = "smart",
        coalescing_enabled: bool = True,
        coalescing_time_window_ms: int = 100,
        # 新增参数
        buffer_size: int = 8192,
        enable_schema_validation: bool = False,
        schema: Optional[Dict[str, Any]] = None,
        adaptive_timeout_enabled: bool = True,
        max_timeout: float = 30.0,
        backoff_factor: float = 1.5,
        # 字段过滤参数
        field_filter: Optional[FieldFilter] = None
    ):
        """初始化流式解析器
        
        Args:
            enable_completion: 是否启用JSON补全
            completion_strategy: JSON补全策略
            path_style: 路径风格
            max_depth: 最大解析深度
            chunk_timeout: 块处理超时时间
            enable_diff_engine: 是否启用差分引擎
            diff_mode: 差分模式（"conservative" 或 "smart"）
            coalescing_enabled: 是否启用事件合并
            coalescing_time_window_ms: 合并时间窗口（毫秒）
            buffer_size: 跨块缓冲区大小
            enable_schema_validation: 是否启用 Schema 验证
            schema: JSON Schema 定义
            adaptive_timeout_enabled: 是否启用自适应超时
            max_timeout: 最大超时时间
            backoff_factor: 超时退避因子
        """
        self.enable_completion = enable_completion
        self.completion_strategy = completion_strategy
        self.path_style = path_style
        self.max_depth = max_depth
        self.chunk_timeout = chunk_timeout
        self.enable_diff_engine = enable_diff_engine
        self.buffer_size = buffer_size
        self.enable_schema_validation = enable_schema_validation
        self.schema = schema
        self.adaptive_timeout_enabled = adaptive_timeout_enabled
        self.max_timeout = max_timeout
        self.backoff_factor = backoff_factor
        
        # 字段过滤器配置
        self.field_filter = field_filter or FieldFilter()
        
        # 性能优化器初始化
        self.performance_optimizer = PerformanceOptimizer(
            enable_string_optimization=True,
            enable_path_optimization=True,
            enable_memory_management=True,
            max_cache_size=1000
        )
        
        # 将性能优化器传递给字段过滤器
        self.field_filter.performance_optimizer = self.performance_optimizer
        
        # 内存管理器初始化
        self.memory_manager = MemoryManager(
            max_sessions=1000,
            session_timeout=3600,  # 1小时
            cleanup_interval=300,  # 5分钟
            memory_threshold_mb=500.0,
            enable_auto_gc=True
        )
        
        # 组件初始化
        self.path_builder = PathBuilder(path_style)
        self.json_completer = JSONCompleter(completion_strategy) if enable_completion else None
        
        # 差分引擎初始化
        if enable_diff_engine:
            self.diff_engine = create_diff_engine(
                mode=diff_mode,
                coalescing_enabled=coalescing_enabled,
                time_window_ms=coalescing_time_window_ms
            )
        else:
            self.diff_engine = None
        
        # Schema 验证器初始化
        if enable_schema_validation and schema:
            self.schema_validator = SchemaValidator(
                schema=schema,
                path_builder=self.path_builder
            )
        else:
            self.schema_validator = None
        
        # 解析状态
        self.parsing_states: Dict[str, ParsingState] = {}
        
        # 事件回调
        self.event_callbacks: Dict[EventType, List[Callable]] = {
            EventType.DELTA: [],
            EventType.DONE: [],
            EventType.ERROR: [],
            EventType.START: [],
            EventType.FINISH: [],
            EventType.PROGRESS: []
        }
        
        # 统计信息
        self.stats = {
            "total_sessions": 0,
            "active_sessions": 0,
            "completed_sessions": 0,
            "failed_sessions": 0,
            "total_events_emitted": 0,
            "total_chunks_processed": 0,
            "total_buffer_overflows": 0,
            "total_timeouts": 0,
            "total_repairs": 0,
            "total_validation_errors": 0
        }
    
    def create_session(self, session_id: Optional[str] = None) -> str:
        """创建新的解析会话
        
        Args:
            session_id: 可选的会话ID，如果不提供则自动生成
        
        Returns:
            str: 会话ID
        """
        if session_id is None:
            session_id = str(uuid.uuid4())
        
        # 创建解析状态
        state = ParsingState(session_id=session_id)
        
        # 配置缓冲区大小
        state.chunk_buffer.max_size = self.buffer_size
        
        # 配置自适应超时
        if self.adaptive_timeout_enabled:
            state.adaptive_timeout.base_timeout = self.chunk_timeout
            state.adaptive_timeout.max_timeout = self.max_timeout
            state.adaptive_timeout.backoff_factor = self.backoff_factor
        
        # 创建验证上下文
        if self.enable_schema_validation:
            state.validation_context = ValidationContext(
                session_id=session_id,
                sequence_number=0
            )
        
        self.parsing_states[session_id] = state
        
        # 注册会话到内存管理器
        self.memory_manager.register_session(session_id, state)
        
        self.stats["total_sessions"] += 1
        self.stats["active_sessions"] += 1
        return session_id
    
    def add_event_callback(self, event_type: EventType, callback: Callable):
        """添加事件回调
        
        Args:
            event_type: 事件类型
            callback: 回调函数
        """
        if event_type in self.event_callbacks:
            self.event_callbacks[event_type].append(callback)
    
    def remove_event_callback(self, event_type: EventType, callback: Callable):
        """移除事件回调
        
        Args:
            event_type: 事件类型
            callback: 回调函数
        """
        if event_type in self.event_callbacks and callback in self.event_callbacks[event_type]:
            self.event_callbacks[event_type].remove(callback)
    
    async def _emit_event(self, event: StreamingEvent):
        """发出事件
        
        Args:
            event: 流式事件
        """
        self.stats["total_events_emitted"] += 1
        
        # 调用注册的回调函数
        callbacks = self.event_callbacks.get(event.event_type, [])
        for callback in callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(event)
                else:
                    callback(event)
            except Exception as e:
                # 记录回调错误，但不中断处理
                print(f"Event callback error: {e}")
    
    async def parse_chunk(self, session_id: str, chunk: str, is_final: bool = False) -> List[StreamingEvent]:
        """解析JSON块
        
        Args:
            session_id: 会话ID
            chunk: JSON块
            is_final: 是否为最终块
            
        Returns:
            List[StreamingEvent]: 生成的事件列表
            
        Raises:
            ParsingError: 当解析过程中发生不可恢复的错误时
            ValidationError: 当输入验证失败时
            BufferOverflowError: 当缓冲区溢出时
        """
        # 初始化错误处理器
        error_handler = ErrorHandler()
        
        try:
            # 验证输入参数
            if not isinstance(session_id, str) or not session_id:
                raise ValidationError(
                    "Session ID must be a non-empty string",
                    severity=ErrorSeverity.HIGH
                )
            
            if not isinstance(chunk, str):
                raise ValidationError(
                    f"Chunk must be a string, got {type(chunk)}",
                    severity=ErrorSeverity.HIGH
                )
            
            if session_id not in self.parsing_states:
                raise ValidationError(
                    f"Session {session_id} not found",
                    severity=ErrorSeverity.HIGH
                )
            
            state = self.parsing_states[session_id]
            state.total_chunks += 1
            state.enhanced_stats.total_chunks += 1
            state.update_timestamp()
            
            # 记录块接收时间（用于自适应超时）
            if self.adaptive_timeout_enabled:
                state.adaptive_timeout.on_chunk_received()
            
            events = []
            start_time = time.time()
            
            try:
                # 添加块到缓冲区
                buffered_content = state.chunk_buffer.add_chunk(chunk)
                
                # 检查缓冲区是否溢出
                if state.chunk_buffer.total_size >= state.chunk_buffer.max_size:
                    self.stats["total_buffer_overflows"] += 1
                    raise BufferOverflowError(
                        f"Buffer overflow: size {state.chunk_buffer.total_size} exceeds limit {state.chunk_buffer.max_size}",
                        buffer_size=state.chunk_buffer.total_size,
                        max_size=state.chunk_buffer.max_size,
                        severity=ErrorSeverity.HIGH
                    )
                
                # 获取软裁剪后的内容进行解析
                content_to_parse = (
                    state.chunk_buffer.get_soft_trimmed_content() 
                    if not is_final 
                    else buffered_content
                )
                
                # 尝试解析当前内容
                parsed_data = await self._parse_json_chunk(content_to_parse, state)
                
                if parsed_data is not None:
                    # 记录第一个字段时间
                    if not state.enhanced_stats.first_field_time and parsed_data:
                        state.enhanced_stats.record_first_field()
                    
                    # 比较并生成事件
                    chunk_events = await self._compare_and_generate_events(state, parsed_data)
                    events.extend(chunk_events)
                    
                    # Schema 验证（如果启用）
                    if self.enable_schema_validation and self.schema_validator and state.validation_context:
                        validation_events = await self._validate_data(state, parsed_data)
                        events.extend(validation_events)
                    
                    # 更新状态
                    state.previous_data = copy.deepcopy(state.current_data)
                    state.current_data = parsed_data
                    state.processed_chunks += 1
                    state.enhanced_stats.processed_chunks += 1
                else:
                    # 解析失败，尝试错误恢复
                    try:
                        recovery_result = error_handler.attempt_recovery(
                            ParsingError(
                                "Failed to parse JSON chunk",
                                json_content=content_to_parse[:100],  # 只记录前100个字符
                                severity=ErrorSeverity.MEDIUM
                            )
                        )
                        
                        if recovery_result is not None:
                            # 恢复成功，继续处理
                            # recovery_result可能包含恢复的数据
                            pass
                        else:
                            # 恢复失败，生成错误事件
                            error_events = await self._handle_parsing_error(
                                state, session_id, content_to_parse, chunk, 
                                start_time, is_final, "Failed to parse JSON chunk"
                            )
                            events.extend(error_events)
                    except Exception:
                        # 恢复过程中出现异常，直接生成错误事件
                        error_events = await self._handle_parsing_error(
                            state, session_id, content_to_parse, chunk, 
                            start_time, is_final, "Failed to parse JSON chunk"
                        )
                        events.extend(error_events)
                
                # 更新统计信息
                self.stats["total_chunks_processed"] += 1
                
            except (BufferOverflowError, ValidationError, ParsingError) as e:
                # 记录特定类型的错误到会话状态
                error_message = f"Specific error in chunk processing: {str(e)}"
                if session_id in self.parsing_states:
                    state = self.parsing_states[session_id]
                    state.errors.append(error_message)
                else:
                    # 对于ValidationError "Session not found"，创建临时状态
                    temp_state = ParsingState(session_id)
                    temp_state.errors.append(error_message)
                    self.parsing_states[session_id] = temp_state
                raise
            except Exception as e:
                # 尝试错误恢复
                try:
                    recovery_result = error_handler.attempt_recovery(
                        ParsingError(
                            f"Unexpected error during chunk processing: {str(e)}",
                            json_content=chunk[:100],  # 只记录前100个字符
                            severity=ErrorSeverity.HIGH
                        )
                    )
                    
                    if recovery_result is not None:
                        # 恢复成功，继续处理
                        pass
                    else:
                        # 恢复失败，重新抛出异常
                        raise ParsingError(
                            f"Unrecoverable error during chunk processing: {str(e)}",
                            json_content=chunk[:100],
                            severity=ErrorSeverity.HIGH
                        ) from e
                except Exception:
                    # 恢复过程中出现异常，重新抛出原异常
                    raise ParsingError(
                        f"Unrecoverable error during chunk processing: {str(e)}",
                        json_content=chunk[:100],
                        severity=ErrorSeverity.HIGH
                    ) from e
        
        except Exception as e:
            # 处理最外层异常
            error_message = f"Unexpected error in chunk processing: {str(e)}"
            error_event = create_error_event(
                path="",
                error_type="processing_error",
                error_message=error_message,
                session_id=session_id,
                sequence_number=0,  # 使用默认序列号
                metadata={"error_type": type(e).__name__}
            )
            events = [error_event]
            
            # 将错误记录到会话状态中
            if session_id in self.parsing_states:
                state = self.parsing_states[session_id]
                state.errors.append(error_message)
            else:
                # 如果会话不存在，创建临时状态记录错误
                # 这种情况通常发生在ValidationError "Session not found"时
                temp_state = ParsingState(session_id)
                temp_state.errors.append(error_message)
                self.parsing_states[session_id] = temp_state
        
        # 检查超时
        try:
            if (self.adaptive_timeout_enabled and 
                session_id in self.parsing_states and 
                self.parsing_states[session_id].adaptive_timeout.is_timeout()):
                state = self.parsing_states[session_id]
                state.adaptive_timeout.on_timeout()
                self.stats["total_timeouts"] += 1
                
                timeout_event = create_error_event(
                    path="",
                    error_type="timeout_error",
                    error_message=f"Chunk processing timeout after {state.adaptive_timeout.current_timeout}s",
                    session_id=session_id,
                    sequence_number=state.increment_sequence(),
                    metadata={
                        "timeout_duration": state.adaptive_timeout.current_timeout,
                        "consecutive_timeouts": state.adaptive_timeout.consecutive_timeouts
                    }
                )
                if 'events' not in locals():
                    events = []
                events.append(timeout_event)
        except Exception as e:
            # 超时检查错误
            error_event = create_error_event(
                path="",
                error_type="timeout_check_error",
                error_message=f"Error during timeout check: {str(e)}",
                session_id=session_id,
                sequence_number=0
            )
            if 'events' not in locals():
                events = []
            events.append(error_event)
        
        # 发出所有事件
        for event in events:
            await self._emit_event(event)
        
        return events
    
    def _check_and_handle_timeout(self, state: ParsingState) -> List[StreamingEvent]:
        """检查并处理超时事件
        
        Args:
            state: 解析状态
            
        Returns:
            List[StreamingEvent]: 超时事件列表
        """
        if not self.adaptive_timeout_enabled:
            return []
        
        events = []
        current_time = time.time()
        
        # 检查是否超时
        if state.adaptive_timeout.is_timeout(current_time):
            # 生成超时事件
            timeout_event = create_error_event(
                path="",
                error_type="chunk_timeout",
                error_message=f"Chunk processing timeout after {state.adaptive_timeout.current_timeout}s",
                session_id=state.session_id,
                sequence_number=state.increment_sequence(),
                metadata={
                    "timeout_duration": state.adaptive_timeout.current_timeout,
                    "chunks_received": len(state.adaptive_timeout.chunk_times),
                    "last_chunk_time": state.adaptive_timeout.last_chunk_time,
                    "adaptive_timeout_enabled": True
                }
            )
            events.append(timeout_event)
            
            # 应用退避策略
            state.adaptive_timeout.apply_backoff()
            
            # 更新统计信息
            state.enhanced_stats.timeout_events += 1
            self.stats["total_timeout_events"] += 1
        
        return events
    
    def _calculate_confidence(self, diff_result, state: ParsingState) -> float:
        """计算事件置信度
        
        Args:
            diff_result: 差分结果
            state: 解析状态
            
        Returns:
            float: 置信度 (0.0-1.0)
        """
        confidence = 1.0
        
        # 基于数据类型的置信度
        if isinstance(diff_result.new_value, str):
            # 字符串长度影响置信度
            if len(diff_result.new_value) < 10:
                confidence *= 0.9
            elif len(diff_result.new_value) > 1000:
                confidence *= 0.8
        
        # 基于解析状态的置信度
        if state.enhanced_stats.repair_attempts > 0:
            confidence *= 0.8
        
        # 基于缓冲区状态的置信度
        if state.chunk_buffer.total_size > state.chunk_buffer.max_size * 0.8:
            confidence *= 0.9
        
        return max(0.0, min(1.0, confidence))
    
    async def _validate_data(self, state: ParsingState, data: Dict[str, Any]) -> List[StreamingEvent]:
        """验证数据并生成验证事件
        
        Args:
            state: 解析状态
            data: 待验证的数据
            
        Returns:
            List[StreamingEvent]: 验证事件列表
        """
        if not self.schema_validator or not state.validation_context:
            return []
        
        events = []
        
        try:
            # 获取所有路径
            all_paths = self.path_builder.extract_parsing_key_orders(data)
            
            for path in all_paths:
                success, value = self.path_builder.get_value_at_path(data, path)
                if not success:
                    continue
                
                # 验证路径值
                validation_result = self.schema_validator.validate_path(
                    path=path,
                    value=value,
                    context=state.validation_context
                )
                
                # 如果验证失败，生成错误事件
                if not validation_result.is_valid:
                    state.enhanced_stats.validation_errors += 1
                    self.stats["total_validation_errors"] += 1
                    
                    error_event = create_error_event(
                        path=path,
                        error_type="validation_error",
                        error_message=f"Schema validation failed: {validation_result.level.value}",
                        session_id=state.session_id,
                        sequence_number=state.increment_sequence(),
                        metadata={
                            "validation_result": validation_result.to_dict(),
                            "schema_issues": [issue.to_dict() for issue in validation_result.issues],
                            "repair_suggestions": [suggestion.to_dict() for suggestion in validation_result.suggestions]
                        }
                    )
                    events.append(error_event)
        
        except Exception as e:
            # Schema 验证错误
            error_event = create_error_event(
                path="",
                error_type="schema_validation_error",
                error_message=f"Schema validation error: {str(e)}",
                session_id=state.session_id,
                sequence_number=state.increment_sequence()
            )
            events.append(error_event)
        
        return events
    
    async def _handle_parsing_error(
        self, 
        state: ParsingState, 
        session_id: str, 
        content_to_parse: str, 
        chunk: str, 
        start_time: float, 
        is_final: bool, 
        error_message: str
    ) -> List[StreamingEvent]:
        """处理解析错误和修复逻辑
        
        Args:
            state: 解析状态
            session_id: 会话ID
            content_to_parse: 待解析内容
            chunk: 原始块
            start_time: 开始时间
            is_final: 是否为最终块
            error_message: 错误消息
            
        Returns:
            List[StreamingEvent]: 错误事件列表
        """
        events = []
        
        # 记录失败统计
        state.enhanced_stats.failed_chunks += 1
        
        # 尝试修复（如果启用了补全）
        repair_attempted = False
        if self.json_completer and not is_final:
            try:
                state.enhanced_stats.repair_attempts += 1
                self.stats["total_repairs"] += 1
                
                # 尝试使用补全器修复
                completion_result = self.json_completer.complete(content_to_parse)
                if completion_result.is_valid:
                    parsed_data = json.loads(completion_result.completed_json)
                    
                    # 生成修复事件
                    repair_event = create_delta_event(
                        path="",
                        value=parsed_data,
                        delta_value=parsed_data,
                        session_id=session_id,
                        sequence_number=state.increment_sequence(),
                        previous_value=state.current_data,
                        is_partial=True,
                        metadata={
                            "repaired": True,
                            "repair_confidence": completion_result.confidence,
                            "repair_trace": completion_result.completion_trace
                        }
                    )
                    events.append(repair_event)
                    
                    # 更新状态
                    state.previous_data = copy.deepcopy(state.current_data)
                    state.current_data = parsed_data
                    state.enhanced_stats.successful_repairs += 1
                    repair_attempted = True
                    
            except Exception:
                pass  # 修复失败，继续处理原始错误
        
        if not repair_attempted:
            # 获取详细的异常信息
            import traceback
            import sys
            exception_details = {
                "chunk_size": len(chunk),
                "buffer_size": state.chunk_buffer.total_size,
                "processing_time_ms": (time.time() - start_time) * 1000,
                "is_final": is_final,
                "content_preview": content_to_parse[:100] if content_to_parse else ""
            }
            
            # 如果有当前异常，添加详细信息
            current_exception = sys.exc_info()
            if current_exception[0] is not None:
                exception_details.update({
                    "exception_type": current_exception[0].__name__,
                    "exception_message": str(current_exception[1]),
                    "exception_traceback": traceback.format_exception(*current_exception)
                })
                print(f"[DEBUG] 捕获到异常: {current_exception[0].__name__}: {current_exception[1]}")
                print(f"[DEBUG] 异常堆栈: {''.join(traceback.format_exception(*current_exception))}")
            
            # 生成错误事件
            error_event = create_error_event(
                path="",
                error_type="parsing_error",
                error_message=error_message,
                session_id=session_id,
                sequence_number=state.increment_sequence(),
                metadata=exception_details
            )
            events.append(error_event)
            state.errors.append(error_message)
        
        return events
    
    async def _parse_json_chunk(self, chunk: str, state: ParsingState) -> Optional[Dict[str, Any]]:
        """解析JSON块
        
        Args:
            chunk: JSON块
            state: 解析状态
            
        Returns:
            Optional[Dict[str, Any]]: 解析结果
            
        Raises:
            ParsingError: 当解析过程中发生严重错误时
        """
        try:
            # 验证输入参数
            if not isinstance(chunk, str):
                raise ParsingError(
                    f"Chunk must be a string, got {type(chunk)}",
                    json_content=str(chunk)[:100],
                    severity=ErrorSeverity.HIGH
                )
            
            if not chunk.strip():
                return None
            
            # 检查块大小是否合理
            if len(chunk) > 10 * 1024 * 1024:  # 10MB限制
                raise ParsingError(
                    f"Chunk size too large: {len(chunk)} bytes",
                    json_content=chunk[:100],
                    severity=ErrorSeverity.HIGH
                )
            
            try:
                # 首先尝试直接解析
                return json.loads(chunk)
            except json.JSONDecodeError as e:
                # 记录JSON解析错误
                state.enhanced_stats.json_decode_errors += 1
                
                # 如果是严重的语法错误，记录详细信息
                if hasattr(e, 'lineno') and hasattr(e, 'colno'):
                    error_context = {
                        'line': e.lineno,
                        'column': e.colno,
                        'position': getattr(e, 'pos', None),
                        'error_msg': str(e)
                    }
                    state.parsing_errors.append(error_context)
            
            try:
                # 尝试使用json5解析（支持更宽松的语法）
                import json5
                result = json5.loads(chunk)
                state.enhanced_stats.json5_fallback_success += 1
                return result
            except Exception as e:
                # 记录json5解析失败
                state.enhanced_stats.json5_fallback_errors += 1
            
            # 如果启用了补全，尝试补全后解析
            if self.json_completer:
                try:
                    completion_result = self.json_completer.complete(chunk)
                    if completion_result.is_valid:
                        result = json.loads(completion_result.completed_json)
                        state.enhanced_stats.completion_success += 1
                        return result
                    else:
                        state.enhanced_stats.completion_failures += 1
                except Exception as e:
                    state.enhanced_stats.completion_errors += 1
                    # 补全器错误不应该阻止整个解析过程
                    pass
            
            # 所有解析方法都失败了
            state.enhanced_stats.total_parse_failures += 1
            return None
            
        except ParsingError:
            raise
        except Exception as e:
            # 捕获所有其他异常
            raise ParsingError(
                f"Unexpected error during JSON parsing: {str(e)}",
                json_content=chunk[:100] if isinstance(chunk, str) else str(chunk)[:100],
                severity=ErrorSeverity.HIGH
            ) from e
    
    async def _compare_and_generate_events(
        self, 
        state: ParsingState, 
        new_data: Any
    ) -> List[StreamingEvent]:
        """比较数据并生成事件 - 支持文本和JSON两种格式
        
        参考agently项目的稳定实现，支持：
        1. 纯文本流式输出（字符串增量）
        2. JSON结构化流式输出（字段增量）
        
        Args:
            state: 解析状态
            new_data: 新数据（可以是字符串或字典）
            
        Returns:
            List[StreamingEvent]: 事件列表
            
        Raises:
            ParsingError: 当事件生成过程中发生错误时
        """
        try:
            # 验证输入参数
            if state is None:
                raise ParsingError(
                    "Parsing state cannot be None",
                    severity=ErrorSeverity.HIGH
                )
            
            events = []
            
            try:
                # 处理纯文本流式输出
                if isinstance(new_data, str):
                    return await self._handle_text_streaming(state, new_data)
                
                # 处理JSON结构化流式输出
                if isinstance(new_data, dict):
                    return await self._handle_json_streaming(state, new_data)
                
                # 处理None或其他类型
                if new_data is None:
                    # JSON解析失败，不生成任何事件
                    return []
                
                # 其他类型直接使用递归比较
                await self._traverse_and_compare(
                    events=events,
                    current_data=new_data,
                    previous_data=state.current_data,
                    path="",
                    state=state
                )
                
                return events
                
            except Exception as e:
                # 记录事件生成错误
                state.enhanced_stats.event_generation_errors += 1
                
                # 尝试生成错误事件
                try:
                    error_event = create_error_event(
                        path="",
                        error_type="event_generation_error",
                        error_message=f"Failed to generate events: {str(e)}",
                        session_id=state.session_id,
                        sequence_number=state.increment_sequence(),
                        metadata={
                            "data_type": type(new_data).__name__,
                            "data_preview": str(new_data)[:100] if new_data is not None else "None"
                        }
                    )
                    return [error_event]
                except Exception:
                    # 如果连错误事件都无法生成，返回空列表
                    return []
                
        except ParsingError:
            raise
        except Exception as e:
            # 捕获所有其他异常
            raise ParsingError(
                f"Unexpected error during event generation: {str(e)}",
                json_content=str(new_data)[:100] if new_data is not None else "None",
                severity=ErrorSeverity.HIGH
            ) from e
    
    async def _handle_text_streaming(self, state: ParsingState, new_text: str) -> List[StreamingEvent]:
        """处理纯文本流式输出
        
        Args:
            state: 解析状态
            new_text: 新文本内容
            
        Returns:
            List[StreamingEvent]: 事件列表
        """
        events = []
        previous_text = state.current_data if isinstance(state.current_data, str) else ""
        
        # 计算文本增量
        if len(new_text) > len(previous_text):
            delta_text = new_text[len(previous_text):]
            
            # 生成增量事件
            delta_event = create_delta_event(
                path="content",
                value=new_text,
                delta_value=delta_text,
                session_id=state.session_id,
                sequence_number=state.increment_sequence(),
                previous_value=previous_text,
                is_partial=True
            )
            events.append(delta_event)
        
        # 更新状态
        state.current_data = new_text
        return events
    
    async def _handle_json_streaming(self, state: ParsingState, new_data: Dict[str, Any]) -> List[StreamingEvent]:
        """处理JSON结构化流式输出
        
        Args:
            state: 解析状态
            new_data: 新JSON数据
            
        Returns:
            List[StreamingEvent]: 事件列表
        """
        events = []
        
        # 使用简化的递归比较逻辑
        await self._traverse_and_compare(
            events=events,
            current_data=new_data,
            previous_data=state.current_data if isinstance(state.current_data, dict) else {},
            path="",
            state=state
        )
        
        # 更新状态
        state.current_data = new_data
        return events
    
    async def _traverse_and_compare(
        self,
        events: List[StreamingEvent],
        current_data: Any,
        previous_data: Any,
        path: str,
        state: ParsingState
    ) -> None:
        """递归遍历并比较数据，生成增量事件 - 重新设计的字段级流式解析
        
        参考agently项目的实现，重新设计字段过滤逻辑：
        1. 在递归遍历过程中进行字段过滤
        2. 确保只有匹配的字段才生成事件
        3. 支持真正的字段级流式输出
        4. 保持事件的实时性和连续性
        5. 正确处理对象边界和字段分离
        
        Args:
            events: 事件列表，用于收集生成的事件
            current_data: 当前数据
            previous_data: 之前的数据
            path: 当前路径
            state: 解析状态
        """
        # 处理字符串类型 - 最常见的流式更新场景
        if isinstance(current_data, str):
            # 检查字段过滤 - 只有匹配的字段才生成事件
            if self._should_include_field(path):
                if not isinstance(previous_data, str):
                    # 新字符串字段 - 生成delta事件
                    delta_event = create_delta_event(
                        path=path,
                        value=current_data,
                        delta_value=current_data,
                        session_id=state.session_id,
                        sequence_number=state.increment_sequence(),
                        previous_value=previous_data,
                        is_partial=self._is_value_partial(current_data)
                    )
                    events.append(delta_event)
                elif current_data != previous_data:
                    # 字符串更新 - 计算真正的增量部分
                    delta_value = self._calculate_string_delta(previous_data, current_data)
                    
                    delta_event = create_delta_event(
                        path=path,
                        value=current_data,
                        delta_value=delta_value,
                        session_id=state.session_id,
                        sequence_number=state.increment_sequence(),
                        previous_value=previous_data,
                        is_partial=self._is_value_partial(current_data)
                    )
                    events.append(delta_event)
                
                # 检查字符串是否完成
                if self._should_mark_field_complete(path, current_data, state):
                    if path not in state.completed_fields:
                        done_event = create_done_event(
                            path=path,
                            final_value=current_data,
                            session_id=state.session_id,
                            sequence_number=state.increment_sequence(),
                            validation_passed=True
                        )
                        events.append(done_event)
                        state.completed_fields.add(path)
        
        # 处理基本类型 (int, float, bool, None)
        elif isinstance(current_data, (int, float, bool, type(None))):
            # 检查字段过滤 - 只有匹配的字段才生成事件
            if self._should_include_field(path):
                if current_data != previous_data:
                    delta_event = create_delta_event(
                        path=path,
                        value=current_data,
                        delta_value=current_data,
                        session_id=state.session_id,
                        sequence_number=state.increment_sequence(),
                        previous_value=previous_data,
                        is_partial=False
                    )
                    events.append(delta_event)
                    
                    # 基本类型通常立即完成
                    if path not in state.completed_fields:
                        done_event = create_done_event(
                            path=path,
                            final_value=current_data,
                            session_id=state.session_id,
                            sequence_number=state.increment_sequence(),
                            validation_passed=True
                        )
                        events.append(done_event)
                        state.completed_fields.add(path)
        
        # 处理字典类型
        elif isinstance(current_data, dict):
            previous_dict = previous_data if isinstance(previous_data, dict) else {}
            
            # 遍历当前字典的所有键
            for key, value in current_data.items():
                new_path = f"{path}.{key}" if path else key
                previous_value = previous_dict.get(key)
                
                # 检查字段过滤 - 如果当前路径或其子路径可能被包含，才进行递归处理
                if self._should_process_path_branch(new_path):
                    # 递归处理子项
                    await self._traverse_and_compare(
                        events=events,
                        current_data=value,
                        previous_data=previous_value,
                        path=new_path,
                        state=state
                    )
        
        # 处理列表类型
        elif isinstance(current_data, list):
            previous_list = previous_data if isinstance(previous_data, list) else []
            
            # 遍历当前列表的所有项
            for i, value in enumerate(current_data):
                new_path = f"{path}[{i}]"
                previous_value = previous_list[i] if i < len(previous_list) else None
                
                # 检查字段过滤 - 如果当前路径或其子路径可能被包含，才进行递归处理
                if self._should_process_path_branch(new_path):
                    # 递归处理列表项
                    await self._traverse_and_compare(
                        events=events,
                        current_data=value,
                        previous_data=previous_value,
                        path=new_path,
                        state=state
                    )
    
    def _should_include_field(self, path: str) -> bool:
        """判断字段是否应该包含在输出中 - 精确的字段过滤逻辑
        
        Args:
            path: 字段路径
            
        Returns:
            bool: 是否应该包含该字段
        """
        if not self.field_filter.enabled:
            return True
        
        return self.field_filter.should_include_path(path)
    
    def _should_process_path_branch(self, path: str) -> bool:
        """判断是否应该处理某个路径分支 - 修复的分支处理逻辑
        
        参考agently的实现，修复分支处理逻辑：
        1. include模式：只处理可能包含目标字段的分支
        2. exclude模式：处理所有分支，在字段级别进行排除
        3. 避免过早剪枝导致遗漏有效字段
        
        Args:
            path: 要检查的路径
            
        Returns:
            bool: 是否应该处理该路径分支
        """
        if not self.field_filter.enabled:
            return True
        
        # 根路径始终处理，避免过早剪枝
        if not path:
            return True
        
        if self.field_filter.mode == "include":
            # include模式：检查是否有包含路径可能在此分支下
            for include_path in self.field_filter.include_paths:
                # 1. 当前路径是目标路径的前缀（需要继续深入）
                if include_path.startswith(path + ".") or include_path.startswith(path + "["):
                    return True
                # 2. 当前路径包含目标字段名（可能匹配）
                if path.endswith("." + include_path) or path.endswith("[" + include_path + "]"):
                    return True
                # 3. 目标路径是当前路径的前缀（当前路径在目标路径下）
                if path.startswith(include_path + ".") or path.startswith(include_path + "["):
                    return True
                # 4. 精确匹配
                if path == include_path:
                    return True
                # 5. 简单字段名匹配（处理顶级字段）
                if path == include_path or include_path == path.split(".")[-1]:
                    return True
            return False
        elif self.field_filter.mode == "exclude":
            # exclude模式：处理所有分支，让字段级过滤来决定是否输出
            # 这是关键修复：不在分支级别进行排除，避免遗漏其他字段
            return True
        
        return True
    
    def _calculate_string_delta(self, old_value: str, new_value: str) -> str:
        """计算字符串的增量部分 - 使用性能优化器的缓存功能
        
        Args:
            old_value: 旧字符串值
            new_value: 新字符串值
            
        Returns:
            str: 增量部分
        """
        # 使用性能优化器的字符串增量计算
        return self.performance_optimizer.calculate_string_delta(old_value, new_value)
    
    def _is_value_partial(self, value: Any) -> bool:
        """判断值是否为部分值 - 优化的部分值判断
        
        Args:
            value: 值
            
        Returns:
            bool: 是否为部分值
        """
        if isinstance(value, str):
             # 字符串部分值判断
             if not value.strip():
                 return True
             # 如果不以完整标点结尾，可能是部分值
             return not value.rstrip().endswith(('.', '!', '?', '。', '！', '？', '"', "'"))
        elif isinstance(value, (dict, list)):
            # 复杂对象在流式解析中通常是部分值
            return True
        else:
            # 基本类型通常是完整的
            return False
    
    def _calculate_delta(self, old_value: Any, new_value: Any) -> Any:
        """计算增量值 - 简化的增量计算逻辑
        
        Args:
            old_value: 旧值
            new_value: 新值
            
        Returns:
            Any: 增量值
        """
        # 注意：在新的traverse_and_compare逻辑中，增量计算已经内置
        # 这个方法保留用于向后兼容
        if isinstance(old_value, str) and isinstance(new_value, str):
            if new_value.startswith(old_value):
                return new_value[len(old_value):]
        
        # 对于其他类型，直接返回新值作为增量
        return new_value
    
    def _should_process_path(self, path: str) -> bool:
        """判断是否应该处理某个路径
        
        考虑字段过滤设置，判断当前路径或其子路径是否可能被包含在输出中。
        这是一个优化方法，避免处理肯定不会输出的路径分支。
        
        Args:
            path: 要检查的路径
            
        Returns:
            bool: 是否应该处理该路径
        """
        if not self.field_filter.enabled:
            return True
        
        # 如果当前路径本身应该被包含，则处理
        if self.field_filter.should_include_path(path):
            return True
        
        # 检查是否有子路径可能被包含
        if self.field_filter.mode == "include":
            # include模式：检查是否有包含路径以当前路径为前缀
            for include_path in self.field_filter.include_paths:
                if include_path.startswith(path + ".") or include_path.startswith(path + "["):
                    return True
                # 检查字段名匹配的情况
                if "." + include_path in path or "[" + include_path + "]" in path:
                    return True
        elif self.field_filter.mode == "exclude":
            # exclude模式：只要不是被明确排除的路径，就可能需要处理
            # 检查当前路径是否是被排除路径的前缀
            for exclude_path in self.field_filter.exclude_paths:
                if path.endswith("." + exclude_path) or path.endswith("[" + exclude_path + "]"):
                    return False
            return True
        
        return True
    
    def _should_mark_field_complete(self, path: str, value: Any, state: ParsingState) -> bool:
        """判断字段是否应该标记为完成 - 优化的完成判断逻辑
        
        参考agently项目的完成判断策略，采用更保守和准确的方法
        
        Args:
            path: 字段路径
            value: 字段值
            state: 解析状态
            
        Returns:
            bool: 是否应该标记为完成
        """
        # 基本类型立即完成
        if isinstance(value, (int, float, bool, type(None))):
            return True
        
        # 字符串完成判断 - 更严格的条件
        if isinstance(value, str):
            # 空字符串不算完成
            if not value.strip():
                return False
            
            # 检查是否以完整的句子结尾
            if value.rstrip().endswith(('.', '!', '?', '。', '！', '？')):
                return True
            
            # 检查是否以引号结尾（可能是完整的字符串）
            if value.endswith(('"', "'", '}', ']')):
                return True
            
            # 对于较短的字符串，如果看起来是完整的词或短语
            if len(value) < 50 and not value.endswith((',', '\n', '\t')):
                return True
        
        # 复杂对象需要更复杂的逻辑
        return False
    
    async def finalize_session(self, session_id: str) -> List[StreamingEvent]:
        """完成解析会话
        
        Args:
            session_id: 会话ID
            
        Returns:
            List[StreamingEvent]: 最终事件列表
        """
        if session_id not in self.parsing_states:
            raise ValueError(f"Session {session_id} not found")
        
        state = self.parsing_states[session_id]
        events = []
        current_time = time.time()
        
        # 处理剩余的缓冲区数据
        if state.chunk_buffer.buffer:
            remaining_content = state.chunk_buffer.get_soft_trimmed_content()
            if remaining_content.strip():
                try:
                    # 尝试解析剩余内容
                    final_data = await self._parse_json_chunk(remaining_content, state)
                    if final_data and state.current_data != final_data:
                        # 生成最终差分事件
                        final_events = await self._compare_and_generate_events(state, final_data)
                        events.extend(final_events)
                        state.current_data = final_data
                except Exception as e:
                    # 生成最终解析错误事件
                    error_event = create_error_event(
                        path="",
                        error_type="final_parsing_error",
                        error_message=f"Failed to parse remaining buffer: {str(e)}",
                        session_id=session_id,
                        sequence_number=state.increment_sequence(),
                        metadata={
                            "remaining_buffer_size": len(remaining_content),
                            "timing": {
                                "error_time": current_time,
                                "session_duration": current_time - state.enhanced_stats.start_time.timestamp()
                            }
                        }
                    )
                    events.append(error_event)
        
        # 标记所有剩余字段为完成
        all_paths = set(self.path_builder.extract_parsing_key_orders(state.current_data))
        remaining_paths = all_paths - state.completed_fields
        
        for path in remaining_paths:
            # 检查字段过滤器，只为应该包含的路径生成done事件
            if self.field_filter and not self.field_filter.should_include_path(path):
                continue
                
            success, value = self.path_builder.get_value_at_path(state.current_data, path)
            if success:
                path_hash = state.calculate_path_hash(path, value)
                done_event = create_done_event(
                    path=path,
                    final_value=value,
                    session_id=session_id,
                    sequence_number=state.increment_sequence(),
                    validation_passed=True,
                    metadata={
                        "path_hash": path_hash,
                        "timing": {
                            "completion_time": current_time,
                            "session_duration": current_time - state.enhanced_stats.start_time.timestamp()
                        },
                        "finalized": True
                    }
                )
                events.append(done_event)
                state.completed_fields.add(path)
                state.enhanced_stats.record_field_completion(path)
        
        # 如果启用了差分引擎，进行最终处理
        if self.enable_diff_engine and self.diff_engine:
            # 最终稳定性检查并发射 DONE 事件
            final_done_events = self.diff_engine.check_stability_and_emit_done(
                session_id=session_id,
                sequence_number_generator=state.increment_sequence,
                current_data=state.current_data
            )
            events.extend(final_done_events)
            
            # 刷新最终的合并事件
            final_coalesced_events = self.diff_engine.flush_all_coalescing_buffers()
            events.extend(final_coalesced_events)
            
            # 清理过期的路径状态
            self.diff_engine.cleanup_old_paths(max_age_hours=0)  # 立即清理
        
        # 记录会话完成时间
        state.enhanced_stats.record_completion()
        
        # 发出所有事件
        for event in events:
            await self._emit_event(event)
        
        # 清理会话相关的验证上下文
        if self.schema_validator and state.validation_context:
            # 清理验证上下文（如果有相关方法）
            pass
        
        # 从内存管理器注销会话
        self.memory_manager.unregister_session(session_id)
        
        # 更新统计
        self.stats["active_sessions"] -= 1
        if state.errors:
            self.stats["failed_sessions"] += 1
        else:
            self.stats["completed_sessions"] += 1
        
        # 更新增强统计信息
        session_duration = current_time - state.enhanced_stats.start_time.timestamp()
        self.stats["total_repair_attempts"] = self.stats.get("total_repair_attempts", 0) + state.enhanced_stats.repair_attempts
        self.stats["total_validation_errors"] = self.stats.get("total_validation_errors", 0) + state.enhanced_stats.validation_errors
        
        return events
    
    async def parse_stream(
        self,
        stream: AsyncGenerator[str, None],
        session_id: Optional[str] = None
    ) -> AsyncGenerator[StreamingEvent, None]:
        """解析流式数据
        
        Args:
            stream: 异步数据流
            session_id: 会话ID，如果为None则自动创建
            
        Yields:
            StreamingEvent: 流式事件
        """
        if session_id is None:
            session_id = self.create_session()
        
        try:
            async for chunk in stream:
                events = await self.parse_chunk(session_id, chunk)
                for event in events:
                    yield event
                
                # 添加超时检查
                await asyncio.sleep(0)  # 让出控制权
        
        except Exception as e:
            # 生成错误事件
            error_event = create_error_event(
                path="",
                error_type="stream_error",
                error_message=str(e),
                session_id=session_id,
                sequence_number=self.parsing_states[session_id].increment_sequence()
            )
            await self._emit_event(error_event)
            yield error_event
        
        finally:
            # 完成会话
            final_events = await self.finalize_session(session_id)
            for event in final_events:
                yield event
    
    def get_session_state(self, session_id: str) -> Optional[ParsingState]:
        """获取会话状态
        
        Args:
            session_id: 会话ID
            
        Returns:
            Optional[ParsingState]: 会话状态
        """
        return self.parsing_states.get(session_id)
    
    def get_parsing_state(self, session_id: str) -> Optional[ParsingState]:
        """获取解析状态（别名方法）
        
        Args:
            session_id: 会话ID
            
        Returns:
            Optional[ParsingState]: 解析状态
        """
        state = self.parsing_states.get(session_id)
        if state:
            # 添加is_complete属性 - 改进的完成状态判断逻辑
            # 1. 没有错误
            # 2. 已处理至少一个块
            # 3. 当前数据不为空（表示成功解析了数据）
            # 4. 没有解析错误
            state.is_complete = (
                len(state.errors) == 0 and 
                state.processed_chunks > 0 and 
                bool(state.current_data) and
                len(state.parsing_errors) == 0
            )
        return state
    
    def has_session(self, session_id: str) -> bool:
        """检查会话是否存在
        
        Args:
            session_id: 会话ID
            
        Returns:
            bool: 会话是否存在
        """
        return session_id in self.parsing_states
    
    def complete_session(self, session_id: str):
        """完成会话（同步版本）
        
        Args:
            session_id: 会话ID
        """
        if session_id in self.parsing_states:
            state = self.parsing_states[session_id]
            state.is_complete = True
            if self.stats["active_sessions"] > 0:
                self.stats["active_sessions"] -= 1
            self.stats["completed_sessions"] += 1
    
    def get_current_data(self, session_id: str) -> Optional[Dict[str, Any]]:
        """获取当前解析数据
        
        Args:
            session_id: 会话ID
            
        Returns:
            Optional[Dict[str, Any]]: 当前数据
        """
        state = self.parsing_states.get(session_id)
        return state.current_data if state else None
    
    def cleanup_session(self, session_id: str):
        """清理会话
        
        Args:
            session_id: 会话ID
        """
        if session_id in self.parsing_states:
            # 从内存管理器注销会话
            self.memory_manager.unregister_session(session_id)
            
            del self.parsing_states[session_id]
            if self.stats["active_sessions"] > 0:
                self.stats["active_sessions"] -= 1
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息
        
        Returns:
            Dict[str, Any]: 统计信息
        """
        stats = {
            **self.stats,
            "completion_stats": self.json_completer.get_completion_stats() if self.json_completer else None
        }
        
        # 添加差分引擎统计信息
        if self.enable_diff_engine and self.diff_engine:
            stats["diff_engine_stats"] = self.diff_engine.get_stats()
        
        # 添加Schema验证器统计
        if self.schema_validator:
            stats["schema_validator_stats"] = self.schema_validator.get_stats()
        
        # 添加会话级增强统计信息
        session_stats = {
            "active_sessions": len(self.parsing_states),
            "session_details": {}
        }
        
        for session_id, state in self.parsing_states.items():
            current_time = time.time()
            session_duration = current_time - state.enhanced_stats.start_time.timestamp()
            ttf_field = (state.enhanced_stats.first_field_time - state.enhanced_stats.start_time.timestamp()) if state.enhanced_stats.first_field_time else None
            
            session_stats["session_details"][session_id] = {
                "chunks_processed": state.enhanced_stats.processed_chunks,
                "total_chunks": state.enhanced_stats.total_chunks,
                "session_duration": session_duration,
                "ttf_field": ttf_field,
                "completed_fields": len(state.completed_fields),
                "repair_attempts": state.enhanced_stats.repair_attempts,
                "validation_errors": state.enhanced_stats.validation_errors,
                "timeout_events": state.enhanced_stats.timeout_events,
                "buffer_overflows": state.enhanced_stats.buffer_overflows,
                "buffer_utilization": state.chunk_buffer.total_size / state.chunk_buffer.max_size if state.chunk_buffer.max_size > 0 else 0,
                "adaptive_timeout": {
                    "current_timeout": state.adaptive_timeout.current_timeout,
                    "consecutive_timeouts": state.adaptive_timeout.consecutive_timeouts
                } if self.adaptive_timeout_enabled else None
            }
        
        stats["enhanced_sessions"] = session_stats
        
        # 添加全局增强统计信息
        stats["enhanced_global"] = {
            "total_repair_attempts": stats.get("total_repair_attempts", 0),
            "total_validation_errors": stats.get("total_validation_errors", 0),
            "total_timeout_events": stats.get("total_timeout_events", 0),
            "adaptive_timeout_enabled": self.adaptive_timeout_enabled,
            "schema_validation_enabled": self.enable_schema_validation,
            "buffer_size": self.buffer_size
        }
        
        return stats
    
    def reset_stats(self):
        """重置统计信息"""
        self.stats = {
            "total_sessions": 0,
            "active_sessions": 0,
            "completed_sessions": 0,
            "failed_sessions": 0,
            "total_events_emitted": 0
        }
        if self.json_completer:
            self.json_completer.reset_stats()
        
        # 重置差分引擎统计信息
        if self.enable_diff_engine and self.diff_engine:
            self.diff_engine.stats = {
                "total_diffs": 0,
                "suppressed_duplicates": 0,
                "coalesced_events": 0,
                "done_events_emitted": 0
            }


# 便捷函数
async def parse_json_stream(
    stream: AsyncGenerator[str, None],
    enable_completion: bool = True,
    completion_strategy: CompletionStrategy = CompletionStrategy.SMART,
    field_filter: Optional[FieldFilter] = None
) -> AsyncGenerator[StreamingEvent, None]:
    """解析JSON流的便捷函数
    
    Args:
        stream: 异步数据流
        enable_completion: 是否启用补全
        completion_strategy: 补全策略
        field_filter: 字段过滤器配置
        
    Yields:
        StreamingEvent: 流式事件
    """
    parser = StreamingParser(
        enable_completion=enable_completion,
        completion_strategy=completion_strategy,
        field_filter=field_filter
    )
    
    async for event in parser.parse_stream(stream):
        yield event


async def parse_json_stream_with_fields(
    stream: AsyncGenerator[str, None],
    include_fields: Optional[List[str]] = None,
    exclude_fields: Optional[List[str]] = None,
    exact_match: bool = False,
    enable_completion: bool = True,
    completion_strategy: CompletionStrategy = CompletionStrategy.SMART
) -> AsyncGenerator[StreamingEvent, None]:
    """解析JSON流并只输出指定字段的便捷函数
    
    Args:
        stream: 异步数据流
        include_fields: 要包含的字段列表（如 ['description', 'user.name']）
        exclude_fields: 要排除的字段列表
        exact_match: 是否精确匹配字段路径
        enable_completion: 是否启用补全
        completion_strategy: 补全策略
        
    Yields:
        StreamingEvent: 流式事件
        
    Examples:
        # 只输出description字段
        async for event in parse_json_stream_with_fields(stream, include_fields=['description']):
            print(f"{event.path}: {event.data}")
            
        # 排除敏感字段
        async for event in parse_json_stream_with_fields(stream, exclude_fields=['password', 'token']):
            print(f"{event.path}: {event.data}")
    """
    # 创建字段过滤器
    # 确定过滤模式：如果有include_fields则使用include模式，否则使用exclude模式
    if include_fields:
        mode = "include"
        filter_paths = include_fields
    elif exclude_fields:
        mode = "exclude"
        filter_paths = exclude_fields
    else:
        # 如果两者都没有，则不启用过滤
        field_filter = FieldFilter(enabled=False)
    
    if include_fields or exclude_fields:
        field_filter = FieldFilter(
            enabled=True,
            include_paths=include_fields if mode == "include" else [],
            exclude_paths=exclude_fields if mode == "exclude" else [],
            mode=mode,
            exact_match=exact_match
        )
    
    parser = StreamingParser(
        enable_completion=enable_completion,
        completion_strategy=completion_strategy,
        field_filter=field_filter
    )
    
    async for event in parser.parse_stream(stream):
        yield event