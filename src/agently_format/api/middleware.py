"""API中间件

提供CORS、限流、日志、错误处理等中间件功能。
"""

import time
import uuid
import logging
from typing import Callable, Dict, Any
from collections import defaultdict, deque
from datetime import datetime, timedelta

from fastapi import FastAPI, Request, Response, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from .config import get_settings, get_cors_config, get_rate_limit_config
from .models import ErrorResponse, StatusEnum


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """请求日志中间件"""
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
        self.logger = logging.getLogger("api.requests")
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """处理请求
        
        Args:
            request: 请求对象
            call_next: 下一个处理器
            
        Returns:
            Response: 响应对象
        """
        # 生成请求ID
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        
        # 记录请求开始时间
        start_time = time.time()
        
        # 记录请求信息
        self.logger.info(
            f"Request started - ID: {request_id}, "
            f"Method: {request.method}, "
            f"URL: {request.url}, "
            f"Client: {request.client.host if request.client else 'unknown'}"
        )
        
        try:
            # 处理请求
            response = await call_next(request)
            
            # 计算处理时间
            process_time = time.time() - start_time
            
            # 添加响应头
            response.headers["X-Request-ID"] = request_id
            response.headers["X-Process-Time"] = str(process_time)
            
            # 记录响应信息
            self.logger.info(
                f"Request completed - ID: {request_id}, "
                f"Status: {response.status_code}, "
                f"Time: {process_time:.3f}s"
            )
            
            return response
            
        except Exception as e:
            # 计算处理时间
            process_time = time.time() - start_time
            
            # 记录错误信息
            self.logger.error(
                f"Request failed - ID: {request_id}, "
                f"Error: {str(e)}, "
                f"Time: {process_time:.3f}s"
            )
            
            # 返回错误响应
            error_response = ErrorResponse(
                message="Internal server error",
                error_code="INTERNAL_ERROR",
                request_id=request_id,
                error_details={"error": str(e)}
            )
            
            return JSONResponse(
                status_code=500,
                content=error_response.dict(),
                headers={
                    "X-Request-ID": request_id,
                    "X-Process-Time": str(process_time)
                }
            )


class RateLimitMiddleware(BaseHTTPMiddleware):
    """限流中间件"""
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
        self.config = get_rate_limit_config()
        self.requests: Dict[str, deque] = defaultdict(deque)
        self.logger = logging.getLogger("api.ratelimit")
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """处理请求
        
        Args:
            request: 请求对象
            call_next: 下一个处理器
            
        Returns:
            Response: 响应对象
        """
        if not self.config["enabled"]:
            return await call_next(request)
        
        # 获取客户端IP
        client_ip = self._get_client_ip(request)
        
        # 检查限流
        if self._is_rate_limited(client_ip):
            self.logger.warning(f"Rate limit exceeded for IP: {client_ip}")
            
            error_response = ErrorResponse(
                message="Rate limit exceeded",
                error_code="RATE_LIMIT_EXCEEDED",
                request_id=getattr(request.state, 'request_id', None)
            )
            
            return JSONResponse(
                status_code=429,
                content=error_response.dict(),
                headers={
                    "X-RateLimit-Limit": str(self.config["requests"]),
                    "X-RateLimit-Window": str(self.config["window"]),
                    "Retry-After": str(self.config["window"])
                }
            )
        
        # 记录请求
        self._record_request(client_ip)
        
        # 处理请求
        response = await call_next(request)
        
        # 添加限流信息到响应头
        remaining = self._get_remaining_requests(client_ip)
        response.headers["X-RateLimit-Limit"] = str(self.config["requests"])
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Window"] = str(self.config["window"])
        
        return response
    
    def _get_client_ip(self, request: Request) -> str:
        """获取客户端IP
        
        Args:
            request: 请求对象
            
        Returns:
            str: 客户端IP
        """
        # 检查代理头
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip
        
        # 使用客户端IP
        if request.client:
            return request.client.host
        
        return "unknown"
    
    def _is_rate_limited(self, client_ip: str) -> bool:
        """检查是否被限流
        
        Args:
            client_ip: 客户端IP
            
        Returns:
            bool: 是否被限流
        """
        now = datetime.now()
        window_start = now - timedelta(seconds=self.config["window"])
        
        # 清理过期请求
        while (self.requests[client_ip] and 
               self.requests[client_ip][0] < window_start):
            self.requests[client_ip].popleft()
        
        # 检查请求数量
        return len(self.requests[client_ip]) >= self.config["requests"]
    
    def _record_request(self, client_ip: str):
        """记录请求
        
        Args:
            client_ip: 客户端IP
        """
        self.requests[client_ip].append(datetime.now())
    
    def _get_remaining_requests(self, client_ip: str) -> int:
        """获取剩余请求数
        
        Args:
            client_ip: 客户端IP
            
        Returns:
            int: 剩余请求数
        """
        current_requests = len(self.requests[client_ip])
        return max(0, self.config["requests"] - current_requests)


