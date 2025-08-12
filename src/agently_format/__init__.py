"""AgentlyFormat: 专注于大模型格式化输出结果的Python库

提供稳定可靠的JSON格式化解析能力，支持流式解析、智能补全和多模型适配。
"""

from .core.streaming_parser import StreamingParser
from .core.json_completer import JSONCompleter
from .core.path_builder import PathBuilder
from .adapters.model_adapter import ModelAdapter
from .types.events import StreamingEvent, EventType
from .types.models import ModelConfig, ParseRequest, ParseResponse
from .types.schemas import JSONSchema

__version__ = "0.1.0"
__author__ = "AgentEra"
__email__ = "support@agently.tech"

__all__ = [
    "StreamingParser",
    "JSONCompleter",
    "PathBuilder",
    "ModelAdapter",
    "StreamingEvent",
    "EventType",
    "ModelConfig",
    "ParseRequest",
    "ParseResponse",
    "JSONSchema",
]