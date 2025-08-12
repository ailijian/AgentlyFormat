"""FastAPI应用

主应用文件，配置和启动FastAPI应用。
"""

import asyncio
from contextlib import asynccontextmanager
from typing import Dict, Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware

from .config import get_settings
from .middleware import setup_middleware
from .routes import router, cleanup_sessions
from ..core.event_system import get_global_emitter


# 应用生命周期管理
@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    settings = get_settings()
    
    # 启动时的初始化
    print(f"Starting {settings.app_name} v{settings.app_version}")
    print(f"Debug mode: {settings.debug}")
    
    # 启动后台任务
    cleanup_task = asyncio.create_task(cleanup_sessions())
    
    # 初始化事件系统
    emitter = get_global_emitter()
    
    try:
        yield
    finally:
        # 关闭时的清理
        print("Shutting down application...")
        
        # 取消后台任务
        cleanup_task.cancel()
        try:
            await cleanup_task
        except asyncio.CancelledError:
            pass
        
        # 关闭事件系统
        await emitter.close()
        
        print("Application shutdown complete")


def create_app() -> FastAPI:
    """创建FastAPI应用实例"""
    settings = get_settings()
    
    # 创建应用
    app = FastAPI(
        title=settings.app_name,
        description="Agently Format - 智能JSON格式化和流式解析服务",
        version=settings.app_version,
        debug=settings.debug,
        lifespan=lifespan,
        docs_url="/docs" if settings.debug else None,
        redoc_url="/redoc" if settings.debug else None,
        openapi_url="/openapi.json" if settings.debug else None
    )
    
    # 设置中间件
    setup_middleware(app)
    
    # 注册路由
    app.include_router(
        router,
        prefix=settings.api_prefix,
        tags=["AgentlyFormat"]
    )
    
    # 根路径
    @app.get("/")
    async def root():
        """根路径"""
        return {
            "name": settings.app_name,
            "version": settings.app_version,
            "description": "Agently Format - 智能JSON格式化和流式解析服务",
            "docs": "/docs" if settings.debug else None,
            "health": f"{settings.api_prefix}/health"
        }
    
    return app


# 创建应用实例
app = create_app()


if __name__ == "__main__":
    import uvicorn
    
    settings = get_settings()
    
    uvicorn.run(
        "agently_format.api.app:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level="debug" if settings.debug else "info",
        access_log=settings.log_level == "DEBUG"
    )