"""结构化差分引擎模块

实现 dict/list aware 的最小差分算法，支持事件去重与合并（coalescing），
为流式解析提供幂等事件派发能力。
"""

import hashlib
import json
from typing import Any, Dict, List, Optional, Tuple, Set, Union
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import copy

from ..types.events import StreamingEvent, EventType, create_delta_event, create_done_event


class DiffMode(Enum):
    """差分模式枚举"""
    CONSERVATIVE = "conservative"  # 保守模式：仅识别 append 与 index 替换
    SMART = "smart"              # 智能模式：基于 LCS 做最小编辑序列


@dataclass
class PathState:
    """路径状态信息"""
    path: str
    last_emitted_hash: Optional[str] = None
    last_emit_time: Optional[datetime] = None
    emit_count: int = 0
    coalesced_count: int = 0
    is_stable: bool = False
    stability_ticks: int = 0
    
    def update_hash(self, value: Any) -> str:
        """更新路径值的哈希
        
        Args:
            value: 路径对应的值
            
        Returns:
            str: 计算得到的哈希值
        """
        value_str = json.dumps(value, sort_keys=True, ensure_ascii=False)
        new_hash = hashlib.md5(value_str.encode('utf-8')).hexdigest()
        self.last_emitted_hash = new_hash
        self.last_emit_time = datetime.now()
        self.emit_count += 1
        return new_hash
    
    def should_emit(self, value: Any) -> bool:
        """判断是否应该发射事件
        
        Args:
            value: 当前值
            
        Returns:
            bool: 是否应该发射事件
        """
        if self.last_emitted_hash is None:
            return True
        
        value_str = json.dumps(value, sort_keys=True, ensure_ascii=False)
        current_hash = hashlib.md5(value_str.encode('utf-8')).hexdigest()
        return current_hash != self.last_emitted_hash


@dataclass
class DiffResult:
    """差分结果"""
    path: str
    diff_type: str  # 'added', 'modified', 'removed', 'list_append', 'list_insert', 'list_remove'
    old_value: Any = None
    new_value: Any = None
    delta_value: Any = None
    confidence: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CoalescingConfig:
    """事件合并配置"""
    enabled: bool = True
    time_window_ms: int = 100  # 时间窗口（毫秒）
    max_coalesced_events: int = 10  # 最大合并事件数
    stability_threshold: int = 3  # 稳定性阈值（连续无变更的 tick 数）


