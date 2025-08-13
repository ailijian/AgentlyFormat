"""API数据模型

定义FastAPI的请求和响应模型。
"""

from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field, field_validator
from enum import Enum
from datetime import datetime

from ..types.models import ModelType
from ..types.events import EventType


class StatusEnum(str, Enum):
    """状态枚举"""
    SUCCESS = "success"
    ERROR = "error"
    PROCESSING = "processing"
    PENDING = "pending"


class CompletionStrategyEnum(str, Enum):
    """补全策略枚举"""
    CONSERVATIVE = "conservative"
    SMART = "smart"
    AGGRESSIVE = "aggressive"


class PathStyleEnum(str, Enum):
    """路径风格枚举"""
    DOT = "dot"
    SLASH = "slash"
    BRACKET = "bracket"
    MIXED = "mixed"


# 基础响应模型
class BaseResponse(BaseModel):
    """基础响应模型"""
    status: StatusEnum = Field(description="响应状态")
    message: str = Field(description="响应消息")
    timestamp: datetime = Field(default_factory=datetime.now, description="时间戳")
    request_id: Optional[str] = Field(None, description="请求ID")


class ErrorResponse(BaseResponse):
    """错误响应模型"""
    status: StatusEnum = StatusEnum.ERROR
    error_code: Optional[str] = Field(None, description="错误代码")
    error_details: Optional[Dict[str, Any]] = Field(None, description="错误详情")


# 模型配置相关
class ModelConfigRequest(BaseModel):
    """模型配置请求"""
    model_type: ModelType = Field(description="模型类型")
    model_name: str = Field(description="模型名称")
    api_key: str = Field(description="API密钥")
    base_url: Optional[str] = Field(None, description="基础URL")
    api_version: Optional[str] = Field(None, description="API版本")
    request_params: Optional[Dict[str, Any]] = Field(default_factory=dict, description="请求参数")
    headers: Optional[Dict[str, str]] = Field(default_factory=dict, description="请求头")
    timeout: Optional[int] = Field(30, description="超时时间")
    
    class Config:
        schema_extra = {
            "example": {
                "model_type": "openai",
                "model_name": "gpt-3.5-turbo",
                "api_key": "sk-...",
                "base_url": "https://api.openai.com/v1",
                "request_params": {
                    "temperature": 0.7,
                    "max_tokens": 1000
                }
            }
        }


class ModelConfigResponse(BaseResponse):
    """模型配置响应"""
    status: StatusEnum = StatusEnum.SUCCESS
    config_id: str = Field(description="配置ID")
    model_info: Dict[str, Any] = Field(description="模型信息")


# JSON补全相关
class JSONCompleteRequest(BaseModel):
    """JSON补全请求"""
    content: str = Field(description="待补全的JSON内容")
    strategy: CompletionStrategyEnum = Field(
        default=CompletionStrategyEnum.SMART,
        description="补全策略"
    )
    max_depth: Optional[int] = Field(10, description="最大深度")
    
    @field_validator('content')
    @classmethod
    def validate_content(cls, v):
        if not v or not v.strip():
            raise ValueError("Content cannot be empty")
        return v
    
    class Config:
        schema_extra = {
            "example": {
                "content": '{"name": "John", "age": 30, "city"',
                "strategy": "smart",
                "max_depth": 10
            }
        }


class JSONCompleteResponse(BaseResponse):
    """JSON补全响应"""
    status: StatusEnum = StatusEnum.SUCCESS
    completed_json: str = Field(description="补全后的JSON")
    is_valid: bool = Field(description="是否为有效JSON")
    changes_made: bool = Field(description="是否进行了修改")
    confidence: float = Field(description="置信度")


# 路径构建相关
class PathBuildRequest(BaseModel):
    """路径构建请求"""
    data: Dict[str, Any] = Field(description="数据对象")
    style: PathStyleEnum = Field(
        default=PathStyleEnum.DOT,
        description="路径风格"
    )
    include_arrays: bool = Field(True, description="是否包含数组索引")
    
    class Config:
        schema_extra = {
            "example": {
                "data": {
                    "user": {
                        "name": "John",
                        "addresses": [
                            {"city": "New York"},
                            {"city": "Boston"}
                        ]
                    }
                },
                "style": "dot",
                "include_arrays": True
            }
        }


class PathBuildResponse(BaseResponse):
    """路径构建响应"""
    status: StatusEnum = StatusEnum.SUCCESS
    paths: List[str] = Field(description="生成的路径列表")
    total_paths: int = Field(description="路径总数")


# 流式解析相关
class StreamParseRequest(BaseModel):
    """流式解析请求"""
    session_id: Optional[str] = Field(None, description="会话ID")
    chunk: str = Field(description="数据块")
    is_final: bool = Field(False, description="是否为最后一块")
    expected_schema: Optional[Dict[str, Any]] = Field(None, description="期望的JSON模式")
    
    @field_validator('chunk')
    @classmethod
    def validate_chunk(cls, v):
        if not isinstance(v, str):
            raise ValueError("Chunk must be a string")
        return v
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "session_id": "session_123",
                "chunk": '{"name": "John"',
                "is_final": False,
                "expected_schema": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "age": {"type": "number"}
                    }
                }
            }
        }
    }


