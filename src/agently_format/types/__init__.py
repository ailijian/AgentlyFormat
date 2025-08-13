"""核心数据类型定义模块

包含事件、模型配置、请求响应和JSON模式等核心数据类型。
"""

from .events import StreamingEvent, EventType, EventData
from .models import ModelConfig, ParseRequest, ParseResponse, ModelType, ChatMessage
from .schemas import JSONSchema, FieldType, ValidationRule

# 从其他模块导入类型
from ..core.json_completer import CompletionStrategy
from ..core.path_builder import PathStyle

# 创建类型别名以保持向后兼容
ParseEvent = StreamingEvent  # ParseEvent 是 StreamingEvent 的别名
ParseEventType = EventType   # ParseEventType 是 EventType 的别名

__all__ = [
    "StreamingEvent",
    "EventType", 
    "EventData",
    "ModelConfig",
    "ParseRequest",
    "ParseResponse",
    "ModelType",
    "JSONSchema",
    "FieldType",
    "ValidationRule",
    # 新增的类型
    "CompletionStrategy",
    "PathStyle",
    "ChatMessage",
    # 类型别名
    "ParseEvent",
    "ParseEventType",
]