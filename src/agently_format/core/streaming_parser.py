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
        """
        content = self.get_content()
        
        # 如果在字符串中，保留到字符串结束
        if self.in_string:
            return content
        
        # 检查括号平衡
        if not self._is_balanced():
            return content
        
        # 查找最后一个完整的 JSON token
        trimmed = self._find_last_complete_token(content)
        return trimmed
    
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
    
    def _find_last_complete_token(self, content: str) -> str:
        """查找最后一个完整的 JSON token"""
        # 简化实现：查找最后一个完整的对象或数组
        brace_count = 0
        bracket_count = 0
        in_string = False
        string_char = None
        escape_next = False
        last_complete_pos = 0
        
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
                    if brace_count == 0 and bracket_count == 0:
                        last_complete_pos = i + 1
                elif char == '[':
                    bracket_count += 1
                elif char == ']':
                    bracket_count -= 1
                    if brace_count == 0 and bracket_count == 0:
                        last_complete_pos = i + 1
        
        return content[:last_complete_pos] if last_complete_pos > 0 else content
    
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


class StreamingParser:
    """流式JSON解析器
    
    异步逐块解析流式JSON数据，维护解析状态，
    并为每个字段在结构构建过程中发出增量和完成事件。
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
        backoff_factor: float = 1.5
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
    
    async def parse_chunk(self, chunk: str, session_id: str, is_final: bool = False) -> List[StreamingEvent]:
        """解析JSON块
        
        Args:
            chunk: JSON块
            session_id: 会话ID
            is_final: 是否为最终块
            
        Returns:
            List[StreamingEvent]: 生成的事件列表
        """
        if session_id not in self.parsing_states:
            raise ValueError(f"Session {session_id} not found")
        
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
                # 解析失败，处理错误
                error_events = await self._handle_parsing_error(
                    state, session_id, content_to_parse, chunk, 
                    start_time, is_final, "Failed to parse JSON chunk"
                )
                events.extend(error_events)
            
            # 更新统计信息
            self.stats["total_chunks_processed"] += 1
            
        except Exception as e:
            # 处理异常错误
            error_events = await self._handle_parsing_error(
                state, session_id, content_to_parse, chunk, 
                start_time, is_final, str(e)
            )
            events.extend(error_events)
        
        # 检查超时
        if self.adaptive_timeout_enabled and state.adaptive_timeout.is_timeout():
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
            events.append(timeout_event)
        
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
            # 生成错误事件
            error_event = create_error_event(
                path="",
                error_type="parsing_error",
                error_message=error_message,
                session_id=session_id,
                sequence_number=state.increment_sequence(),
                metadata={
                    "chunk_size": len(chunk),
                    "buffer_size": state.chunk_buffer.total_size,
                    "processing_time_ms": (time.time() - start_time) * 1000,
                    "is_final": is_final,
                    "content_preview": content_to_parse[:100] if content_to_parse else ""
                }
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
        """
        if not chunk.strip():
            return None
        
        try:
            # 首先尝试直接解析
            return json.loads(chunk)
        except json.JSONDecodeError:
            pass
        
        try:
            # 尝试使用json5解析（支持更宽松的语法）
            return json5.loads(chunk)
        except Exception:
            pass
        
        # 如果启用了补全，尝试补全后解析
        if self.json_completer:
            try:
                completion_result = self.json_completer.complete(chunk)
                if completion_result.is_valid:
                    return json.loads(completion_result.completed_json)
            except Exception:
                pass
        
        # 如果都失败了，返回None
        return None
    
    async def _compare_and_generate_events(
        self, 
        state: ParsingState, 
        new_data: Dict[str, Any]
    ) -> List[StreamingEvent]:
        """比较数据并生成事件
        
        Args:
            state: 解析状态
            new_data: 新数据
            
        Returns:
            List[StreamingEvent]: 事件列表
        """
        events = []
        current_time = time.time()
        
        if self.enable_diff_engine and self.diff_engine:
            # 使用差分引擎进行结构化差分
            diff_results = self.diff_engine.compute_diff(
                old_data=state.current_data,
                new_data=new_data
            )
            
            # 为每个差分结果生成事件
            for diff_result in diff_results:
                # 计算路径哈希
                path_hash = state.calculate_path_hash(diff_result.path, diff_result.new_value)
                
                # 计算置信度（基于数据完整性和稳定性）
                confidence = self._calculate_confidence(diff_result, state)
                
                # 使用差分引擎的幂等事件发射（扩展字段）
                delta_event = self.diff_engine.emit_delta_event(
                    diff_result=diff_result,
                    session_id=state.session_id,
                    sequence_number=state.increment_sequence()
                )
                
                if delta_event:  # 如果事件未被抑制
                    events.append(delta_event)
                
                # 更新路径哈希记录
                state.path_hashes[diff_result.path] = path_hash
                
                # 检查字段是否完成
                if self._should_mark_field_complete(diff_result.path, diff_result.new_value, state):
                    if diff_result.path not in state.completed_fields:
                        done_event = create_done_event(
                            path=diff_result.path,
                            final_value=diff_result.new_value,
                            session_id=state.session_id,
                            sequence_number=state.increment_sequence(),
                            validation_passed=True,
                            metadata={
                                "path_hash": path_hash,
                                "confidence": confidence,
                                "timing": {
                                    "completion_time": current_time,
                                    "total_processing_time": current_time - state.enhanced_stats.start_time.timestamp()
                                },
                                "stability_confirmed": True
                            }
                        )
                        events.append(done_event)
                        state.completed_fields.add(diff_result.path)
                        
                        # 记录字段完成时间
                        state.enhanced_stats.record_field_completion(diff_result.path)
            
            # 检查稳定性并发射 DONE 事件
            done_events = self.diff_engine.check_stability_and_emit_done(
                session_id=state.session_id,
                sequence_number_generator=state.increment_sequence,
                current_data=new_data
            )
            events.extend(done_events)
            
            # 刷新合并缓冲区中的事件
            coalesced_events = self.diff_engine.flush_all_coalescing_buffers()
            events.extend(coalesced_events)
            
        else:
            # 回退到原始逻辑
            events = await self._compare_and_generate_events_legacy(state, new_data)
        
        return events
    
    async def _compare_and_generate_events_legacy(
        self, 
        state: ParsingState, 
        new_data: Dict[str, Any]
    ) -> List[StreamingEvent]:
        """传统的比较数据并生成事件方法（回退逻辑）
        
        Args:
            state: 解析状态
            new_data: 新数据
            
        Returns:
            List[StreamingEvent]: 事件列表
        """
        events = []
        
        # 获取所有路径
        new_paths = set(self.path_builder.extract_parsing_key_orders(new_data))
        old_paths = set(self.path_builder.extract_parsing_key_orders(state.current_data))
        
        # 处理新增和更新的路径
        for path in new_paths:
            success, new_value = self.path_builder.get_value_at_path(new_data, path)
            if not success:
                continue
            
            old_success, old_value = self.path_builder.get_value_at_path(state.current_data, path)
            
            if not old_success:
                # 新字段
                delta_event = create_delta_event(
                    path=path,
                    value=new_value,
                    delta_value=new_value,
                    session_id=state.session_id,
                    sequence_number=state.increment_sequence(),
                    previous_value=None,
                    is_partial=self._is_value_partial(new_value)
                )
                events.append(delta_event)
            elif old_value != new_value:
                # 字段更新
                delta_event = create_delta_event(
                    path=path,
                    value=new_value,
                    delta_value=self._calculate_delta(old_value, new_value),
                    session_id=state.session_id,
                    sequence_number=state.increment_sequence(),
                    previous_value=old_value,
                    is_partial=self._is_value_partial(new_value)
                )
                events.append(delta_event)
            
            # 检查字段是否完成
            if self._should_mark_field_complete(path, new_value, state):
                if path not in state.completed_fields:
                    done_event = create_done_event(
                        path=path,
                        final_value=new_value,
                        session_id=state.session_id,
                        sequence_number=state.increment_sequence(),
                        validation_passed=True
                    )
                    events.append(done_event)
                    state.completed_fields.add(path)
        
        return events
    
    def _is_value_partial(self, value: Any) -> bool:
        """判断值是否为部分值
        
        Args:
            value: 值
            
        Returns:
            bool: 是否为部分值
        """
        if isinstance(value, str):
            # 字符串可能不完整
            return len(value) < 1000  # 简单启发式
        elif isinstance(value, (dict, list)):
            # 复杂对象可能不完整
            return True
        else:
            # 基本类型通常是完整的
            return False
    
    def _calculate_delta(self, old_value: Any, new_value: Any) -> Any:
        """计算增量值
        
        Args:
            old_value: 旧值
            new_value: 新值
            
        Returns:
            Any: 增量值
        """
        if isinstance(old_value, str) and isinstance(new_value, str):
            # 字符串增量
            if new_value.startswith(old_value):
                return new_value[len(old_value):]
            else:
                return new_value
        elif isinstance(old_value, list) and isinstance(new_value, list):
            # 数组增量
            if len(new_value) > len(old_value):
                return new_value[len(old_value):]
            else:
                return new_value
        elif isinstance(old_value, dict) and isinstance(new_value, dict):
            # 对象增量
            delta = {}
            for key, value in new_value.items():
                if key not in old_value or old_value[key] != value:
                    delta[key] = value
            return delta
        else:
            # 其他情况返回新值
            return new_value
    
    def _should_mark_field_complete(self, path: str, value: Any, state: ParsingState) -> bool:
        """判断字段是否应该标记为完成
        
        Args:
            path: 字段路径
            value: 字段值
            state: 解析状态
            
        Returns:
            bool: 是否应该标记为完成
        """
        # 简单启发式：基本类型通常是完成的
        if isinstance(value, (int, float, bool, type(None))):
            return True
        
        # 字符串：检查是否看起来完整
        if isinstance(value, str):
            # 如果字符串很短或以标点符号结尾，可能是完整的
            return len(value) < 100 or value.endswith(('.', '!', '?', '"', "'"))
        
        # 复杂对象：需要更复杂的逻辑
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
            # 添加is_complete属性
            state.is_complete = len(state.errors) == 0 and state.processed_chunks > 0
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
    completion_strategy: CompletionStrategy = CompletionStrategy.SMART
) -> AsyncGenerator[StreamingEvent, None]:
    """解析JSON流的便捷函数
    
    Args:
        stream: 异步数据流
        enable_completion: 是否启用补全
        completion_strategy: 补全策略
        
    Yields:
        StreamingEvent: 流式事件
    """
    parser = StreamingParser(
        enable_completion=enable_completion,
        completion_strategy=completion_strategy
    )
    
    async for event in parser.parse_stream(stream):
        yield event