class StreamParseResponse(BaseResponse):
    """流式解析响应"""
    status: StatusEnum = StatusEnum.SUCCESS
    session_id: str = Field(description="会话ID")
    events: List[Dict[str, Any]] = Field(description="事件列表")
    current_data: Optional[Dict[str, Any]] = Field(None, description="当前解析的数据")
    is_complete: bool = Field(description="是否解析完成")
    progress: float = Field(description="解析进度")


# 模型聊天相关
class ChatMessage(BaseModel):
    """聊天消息"""
    role: str = Field(description="角色")
    content: str = Field(description="内容")
    
    @field_validator('role')
    @classmethod
    def validate_role(cls, v):
        if v not in ['system', 'user', 'assistant']:
            raise ValueError("Role must be one of: system, user, assistant")
        return v


class ChatRequest(BaseModel):
    """聊天请求"""
    messages: List[ChatMessage] = Field(description="消息列表")
    model_config_data: Optional[ModelConfigRequest] = Field(None, description="模型配置", alias="model_config")
    config_id: Optional[str] = Field(None, description="配置ID")
    stream: bool = Field(False, description="是否流式返回")
    expected_format: Optional[str] = Field(None, description="期望的返回格式")
    
    @field_validator('messages')
    @classmethod
    def validate_messages(cls, v):
        if not v:
            raise ValueError("Messages cannot be empty")
        return v
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "messages": [
                    {"role": "user", "content": "Generate a JSON object with user information"}
                ],
                "stream": False,
                "expected_format": "json"
            }
        }
    }


class ChatResponse(BaseResponse):
    """聊天响应"""
    status: StatusEnum = StatusEnum.SUCCESS
    content: str = Field(description="响应内容")
    usage: Optional[Dict[str, Any]] = Field(None, description="使用统计")
    model: Optional[str] = Field(None, description="使用的模型")
    finish_reason: Optional[str] = Field(None, description="完成原因")


# 健康检查相关
class HealthCheckResponse(BaseResponse):
    """健康检查响应"""
    status: StatusEnum = StatusEnum.SUCCESS
    version: str = Field(description="版本号")
    uptime: float = Field(description="运行时间（秒）")
    dependencies: Dict[str, str] = Field(description="依赖状态")


# 统计信息相关
class StatsResponse(BaseResponse):
    """统计信息响应"""
    status: StatusEnum = StatusEnum.SUCCESS
    total_requests: int = Field(description="总请求数")
    active_sessions: int = Field(description="活跃会话数")
    total_events: int = Field(description="总事件数")
    events_by_type: Dict[str, int] = Field(description="按类型分组的事件数")
    average_response_time: float = Field(description="平均响应时间")
    error_rate: float = Field(description="错误率")
    uptime: float = Field(description="运行时间")


# 会话管理相关
class SessionCreateRequest(BaseModel):
    """会话创建请求"""
    session_id: Optional[str] = Field(None, description="自定义会话ID")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="元数据")
    ttl: Optional[int] = Field(3600, description="生存时间（秒）")


class SessionCreateResponse(BaseResponse):
    """会话创建响应"""
    status: StatusEnum = StatusEnum.SUCCESS
    session_id: str = Field(description="会话ID")
    expires_at: datetime = Field(description="过期时间")


class SessionInfoResponse(BaseResponse):
    """会话信息响应"""
    status: StatusEnum = StatusEnum.SUCCESS
    session_id: str = Field(description="会话ID")
    created_at: datetime = Field(description="创建时间")
    expires_at: datetime = Field(description="过期时间")
    metadata: Dict[str, Any] = Field(description="元数据")
    event_count: int = Field(description="事件数量")
    last_activity: Optional[datetime] = Field(None, description="最后活动时间")


# 批量处理相关
class BatchProcessRequest(BaseModel):
    """批量处理请求"""
    items: List[Dict[str, Any]] = Field(description="待处理项目列表")
    operation: str = Field(description="操作类型")
    options: Optional[Dict[str, Any]] = Field(default_factory=dict, description="选项")
    
    @field_validator('items')
    @classmethod
    def validate_items(cls, v):
        if not v:
            raise ValueError("Items cannot be empty")
        if len(v) > 100:  # 限制批量大小
            raise ValueError("Too many items, maximum 100 allowed")
        return v


class BatchProcessResponse(BaseResponse):
    """批量处理响应"""
    status: StatusEnum = StatusEnum.SUCCESS
    total_items: int = Field(description="总项目数")
    processed_items: int = Field(description="已处理项目数")
    failed_items: int = Field(description="失败项目数")
    results: List[Dict[str, Any]] = Field(description="处理结果")
    errors: List[Dict[str, Any]] = Field(description="错误信息")


# WebSocket相关
class WebSocketMessage(BaseModel):
    """WebSocket消息"""
    type: str = Field(description="消息类型")
    data: Dict[str, Any] = Field(description="消息数据")
    session_id: Optional[str] = Field(None, description="会话ID")
    timestamp: datetime = Field(default_factory=datetime.now, description="时间戳")


class WebSocketResponse(BaseModel):
    """WebSocket响应"""
    type: str = Field(description="响应类型")
    data: Dict[str, Any] = Field(description="响应数据")
    status: StatusEnum = Field(description="状态")
    session_id: Optional[str] = Field(None, description="会话ID")
    timestamp: datetime = Field(default_factory=datetime.now, description="时间戳")