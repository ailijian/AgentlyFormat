"""流式解析事件类型定义

定义流式JSON解析过程中的各种事件类型和数据结构。
"""

from enum import Enum
from typing import Any, Dict, List, Optional, Union
from dataclasses import dataclass
from datetime import datetime


class EventType(Enum):
    """事件类型枚举"""
    DELTA = "delta"  # 增量更新事件
    DONE = "done"    # 字段完成事件
    ERROR = "error"  # 错误事件
    START = "start"  # 解析开始事件
    FINISH = "finish"  # 解析完成事件
    PROGRESS = "progress"  # 进度更新事件


@dataclass
class EventData:
    """事件数据基类"""
    timestamp: datetime
    path: str
    value: Any = None
    metadata: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        """初始化后处理"""
        if self.metadata is None:
            self.metadata = {}


@dataclass
class DeltaEventData(EventData):
    """增量更新事件数据"""
    delta_value: Any = None
    previous_value: Any = None
    is_partial: bool = True


@dataclass
class DoneEventData(EventData):
    """完成事件数据"""
    final_value: Any = None
    is_complete: bool = True
    validation_passed: bool = True


class ErrorEventData(EventData):
    """错误事件数据"""
    
    def __init__(self, timestamp: datetime, path: str, error_type: str, error_message: str, 
                 value: Any = None, metadata: Optional[Dict[str, Any]] = None,
                 error_code: Optional[str] = None, stack_trace: Optional[str] = None):
        super().__init__(timestamp, path, value, metadata)
        self.error_type = error_type
        self.error_message = error_message
        self.error_code = error_code
        self.stack_trace = stack_trace


class ProgressEventData(EventData):
    """进度事件数据"""
    
    def __init__(self, timestamp: datetime, path: str, total_fields: int, completed_fields: int,
                 progress_percentage: float, value: Any = None, metadata: Optional[Dict[str, Any]] = None,
                 estimated_remaining_time: Optional[float] = None):
        super().__init__(timestamp, path, value, metadata)
        self.total_fields = total_fields
        self.completed_fields = completed_fields
        self.progress_percentage = progress_percentage
        self.estimated_remaining_time = estimated_remaining_time


@dataclass
class StreamingEvent:
    """流式解析事件"""
    event_type: EventType
    data: EventData
    session_id: str
    sequence_number: int
    
    def __post_init__(self):
        """验证事件数据类型匹配"""
        expected_data_types = {
            EventType.DELTA: DeltaEventData,
            EventType.DONE: DoneEventData,
            EventType.ERROR: ErrorEventData,
            EventType.PROGRESS: ProgressEventData,
        }
        
        if self.event_type in expected_data_types:
            expected_type = expected_data_types[self.event_type]
            if not isinstance(self.data, expected_type):
                raise TypeError(
                    f"Event type {self.event_type} requires data of type {expected_type.__name__}, "
                    f"got {type(self.data).__name__}"
                )
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "event_type": self.event_type.value,
            "data": {
                "timestamp": self.data.timestamp.isoformat(),
                "path": self.data.path,
                "value": self.data.value,
                "metadata": self.data.metadata,
                **self._get_specific_data_fields()
            },
            "session_id": self.session_id,
            "sequence_number": self.sequence_number
        }
    
    def _get_specific_data_fields(self) -> Dict[str, Any]:
        """获取特定事件类型的数据字段"""
        if isinstance(self.data, DeltaEventData):
            return {
                "delta_value": self.data.delta_value,
                "previous_value": self.data.previous_value,
                "is_partial": self.data.is_partial
            }
        elif isinstance(self.data, DoneEventData):
            return {
                "final_value": self.data.final_value,
                "is_complete": self.data.is_complete,
                "validation_passed": self.data.validation_passed
            }
        elif isinstance(self.data, ErrorEventData):
            return {
                "error_type": self.data.error_type,
                "error_message": self.data.error_message,
                "error_code": self.data.error_code,
                "stack_trace": self.data.stack_trace
            }
        elif isinstance(self.data, ProgressEventData):
            return {
                "total_fields": self.data.total_fields,
                "completed_fields": self.data.completed_fields,
                "progress_percentage": self.data.progress_percentage,
                "estimated_remaining_time": self.data.estimated_remaining_time
            }
        return {}


# 事件工厂函数
def create_delta_event(
    path: str,
    value: Any,
    delta_value: Any,
    session_id: str,
    sequence_number: int,
    previous_value: Any = None,
    is_partial: bool = True,
    metadata: Optional[Dict[str, Any]] = None
) -> StreamingEvent:
    """创建增量更新事件"""
    data = DeltaEventData(
        timestamp=datetime.now(),
        path=path,
        value=value,
        metadata=metadata,
        delta_value=delta_value,
        previous_value=previous_value,
        is_partial=is_partial
    )
    return StreamingEvent(EventType.DELTA, data, session_id, sequence_number)


def create_done_event(
    path: str,
    final_value: Any,
    session_id: str,
    sequence_number: int,
    validation_passed: bool = True,
    metadata: Optional[Dict[str, Any]] = None
) -> StreamingEvent:
    """创建完成事件"""
    data = DoneEventData(
        timestamp=datetime.now(),
        path=path,
        value=final_value,
        metadata=metadata,
        final_value=final_value,
        is_complete=True,
        validation_passed=validation_passed
    )
    return StreamingEvent(EventType.DONE, data, session_id, sequence_number)


def create_error_event(
    path: str,
    error_type: str,
    error_message: str,
    session_id: str,
    sequence_number: int,
    error_code: Optional[str] = None,
    stack_trace: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> StreamingEvent:
    """创建错误事件"""
    data = ErrorEventData(
        timestamp=datetime.now(),
        path=path,
        metadata=metadata,
        error_type=error_type,
        error_message=error_message,
        error_code=error_code,
        stack_trace=stack_trace
    )
    return StreamingEvent(EventType.ERROR, data, session_id, sequence_number)