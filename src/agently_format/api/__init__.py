"""FastAPI应用模块

提供RESTful API接口，支持流式JSON解析和模型适配。
"""

from .app import create_app, app
from .routes import router
from .models import *
from .middleware import setup_middleware
from .config import get_settings

__all__ = [
    "create_app",
    "app",
    "router",
    "setup_middleware",
    "get_settings",
]