class StructuredDiffEngine:
    """结构化差分引擎
    
    提供 dict/list aware 的最小差分算法，支持事件去重与合并，
    实现幂等事件派发与 DONE 条件收敛。
    """
    
    def __init__(
        self,
        diff_mode: DiffMode = DiffMode.SMART,
        list_threshold: int = 1000,
        coalescing_config: Optional[CoalescingConfig] = None
    ):
        """初始化结构化差分引擎
        
        Args:
            diff_mode: 差分模式
            list_threshold: 列表差分阈值，超过此长度使用保守模式
            coalescing_config: 事件合并配置
        """
        self.diff_mode = diff_mode
        self.list_threshold = list_threshold
        self.coalescing_config = coalescing_config or CoalescingConfig()
        
        # 路径状态管理
        self.path_states: Dict[str, PathState] = {}
        
        # 事件合并缓冲区
        self.coalescing_buffer: Dict[str, List[StreamingEvent]] = {}
        
        # 统计信息
        self.stats = {
            "total_diffs": 0,
            "suppressed_duplicates": 0,
            "coalesced_events": 0,
            "done_events_emitted": 0
        }
    
    def compute_diff(
        self,
        old_data: Dict[str, Any],
        new_data: Dict[str, Any],
        base_path: str = ""
    ) -> List[DiffResult]:
        """计算两个数据结构之间的差分
        
        Args:
            old_data: 旧数据
            new_data: 新数据
            base_path: 基础路径
            
        Returns:
            List[DiffResult]: 差分结果列表
        """
        self.stats["total_diffs"] += 1
        
        if old_data is None:
            old_data = {}
        if new_data is None:
            new_data = {}
        
        diffs = []
        
        # 处理字典差分
        if isinstance(new_data, dict):
            diffs.extend(self._diff_dict(old_data, new_data, base_path))
        elif isinstance(new_data, list):
            diffs.extend(self._diff_list(old_data, new_data, base_path))
        else:
            # 基本类型差分
            if old_data != new_data:
                diffs.append(DiffResult(
                    path=base_path,
                    diff_type="modified",
                    old_value=old_data,
                    new_value=new_data,
                    delta_value=new_data
                ))
        
        return diffs
    
    def _diff_dict(
        self,
        old_dict: Dict[str, Any],
        new_dict: Dict[str, Any],
        base_path: str
    ) -> List[DiffResult]:
        """计算字典差分
        
        Args:
            old_dict: 旧字典
            new_dict: 新字典
            base_path: 基础路径
            
        Returns:
            List[DiffResult]: 差分结果列表
        """
        diffs = []
        
        if not isinstance(old_dict, dict):
            old_dict = {}
        
        # 获取所有键的并集
        all_keys = set(old_dict.keys()) | set(new_dict.keys())
        
        for key in all_keys:
            current_path = f"{base_path}.{key}" if base_path else key
            
            old_value = old_dict.get(key)
            new_value = new_dict.get(key)
            
            if key not in old_dict:
                # 新增键
                diffs.append(DiffResult(
                    path=current_path,
                    diff_type="added",
                    old_value=None,
                    new_value=new_value,
                    delta_value=new_value
                ))
            elif key not in new_dict:
                # 删除键
                diffs.append(DiffResult(
                    path=current_path,
                    diff_type="removed",
                    old_value=old_value,
                    new_value=None,
                    delta_value=None
                ))
            elif old_value != new_value:
                # 递归处理嵌套结构
                if isinstance(new_value, (dict, list)):
                    nested_diffs = self.compute_diff(old_value, new_value, current_path)
                    diffs.extend(nested_diffs)
                else:
                    # 值修改
                    diffs.append(DiffResult(
                        path=current_path,
                        diff_type="modified",
                        old_value=old_value,
                        new_value=new_value,
                        delta_value=self._calculate_delta(old_value, new_value)
                    ))
        
        return diffs
    
    def _diff_list(
        self,
        old_list: List[Any],
        new_list: List[Any],
        base_path: str
    ) -> List[DiffResult]:
        """计算列表差分
        
        Args:
            old_list: 旧列表
            new_list: 新列表
            base_path: 基础路径
            
        Returns:
            List[DiffResult]: 差分结果列表
        """
        diffs = []
        
        if not isinstance(old_list, list):
            old_list = []
        
        # 根据列表长度和模式选择差分策略
        if (len(new_list) > self.list_threshold or 
            self.diff_mode == DiffMode.CONSERVATIVE):
            diffs.extend(self._diff_list_conservative(old_list, new_list, base_path))
        else:
            diffs.extend(self._diff_list_smart(old_list, new_list, base_path))
        
        return diffs
    
    def _diff_list_conservative(
        self,
        old_list: List[Any],
        new_list: List[Any],
        base_path: str
    ) -> List[DiffResult]:
        """保守模式列表差分：仅识别 append 与 index 替换
        
        Args:
            old_list: 旧列表
            new_list: 新列表
            base_path: 基础路径
            
        Returns:
            List[DiffResult]: 差分结果列表
        """
        diffs = []
        
        old_len = len(old_list)
        new_len = len(new_list)
        
        # 处理现有元素的修改
        for i in range(min(old_len, new_len)):
            current_path = f"{base_path}[{i}]"
            if old_list[i] != new_list[i]:
                if isinstance(new_list[i], (dict, list)):
                    # 递归处理嵌套结构
                    nested_diffs = self.compute_diff(old_list[i], new_list[i], current_path)
                    diffs.extend(nested_diffs)
                else:
                    diffs.append(DiffResult(
                        path=current_path,
                        diff_type="modified",
                        old_value=old_list[i],
                        new_value=new_list[i],
                        delta_value=new_list[i]
                    ))
        
        # 处理新增元素（append）
        if new_len > old_len:
            for i in range(old_len, new_len):
                current_path = f"{base_path}[{i}]"
                diffs.append(DiffResult(
                    path=current_path,
                    diff_type="list_append",
                    old_value=None,
                    new_value=new_list[i],
                    delta_value=new_list[i]
                ))
        
        # 处理删除元素
        elif new_len < old_len:
            for i in range(new_len, old_len):
                current_path = f"{base_path}[{i}]"
                diffs.append(DiffResult(
                    path=current_path,
                    diff_type="list_remove",
                    old_value=old_list[i],
                    new_value=None,
                    delta_value=None
                ))
        
        return diffs
    
    def _diff_list_smart(
        self,
        old_list: List[Any],
        new_list: List[Any],
        base_path: str
    ) -> List[DiffResult]:
        """智能模式列表差分：基于 LCS 做最小编辑序列
        
        Args:
            old_list: 旧列表
            new_list: 新列表
            base_path: 基础路径
            
        Returns:
            List[DiffResult]: 差分结果列表
        """
        # 简化版 LCS 实现，实际项目中可以使用更高效的算法
        diffs = []
        
        # 对于简单情况，回退到保守模式
        if len(old_list) == 0:
            for i, item in enumerate(new_list):
                current_path = f"{base_path}[{i}]"
                diffs.append(DiffResult(
                    path=current_path,
                    diff_type="list_append",
                    old_value=None,
                    new_value=item,
                    delta_value=item
                ))
        elif len(new_list) == 0:
            for i, item in enumerate(old_list):
                current_path = f"{base_path}[{i}]"
                diffs.append(DiffResult(
                    path=current_path,
                    diff_type="list_remove",
                    old_value=item,
                    new_value=None,
                    delta_value=None
                ))
        else:
            # 简化处理：检查是否为简单的 append 操作
            if (len(new_list) > len(old_list) and 
                new_list[:len(old_list)] == old_list):
                # 简单 append
                for i in range(len(old_list), len(new_list)):
                    current_path = f"{base_path}[{i}]"
                    diffs.append(DiffResult(
                        path=current_path,
                        diff_type="list_append",
                        old_value=None,
                        new_value=new_list[i],
                        delta_value=new_list[i]
                    ))
            else:
                # 复杂情况，回退到保守模式
                diffs.extend(self._diff_list_conservative(old_list, new_list, base_path))
        
        return diffs
    
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
    
    def should_emit_event(self, path: str, value: Any) -> bool:
        """判断是否应该发射事件（基于幂等性检查）
        
        Args:
            path: 路径
            value: 值
            
        Returns:
            bool: 是否应该发射事件
        """
        if path not in self.path_states:
            self.path_states[path] = PathState(path=path)
        
        path_state = self.path_states[path]
        
        if path_state.should_emit(value):
            return True
        else:
            self.stats["suppressed_duplicates"] += 1
            return False
    
    def emit_delta_event(
        self,
        diff_result: DiffResult,
        session_id: str,
        sequence_number: int
    ) -> Optional[StreamingEvent]:
        """发射增量事件（带幂等性检查）
        
        Args:
            diff_result: 差分结果
            session_id: 会话ID
            sequence_number: 序列号
            
        Returns:
            Optional[StreamingEvent]: 事件对象，如果被抑制则返回 None
        """
        if not self.should_emit_event(diff_result.path, diff_result.new_value):
            return None
        
        # 更新路径状态
        path_state = self.path_states[diff_result.path]
        path_state.update_hash(diff_result.new_value)
        
        # 创建事件
        event = create_delta_event(
            path=diff_result.path,
            value=diff_result.new_value,
            delta_value=diff_result.delta_value,
            session_id=session_id,
            sequence_number=sequence_number,
            previous_value=diff_result.old_value,
            is_partial=self._is_value_partial(diff_result.new_value),
            metadata={
                "diff_type": diff_result.diff_type,
                "confidence": diff_result.confidence,
                **diff_result.metadata
            }
        )
        
        # 如果启用了事件合并，添加到缓冲区
        if self.coalescing_config.enabled:
            self._add_to_coalescing_buffer(event)
            return None  # 事件将在合并后发射
        
        return event
    
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
    
    def _add_to_coalescing_buffer(self, event: StreamingEvent):
        """添加事件到合并缓冲区
        
        Args:
            event: 流式事件
        """
        path = event.data.path
        
        if path not in self.coalescing_buffer:
            self.coalescing_buffer[path] = []
        
        self.coalescing_buffer[path].append(event)
        
        # 检查是否需要立即合并
        if len(self.coalescing_buffer[path]) >= self.coalescing_config.max_coalesced_events:
            self._flush_coalescing_buffer(path)
    
    def _flush_coalescing_buffer(self, path: str) -> List[StreamingEvent]:
        """刷新指定路径的合并缓冲区
        
        Args:
            path: 路径
            
        Returns:
            List[StreamingEvent]: 合并后的事件列表
        """
        if path not in self.coalescing_buffer or not self.coalescing_buffer[path]:
            return []
        
        events = self.coalescing_buffer[path]
        self.coalescing_buffer[path] = []
        
        if len(events) == 1:
            return events
        
        # 合并事件：保留最后一个事件，更新合并计数
        final_event = events[-1]
        coalesced_count = len(events) - 1
        
        # 更新事件元数据
        if final_event.data.metadata is None:
            final_event.data.metadata = {}
        
        final_event.data.metadata["coalesced_count"] = coalesced_count
        final_event.data.metadata["is_coalesced"] = True
        
        self.stats["coalesced_events"] += coalesced_count
        
        return [final_event]
    
    def flush_all_coalescing_buffers(self) -> List[StreamingEvent]:
        """刷新所有合并缓冲区
        
        Returns:
            List[StreamingEvent]: 所有合并后的事件列表
        """
        all_events = []
        
        for path in list(self.coalescing_buffer.keys()):
            events = self._flush_coalescing_buffer(path)
            all_events.extend(events)
        
        return all_events
    
    def check_stability_and_emit_done(
        self,
        session_id: str,
        sequence_number_generator: callable,
        current_data: Dict[str, Any] = None
    ) -> List[StreamingEvent]:
        """检查路径稳定性并发射 DONE 事件
        
        Args:
            session_id: 会话ID
            sequence_number_generator: 序列号生成器函数
            
        Returns:
            List[StreamingEvent]: DONE 事件列表
        """
        done_events = []
        current_time = datetime.now()
        
        for path, path_state in self.path_states.items():
            # 检查稳定性条件
            if (path_state.last_emit_time and 
                not path_state.is_stable and
                (current_time - path_state.last_emit_time).total_seconds() * 1000 >= 
                self.coalescing_config.time_window_ms):
                
                path_state.stability_ticks += 1
                
                # 达到稳定性阈值
                if path_state.stability_ticks >= self.coalescing_config.stability_threshold:
                    path_state.is_stable = True
                    
                    # 获取当前值
                    current_value = None
                    if current_data:
                        from .path_builder import PathBuilder
                        path_builder = PathBuilder()
                        success, value = path_builder.get_value_at_path(current_data, path)
                        if success:
                            current_value = value
                    
                    done_event = create_done_event(
                        path=path,
                        final_value=current_value,
                        session_id=session_id,
                        sequence_number=sequence_number_generator(),
                        validation_passed=True,
                        metadata={
                            "stability_ticks": path_state.stability_ticks,
                            "emit_count": path_state.emit_count
                        }
                    )
                    
                    done_events.append(done_event)
                    self.stats["done_events_emitted"] += 1
        
        return done_events
    
    def reset_path_stability(self, path: str):
        """重置路径稳定性状态
        
        Args:
            path: 路径
        """
        if path in self.path_states:
            self.path_states[path].is_stable = False
            self.path_states[path].stability_ticks = 0
    
    def get_path_state(self, path: str) -> Optional[PathState]:
        """获取路径状态
        
        Args:
            path: 路径
            
        Returns:
            Optional[PathState]: 路径状态
        """
        return self.path_states.get(path)
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息
        
        Returns:
            Dict[str, Any]: 统计信息
        """
        return {
            **self.stats,
            "active_paths": len(self.path_states),
            "stable_paths": sum(1 for ps in self.path_states.values() if ps.is_stable),
            "buffered_events": sum(len(events) for events in self.coalescing_buffer.values())
        }
    
    def cleanup_old_paths(self, max_age_hours: int = 24):
        """清理过期的路径状态
        
        Args:
            max_age_hours: 最大保留时间（小时）
        """
        current_time = datetime.now()
        cutoff_time = current_time - timedelta(hours=max_age_hours)
        
        paths_to_remove = []
        for path, path_state in self.path_states.items():
            if (path_state.last_emit_time and 
                path_state.last_emit_time < cutoff_time):
                paths_to_remove.append(path)
        
        for path in paths_to_remove:
            del self.path_states[path]
            if path in self.coalescing_buffer:
                del self.coalescing_buffer[path]


# 便捷函数
def create_diff_engine(
    mode: str = "smart",
    list_threshold: int = 1000,
    coalescing_enabled: bool = True,
    time_window_ms: int = 100
) -> StructuredDiffEngine:
    """创建差分引擎的便捷函数
    
    Args:
        mode: 差分模式（"conservative" 或 "smart"）
        list_threshold: 列表差分阈值
        coalescing_enabled: 是否启用事件合并
        time_window_ms: 合并时间窗口（毫秒）
        
    Returns:
        StructuredDiffEngine: 差分引擎实例
    """
    diff_mode = DiffMode.SMART if mode == "smart" else DiffMode.CONSERVATIVE
    coalescing_config = CoalescingConfig(
        enabled=coalescing_enabled,
        time_window_ms=time_window_ms
    )
    
    return StructuredDiffEngine(
        diff_mode=diff_mode,
        list_threshold=list_threshold,
        coalescing_config=coalescing_config
    )