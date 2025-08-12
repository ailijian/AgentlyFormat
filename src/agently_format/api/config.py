"""API配置模块

管理FastAPI应用的配置参数。
"""

import os
from typing import Optional, List
from pydantic_settings import BaseSettings
from pydantic import Field
from functools import lru_cache


class Settings(BaseSettings):
    """应用配置"""
    
    # 应用基础配置
    app_name: str = Field(default="Agently Format API", description="应用名称")
    app_version: str = Field(default="1.0.0", description="应用版本")
    debug: bool = Field(default=False, description="调试模式")
    
    # 服务器配置
    host: str = Field(default="0.0.0.0", description="服务器地址")
    port: int = Field(default=8000, description="服务器端口")
    workers: int = Field(default=1, description="工作进程数")
    
    # API配置
    api_prefix: str = Field(default="/api/v1", description="API前缀")
    docs_url: Optional[str] = Field(default="/docs", description="文档URL")
    redoc_url: Optional[str] = Field(default="/redoc", description="ReDoc URL")
    openapi_url: Optional[str] = Field(default="/openapi.json", description="OpenAPI URL")
    
    # CORS配置
    cors_origins: List[str] = Field(
        default=["*"],
        description="允许的CORS源"
    )
    cors_methods: List[str] = Field(
        default=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        description="允许的CORS方法"
    )
    cors_headers: List[str] = Field(
        default=["*"],
        description="允许的CORS头"
    )
    
    # 安全配置
    secret_key: str = Field(
        default="your-secret-key-change-in-production",
        description="密钥"
    )
    access_token_expire_minutes: int = Field(
        default=30,
        description="访问令牌过期时间（分钟）"
    )
    
    # 限流配置
    rate_limit_enabled: bool = Field(default=True, description="是否启用限流")
    rate_limit_requests: int = Field(default=100, description="限流请求数")
    rate_limit_window: int = Field(default=60, description="限流时间窗口（秒）")
    
    # 日志配置
    log_level: str = Field(default="INFO", description="日志级别")
    log_format: str = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        description="日志格式"
    )
    log_file: Optional[str] = Field(default=None, description="日志文件路径")
    
    # 数据库配置（如果需要）
    database_url: Optional[str] = Field(default=None, description="数据库URL")
    
    # Redis配置（如果需要缓存）
    redis_url: Optional[str] = Field(default=None, description="Redis URL")
    
    # 模型配置
    default_model_type: str = Field(default="openai", description="默认模型类型")
    default_model_name: str = Field(default="gpt-3.5-turbo", description="默认模型名称")
    
    # 解析配置
    max_content_length: int = Field(
        default=10 * 1024 * 1024,  # 10MB
        description="最大内容长度"
    )
    max_session_duration: int = Field(
        default=3600,  # 1小时
        description="最大会话持续时间（秒）"
    )
    cleanup_interval: int = Field(
        default=300,  # 5分钟
        description="清理间隔（秒）"
    )
    
    # 监控配置
    metrics_enabled: bool = Field(default=True, description="是否启用指标")
    health_check_enabled: bool = Field(default=True, description="是否启用健康检查")
    
    # 文件上传配置
    upload_max_size: int = Field(
        default=50 * 1024 * 1024,  # 50MB
        description="上传文件最大大小"
    )
    upload_allowed_types: List[str] = Field(
        default=["application/json", "text/plain"],
        description="允许的上传文件类型"
    )
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        
        # 环境变量前缀
        env_prefix = "AGENTLY_"
        
        # 字段别名
        fields = {
            "app_name": {"env": "APP_NAME"},
            "app_version": {"env": "APP_VERSION"},
            "debug": {"env": "DEBUG"},
            "host": {"env": "HOST"},
            "port": {"env": "PORT"},
            "secret_key": {"env": "SECRET_KEY"},
            "database_url": {"env": "DATABASE_URL"},
            "redis_url": {"env": "REDIS_URL"},
        }


class DevelopmentSettings(Settings):
    """开发环境配置"""
    debug: bool = True
    log_level: str = "DEBUG"
    cors_origins: List[str] = ["*"]


class ProductionSettings(Settings):
    """生产环境配置"""
    debug: bool = False
    log_level: str = "INFO"
    docs_url: Optional[str] = None  # 生产环境关闭文档
    redoc_url: Optional[str] = None
    openapi_url: Optional[str] = None


class TestingSettings(Settings):
    """测试环境配置"""
    debug: bool = True
    log_level: str = "DEBUG"
    database_url: str = "sqlite:///./test.db"


@lru_cache()
def get_settings() -> Settings:
    """获取配置实例
    
    Returns:
        Settings: 配置实例
    """
    environment = os.getenv("ENVIRONMENT", "development").lower()
    
    if environment == "production":
        return ProductionSettings()
    elif environment == "testing":
        return TestingSettings()
    else:
        return DevelopmentSettings()


def get_database_url() -> Optional[str]:
    """获取数据库URL
    
    Returns:
        Optional[str]: 数据库URL
    """
    settings = get_settings()
    return settings.database_url


def get_redis_url() -> Optional[str]:
    """获取Redis URL
    
    Returns:
        Optional[str]: Redis URL
    """
    settings = get_settings()
    return settings.redis_url


def is_debug_mode() -> bool:
    """是否为调试模式
    
    Returns:
        bool: 是否为调试模式
    """
    settings = get_settings()
    return settings.debug


def get_cors_config() -> dict:
    """获取CORS配置
    
    Returns:
        dict: CORS配置
    """
    settings = get_settings()
    return {
        "allow_origins": settings.cors_origins,
        "allow_methods": settings.cors_methods,
        "allow_headers": settings.cors_headers,
        "allow_credentials": True,
    }


def get_rate_limit_config() -> dict:
    """获取限流配置
    
    Returns:
        dict: 限流配置
    """
    settings = get_settings()
    return {
        "enabled": settings.rate_limit_enabled,
        "requests": settings.rate_limit_requests,
        "window": settings.rate_limit_window,
    }