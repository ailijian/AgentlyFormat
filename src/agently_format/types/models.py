"""模型配置和请求响应类型定义

定义与大模型交互相关的数据结构和配置。
"""

from enum import Enum
from typing import Any, Dict, List, Optional, Union, Callable
from dataclasses import dataclass, field
from datetime import datetime
import uuid


class ModelType(Enum):
    """支持的模型类型"""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    DOUBAO = "doubao"  # 豆包
    QWEN = "qwen"      # 通义千问
    BAIDU = "baidu"    # 百度文心
    DEEPSEEK = "deepseek"  # DeepSeek
    KIMI = "kimi"      # Kimi (月之暗面)
    CUSTOM = "custom"  # 自定义模型


@dataclass
class ModelConfig:
    """模型配置"""
    model_type: ModelType
    model_name: str
    api_key: str
    base_url: Optional[str] = None
    api_version: Optional[str] = None
    api_secret: Optional[str] = None  # 用于需要额外密钥的模型（如文心大模型）
    
    # 请求参数
    temperature: float = 0.7
    max_tokens: Optional[int] = None
    top_p: float = 1.0
    frequency_penalty: float = 0.0
    presence_penalty: float = 0.0
    
    # 流式配置
    stream: bool = True
    stream_options: Optional[Dict[str, Any]] = None
    
    # 超时和重试配置
    timeout: float = 30.0
    max_retries: int = 3
    retry_delay: float = 1.0
    
    # 自定义请求头
    headers: Optional[Dict[str, str]] = None
    
    # 额外的请求参数
    request_params: Optional[Dict[str, Any]] = None
    
    # 验证配置
    validate_response: bool = True
    
    def __post_init__(self):
        """初始化后验证"""
        if self.headers is None:
            self.headers = {}
        if self.stream_options is None:
            self.stream_options = {}
        if self.request_params is None:
            self.request_params = {}
            
        # 验证必要参数
        if not self.api_key:
            raise ValueError("API key is required")
        if not self.model_name:
            raise ValueError("Model name is required")
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "model_type": self.model_type.value,
            "model_name": self.model_name,
            "api_key": "***",  # 隐藏敏感信息
            "base_url": self.base_url,
            "api_version": self.api_version,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "top_p": self.top_p,
            "frequency_penalty": self.frequency_penalty,
            "presence_penalty": self.presence_penalty,
            "stream": self.stream,
            "timeout": self.timeout,
            "max_retries": self.max_retries,
            "retry_delay": self.retry_delay,
            "validate_response": self.validate_response
        }


@dataclass
class ParseRequest:
    """解析请求"""
    # 基本信息
    request_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = field(default_factory=datetime.now)
    
    # 输入数据
    prompt: str = ""
    system_prompt: Optional[str] = None
    messages: Optional[List[Dict[str, str]]] = None
    
    # 期望的JSON模式
    expected_schema: Optional[Dict[str, Any]] = None
    schema_strict: bool = False
    
    # 解析配置
    enable_streaming: bool = True
    enable_completion: bool = True
    completion_strategy: str = "smart"  # smart, aggressive, conservative
    
    # 事件回调
    on_delta: Optional[Callable] = None
    on_done: Optional[Callable] = None
    on_error: Optional[Callable] = None
    on_progress: Optional[Callable] = None
    
    # 验证配置
    validate_json: bool = True
    auto_fix_json: bool = True
    
    # 元数据
    metadata: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        """初始化后处理"""
        if self.messages is None:
            self.messages = []
        if self.metadata is None:
            self.metadata = {}
            
        # 如果提供了prompt但没有messages，自动构建messages
        if self.prompt and not self.messages:
            self.messages = [{"role": "user", "content": self.prompt}]
            
        # 如果提供了system_prompt，添加到messages开头
        if self.system_prompt:
            system_msg = {"role": "system", "content": self.system_prompt}
            if not any(msg.get("role") == "system" for msg in self.messages):
                self.messages.insert(0, system_msg)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "request_id": self.request_id,
            "timestamp": self.timestamp.isoformat(),
            "prompt": self.prompt,
            "system_prompt": self.system_prompt,
            "messages": self.messages,
            "expected_schema": self.expected_schema,
            "schema_strict": self.schema_strict,
            "enable_streaming": self.enable_streaming,
            "enable_completion": self.enable_completion,
            "completion_strategy": self.completion_strategy,
            "validate_json": self.validate_json,
            "auto_fix_json": self.auto_fix_json,
            "metadata": self.metadata
        }