class SecurityMiddleware(BaseHTTPMiddleware):
    """安全中间件"""
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
        self.settings = get_settings()
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """处理请求
        
        Args:
            request: 请求对象
            call_next: 下一个处理器
            
        Returns:
            Response: 响应对象
        """
        # 检查内容长度
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > self.settings.max_content_length:
            error_response = ErrorResponse(
                message="Request entity too large",
                error_code="ENTITY_TOO_LARGE"
            )
            return JSONResponse(
                status_code=413,
                content=error_response.dict()
            )
        
        # 处理请求
        response = await call_next(request)
        
        # 添加安全头
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        
        if not self.settings.debug:
            response.headers["Server"] = "AgentlyFormat"
        
        return response


class MetricsMiddleware(BaseHTTPMiddleware):
    """指标收集中间件"""
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
        self.metrics = {
            "total_requests": 0,
            "requests_by_method": defaultdict(int),
            "requests_by_status": defaultdict(int),
            "response_times": deque(maxlen=1000),
            "errors": 0,
            "start_time": datetime.now()
        }
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """处理请求
        
        Args:
            request: 请求对象
            call_next: 下一个处理器
            
        Returns:
            Response: 响应对象
        """
        start_time = time.time()
        
        # 更新请求计数
        self.metrics["total_requests"] += 1
        self.metrics["requests_by_method"][request.method] += 1
        
        try:
            response = await call_next(request)
            
            # 记录响应时间
            response_time = time.time() - start_time
            self.metrics["response_times"].append(response_time)
            
            # 记录状态码
            self.metrics["requests_by_status"][response.status_code] += 1
            
            # 记录错误
            if response.status_code >= 400:
                self.metrics["errors"] += 1
            
            return response
            
        except Exception as e:
            # 记录异常
            self.metrics["errors"] += 1
            self.metrics["requests_by_status"][500] += 1
            raise
    
    def get_metrics(self) -> Dict[str, Any]:
        """获取指标数据
        
        Returns:
            Dict[str, Any]: 指标数据
        """
        response_times = list(self.metrics["response_times"])
        avg_response_time = sum(response_times) / len(response_times) if response_times else 0
        
        uptime = (datetime.now() - self.metrics["start_time"]).total_seconds()
        error_rate = (self.metrics["errors"] / self.metrics["total_requests"] * 100 
                     if self.metrics["total_requests"] > 0 else 0)
        
        return {
            "total_requests": self.metrics["total_requests"],
            "requests_by_method": dict(self.metrics["requests_by_method"]),
            "requests_by_status": dict(self.metrics["requests_by_status"]),
            "average_response_time": avg_response_time,
            "error_rate": error_rate,
            "uptime": uptime,
            "errors": self.metrics["errors"]
        }


# 全局指标实例
_metrics_middleware: MetricsMiddleware = None


def get_metrics() -> Dict[str, Any]:
    """获取全局指标
    
    Returns:
        Dict[str, Any]: 指标数据
    """
    global _metrics_middleware
    if _metrics_middleware:
        return _metrics_middleware.get_metrics()
    return {}


def setup_middleware(app: FastAPI):
    """设置中间件
    
    Args:
        app: FastAPI应用实例
    """
    global _metrics_middleware
    
    settings = get_settings()
    
    # CORS中间件
    cors_config = get_cors_config()
    app.add_middleware(
        CORSMiddleware,
        **cors_config
    )
    
    # Gzip压缩中间件
    app.add_middleware(GZipMiddleware, minimum_size=1000)
    
    # 安全中间件
    app.add_middleware(SecurityMiddleware)
    
    # 限流中间件
    if get_rate_limit_config()["enabled"]:
        app.add_middleware(RateLimitMiddleware)
    
    # 指标收集中间件
    if settings.metrics_enabled:
        _metrics_middleware = MetricsMiddleware(app)
        app.add_middleware(MetricsMiddleware)
    
    # 请求日志中间件（最后添加，确保记录所有请求）
    app.add_middleware(RequestLoggingMiddleware)


# 异常处理器
async def validation_exception_handler(request: Request, exc: Exception):
    """验证异常处理器
    
    Args:
        request: 请求对象
        exc: 异常对象
        
    Returns:
        JSONResponse: 错误响应
    """
    error_response = ErrorResponse(
        message="Validation error",
        error_code="VALIDATION_ERROR",
        request_id=getattr(request.state, 'request_id', None),
        error_details={"errors": exc.errors() if hasattr(exc, 'errors') else str(exc)}
    )
    
    return JSONResponse(
        status_code=422,
        content=error_response.dict()
    )


async def http_exception_handler(request: Request, exc: HTTPException):
    """HTTP异常处理器
    
    Args:
        request: 请求对象
        exc: HTTP异常对象
        
    Returns:
        JSONResponse: 错误响应
    """
    error_response = ErrorResponse(
        message=exc.detail,
        error_code=f"HTTP_{exc.status_code}",
        request_id=getattr(request.state, 'request_id', None)
    )
    
    return JSONResponse(
        status_code=exc.status_code,
        content=error_response.dict()
    )


async def general_exception_handler(request: Request, exc: Exception):
    """通用异常处理器
    
    Args:
        request: 请求对象
        exc: 异常对象
        
    Returns:
        JSONResponse: 错误响应
    """
    error_response = ErrorResponse(
        message="Internal server error",
        error_code="INTERNAL_ERROR",
        request_id=getattr(request.state, 'request_id', None),
        error_details={"error": str(exc)} if get_settings().debug else None
    )
    
    return JSONResponse(
        status_code=500,
        content=error_response.dict()
    )