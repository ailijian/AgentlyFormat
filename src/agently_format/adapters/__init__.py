"""模型适配器模块

包含各种大模型的适配器实现，支持OpenAI、文心大模型、千问、豆包、DeepSeek、Kimi等模型。
"""

from .model_adapter import ModelAdapter, BaseModelAdapter
from .openai_adapter import OpenAIAdapter
from .doubao_adapter import DoubaoAdapter
from .wenxin_adapter import WenxinAdapter
from .qianwen_adapter import QianwenAdapter
from .deepseek_adapter import DeepSeekAdapter
from .kimi_adapter import KimiAdapter
from .custom_adapter import CustomAdapter
from .factory import ModelAdapterFactory

__all__ = [
    "ModelAdapter",
    "BaseModelAdapter",
    "OpenAIAdapter",
    "DoubaoAdapter",
    "WenxinAdapter",
    "QianwenAdapter",
    "DeepSeekAdapter",
    "KimiAdapter",
    "CustomAdapter",
    "ModelAdapterFactory",
]