@dataclass
class ParseResponse:
    """解析响应"""
    # 基本信息
    request_id: str
    response_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = field(default_factory=datetime.now)
    
    # 响应状态
    success: bool = True
    error_message: Optional[str] = None
    error_code: Optional[str] = None
    
    # 解析结果
    parsed_data: Optional[Dict[str, Any]] = None
    raw_content: str = ""
    completed_content: str = ""
    
    # 解析统计
    total_tokens: Optional[int] = None
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None
    
    # 解析过程信息
    parsing_duration: Optional[float] = None
    total_events: int = 0
    delta_events: int = 0
    done_events: int = 0
    error_events: int = 0
    
    # 验证结果
    validation_passed: bool = True
    validation_errors: Optional[List[str]] = None
    
    # 元数据
    metadata: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        """初始化后处理"""
        if self.validation_errors is None:
            self.validation_errors = []
        if self.metadata is None:
            self.metadata = {}
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "request_id": self.request_id,
            "response_id": self.response_id,
            "timestamp": self.timestamp.isoformat(),
            "success": self.success,
            "error_message": self.error_message,
            "error_code": self.error_code,
            "parsed_data": self.parsed_data,
            "raw_content": self.raw_content,
            "completed_content": self.completed_content,
            "total_tokens": self.total_tokens,
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "parsing_duration": self.parsing_duration,
            "total_events": self.total_events,
            "delta_events": self.delta_events,
            "done_events": self.done_events,
            "error_events": self.error_events,
            "validation_passed": self.validation_passed,
            "validation_errors": self.validation_errors,
            "metadata": self.metadata
        }
    
    def add_error(self, error_message: str, error_code: Optional[str] = None):
        """添加错误信息"""
        self.success = False
        self.error_message = error_message
        self.error_code = error_code
        self.error_events += 1
    
    def add_validation_error(self, error: str):
        """添加验证错误"""
        self.validation_passed = False
        if self.validation_errors is None:
            self.validation_errors = []
        self.validation_errors.append(error)


# 预定义的模型配置
PREDEFINED_MODELS = {
    ModelType.OPENAI: {
        "gpt-4": {
            "base_url": "https://api.openai.com/v1",
            "max_tokens": 8192
        },
        "gpt-3.5-turbo": {
            "base_url": "https://api.openai.com/v1",
            "max_tokens": 4096
        }
    },
    ModelType.DOUBAO: {
        "doubao-pro-4k": {
            "base_url": "https://ark.cn-beijing.volces.com/api/v3",
            "max_tokens": 4096
        },
        "doubao-lite-4k": {
            "base_url": "https://ark.cn-beijing.volces.com/api/v3",
            "max_tokens": 4096
        }
    },
    ModelType.BAIDU: {
        "ernie-4.0-8k": {
            "base_url": "https://aip.baidubce.com",
            "max_tokens": 4096
        },
        "ernie-3.5-8k": {
            "base_url": "https://aip.baidubce.com",
            "max_tokens": 4096
        },
        "ernie-turbo-8k": {
            "base_url": "https://aip.baidubce.com",
            "max_tokens": 4096
        }
    },
    ModelType.QWEN: {
        "qwen-turbo": {
            "base_url": "https://dashscope.aliyuncs.com/api/v1",
            "max_tokens": 8192
        },
        "qwen-plus": {
            "base_url": "https://dashscope.aliyuncs.com/api/v1",
            "max_tokens": 8192
        },
        "qwen-max": {
            "base_url": "https://dashscope.aliyuncs.com/api/v1",
            "max_tokens": 8192
        }
    },
    ModelType.DEEPSEEK: {
        "deepseek-chat": {
            "base_url": "https://api.deepseek.com/v1",
            "max_tokens": 4096
        },
        "deepseek-coder": {
            "base_url": "https://api.deepseek.com/v1",
            "max_tokens": 4096
        },
        "deepseek-reasoner": {
            "base_url": "https://api.deepseek.com/v1",
            "max_tokens": 8192
        }
    },
    ModelType.KIMI: {
        "moonshot-v1-8k": {
            "base_url": "https://api.moonshot.cn/v1",
            "max_tokens": 4096
        },
        "moonshot-v1-32k": {
            "base_url": "https://api.moonshot.cn/v1",
            "max_tokens": 4096
        },
        "moonshot-v1-128k": {
            "base_url": "https://api.moonshot.cn/v1",
            "max_tokens": 4096
        }
    },
    ModelType.CUSTOM: {
        # 为自定义模型提供默认配置
        "_default": {
            "base_url": "https://api.openai.com/v1",
            "max_tokens": 4096
        }
    }
}


@dataclass
class ChatMessage:
    """聊天消息"""
    role: str
    content: str
    
    def __post_init__(self):
        """验证角色"""
        if self.role not in ['system', 'user', 'assistant']:
            raise ValueError("Role must be one of: system, user, assistant")


def create_model_config(
    model_type: Union[ModelType, str],
    model_name: str,
    api_key: str,
    **kwargs
) -> ModelConfig:
    """创建模型配置的便捷函数"""
    # 转换字符串类型为枚举
    if isinstance(model_type, str):
        model_type = ModelType(model_type)
    
    # 获取预定义配置
    predefined = PREDEFINED_MODELS.get(model_type, {})
    model_config = predefined.get(model_name, {})
    
    # 如果没有找到特定模型配置，尝试使用默认配置
    if not model_config and "_default" in predefined:
        model_config = predefined["_default"]
    
    # 合并配置
    config_kwargs = {**model_config, **kwargs}
    
    return ModelConfig(
        model_type=model_type,
        model_name=model_name,
        api_key=api_key,
        **config_kwargs
    )