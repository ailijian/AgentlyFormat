"""AgentlyFormat异常类模块

提供完整的错误处理和异常管理机制，支持生产环境的错误分类、
错误恢复、错误上下文和详细的错误信息。
"""

import traceback
from typing import Any, Dict, List, Optional, Union
from datetime import datetime
from enum import Enum


class ErrorSeverity(Enum):
    """错误严重程度枚举"""
    LOW = "low"          # 轻微错误，不影响核心功能
    MEDIUM = "medium"    # 中等错误，影响部分功能
    HIGH = "high"        # 严重错误，影响核心功能
    CRITICAL = "critical" # 致命错误，系统无法继续运行


class ErrorCategory(Enum):
    """错误分类枚举"""
    PARSING = "parsing"              # JSON解析错误
    VALIDATION = "validation"        # 数据验证错误
    NETWORK = "network"              # 网络请求错误
    AUTHENTICATION = "authentication" # 认证错误
    CONFIGURATION = "configuration"   # 配置错误
    TIMEOUT = "timeout"              # 超时错误
    MEMORY = "memory"                # 内存错误
    FIELD_FILTERING = "field_filtering" # 字段过滤错误
    STREAMING = "streaming"          # 流式处理错误
    ADAPTER = "adapter"              # 适配器错误
    SCHEMA = "schema"                # Schema相关错误
    SYSTEM = "system"                # 系统级错误


class ErrorContext:
    """错误上下文信息"""
    
    def __init__(
        self,
        session_id: Optional[str] = None,
        operation: Optional[str] = None,
        component: Optional[str] = None,
        data: Optional[Dict[str, Any]] = None,
        timestamp: Optional[datetime] = None
    ):
        self.session_id = session_id
        self.operation = operation
        self.component = component
        self.data = data or {}
        self.timestamp = timestamp or datetime.now()
        self.stack_trace = traceback.format_stack()
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "session_id": self.session_id,
            "operation": self.operation,
            "component": self.component,
            "data": self.data,
            "timestamp": self.timestamp.isoformat(),
            "stack_trace": self.stack_trace
        }


class AgentlyFormatError(Exception):
    """AgentlyFormat基础异常类
    
    所有AgentlyFormat相关异常的基类，提供统一的错误处理接口。
    """
    
    def __init__(
        self,
        message: str,
        category: ErrorCategory = ErrorCategory.SYSTEM,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        context: Optional[ErrorContext] = None,
        cause: Optional[Exception] = None,
        recoverable: bool = True,
        error_code: Optional[str] = None
    ):
        super().__init__(message)
        self.message = message
        self.category = category
        self.severity = severity
        self.context = context or ErrorContext()
        self.cause = cause
        self.recoverable = recoverable
        self.timestamp = datetime.now()
        self.error_code = error_code or self._generate_error_code()
    
    def _generate_error_code(self) -> str:
        """生成错误代码"""
        return f"{self.category.value.upper()}_{self.severity.value.upper()}_{int(self.timestamp.timestamp())}"
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式，便于日志记录和API响应"""
        return {
            "error_code": self.error_code,
            "message": self.message,
            "category": self.category.value,
            "severity": self.severity.value,
            "recoverable": self.recoverable,
            "timestamp": self.timestamp.isoformat(),
            "context": self.context.to_dict() if self.context else None,
            "cause": str(self.cause) if self.cause else None
        }
    
    def __str__(self) -> str:
        return f"[{self.error_code}] {self.category.value.title()}: {self.message}"


class ParsingError(AgentlyFormatError):
    """JSON解析相关错误"""
    
    def __init__(
        self,
        message: str,
        json_content: Optional[str] = None,
        position: Optional[int] = None,
        **kwargs
    ):
        super().__init__(
            message,
            category=ErrorCategory.PARSING,
            **kwargs
        )
        self.json_content = json_content
        self.position = position


class ValidationError(AgentlyFormatError):
    """数据验证错误"""
    
    def __init__(
        self,
        message: str,
        field_path: Optional[str] = None,
        expected_type: Optional[str] = None,
        actual_value: Optional[Any] = None,
        **kwargs
    ):
        super().__init__(
            message,
            category=ErrorCategory.VALIDATION,
            **kwargs
        )
        self.field_path = field_path
        self.expected_type = expected_type
        self.actual_value = actual_value


class NetworkError(AgentlyFormatError):
    """网络请求错误"""
    
    def __init__(
        self,
        message: str,
        status_code: Optional[int] = None,
        response_body: Optional[str] = None,
        url: Optional[str] = None,
        **kwargs
    ):
        super().__init__(
            message,
            category=ErrorCategory.NETWORK,
            **kwargs
        )
        self.status_code = status_code
        self.response_body = response_body
        self.url = url


class AuthenticationError(AgentlyFormatError):
    """认证错误"""
    
    def __init__(self, message: str, **kwargs):
        super().__init__(
            message,
            category=ErrorCategory.AUTHENTICATION,
            severity=ErrorSeverity.HIGH,
            recoverable=False,
            **kwargs
        )


class ConfigurationError(AgentlyFormatError):
    """配置错误"""
    
    def __init__(
        self,
        message: str,
        config_key: Optional[str] = None,
        config_value: Optional[Any] = None,
        **kwargs
    ):
        super().__init__(
            message,
            category=ErrorCategory.CONFIGURATION,
            severity=ErrorSeverity.HIGH,
            **kwargs
        )
        self.config_key = config_key
        self.config_value = config_value


class TimeoutError(AgentlyFormatError):
    """超时错误"""
    
    def __init__(
        self,
        message: str,
        timeout_duration: Optional[float] = None,
        operation: Optional[str] = None,
        **kwargs
    ):
        super().__init__(
            message,
            category=ErrorCategory.TIMEOUT,
            **kwargs
        )
        self.timeout_duration = timeout_duration
        self.operation = operation


class MemoryError(AgentlyFormatError):
    """内存相关错误"""
    
    def __init__(
        self,
        message: str,
        memory_usage: Optional[int] = None,
        memory_limit: Optional[int] = None,
        **kwargs
    ):
        super().__init__(
            message,
            category=ErrorCategory.MEMORY,
            severity=ErrorSeverity.HIGH,
            **kwargs
        )
        self.memory_usage = memory_usage
        self.memory_limit = memory_limit


class FieldFilteringError(AgentlyFormatError):
    """字段过滤错误"""
    
    def __init__(
        self,
        message: str,
        field_path: Optional[str] = None,
        filter_config: Optional[Dict[str, Any]] = None,
        **kwargs
    ):
        super().__init__(
            message,
            category=ErrorCategory.FIELD_FILTERING,
            **kwargs
        )
        self.field_path = field_path
        self.filter_config = filter_config


class StreamingError(AgentlyFormatError):
    """流式处理错误"""
    
    def __init__(
        self,
        message: str,
        chunk_index: Optional[int] = None,
        buffer_size: Optional[int] = None,
        **kwargs
    ):
        super().__init__(
            message,
            category=ErrorCategory.STREAMING,
            **kwargs
        )
        self.chunk_index = chunk_index
        self.buffer_size = buffer_size


class BufferOverflowError(AgentlyFormatError):
    """缓冲区溢出错误"""
    
    def __init__(
        self,
        message: str,
        buffer_size: Optional[int] = None,
        max_buffer_size: Optional[int] = None,
        **kwargs
    ):
        super().__init__(
            message,
            category=ErrorCategory.STREAMING,
            severity=ErrorSeverity.HIGH,
            **kwargs
        )
        self.buffer_size = buffer_size
        self.max_buffer_size = max_buffer_size


class AdapterError(AgentlyFormatError):
    """适配器错误"""
    
    def __init__(
        self,
        message: str,
        adapter_name: Optional[str] = None,
        model_name: Optional[str] = None,
        **kwargs
    ):
        super().__init__(
            message,
            category=ErrorCategory.ADAPTER,
            **kwargs
        )
        self.adapter_name = adapter_name
        self.model_name = model_name


class SchemaError(AgentlyFormatError):
    """Schema相关错误"""
    
    def __init__(
        self,
        message: str,
        schema_path: Optional[str] = None,
        validation_errors: Optional[List[str]] = None,
        **kwargs
    ):
        super().__init__(
            message,
            category=ErrorCategory.SCHEMA,
            **kwargs
        )
        self.schema_path = schema_path
        self.validation_errors = validation_errors or []


class ErrorHandler:
    """错误处理器
    
    提供统一的错误处理、恢复和报告机制。
    """
    
    def __init__(self, enable_recovery: bool = True, max_retry_attempts: int = 3):
        self.enable_recovery = enable_recovery
        self.max_retry_attempts = max_retry_attempts
        self.error_history: List[AgentlyFormatError] = []
        self.recovery_strategies: Dict[ErrorCategory, callable] = {}
    
    def register_recovery_strategy(self, category: ErrorCategory, strategy: callable):
        """注册错误恢复策略
        
        Args:
            category: 错误分类
            strategy: 恢复策略函数
        """
        self.recovery_strategies[category] = strategy
    
    def handle_error(
        self,
        error: Union[Exception, AgentlyFormatError],
        context: Optional[ErrorContext] = None
    ) -> Optional[Any]:
        """处理错误
        
        Args:
            error: 错误对象
            context: 错误上下文
            
        Returns:
            Optional[Any]: 恢复结果（如果成功恢复）
        """
        # 转换为AgentlyFormatError
        if not isinstance(error, AgentlyFormatError):
            error = AgentlyFormatError(
                message=str(error),
                context=context,
                cause=error
            )
        
        # 记录错误
        self.error_history.append(error)
        
        # 尝试恢复
        if self.enable_recovery and error.recoverable:
            return self.attempt_recovery(error)
        
        # 无法恢复，重新抛出
        raise error
    
    def attempt_recovery(self, error: AgentlyFormatError) -> Optional[Any]:
        """尝试错误恢复
        
        Args:
            error: 错误对象
            
        Returns:
            Optional[Any]: 恢复结果
        """
        strategy = self.recovery_strategies.get(error.category)
        if strategy:
            try:
                return strategy(error)
            except Exception as recovery_error:
                # 恢复失败，记录并重新抛出原错误
                error.context.data["recovery_error"] = str(recovery_error)
                raise error
        
        return None
    
    def get_error_summary(self) -> Dict[str, Any]:
        """获取错误摘要
        
        Returns:
            Dict[str, Any]: 错误统计信息
        """
        if not self.error_history:
            return {"total_errors": 0}
        
        summary = {
            "total_errors": len(self.error_history),
            "by_category": {},
            "by_severity": {},
            "recoverable_count": 0,
            "critical_count": 0,
            "recent_errors": []
        }
        
        for error in self.error_history:
            # 按分类统计
            category = error.category.value
            summary["by_category"][category] = summary["by_category"].get(category, 0) + 1
            
            # 按严重程度统计
            severity = error.severity.value
            summary["by_severity"][severity] = summary["by_severity"].get(severity, 0) + 1
            
            # 可恢复错误计数
            if error.recoverable:
                summary["recoverable_count"] += 1
            
            # 致命错误计数
            if error.severity == ErrorSeverity.CRITICAL:
                summary["critical_count"] += 1
        
        # 最近的错误（最多10个）
        summary["recent_errors"] = [
            error.to_dict() for error in self.error_history[-10:]
        ]
        
        return summary
    
    def clear_history(self):
        """清空错误历史"""
        self.error_history.clear()


# 全局错误处理器实例
default_error_handler = ErrorHandler()


def handle_error(
    error: Union[Exception, AgentlyFormatError],
    context: Optional[ErrorContext] = None
) -> Optional[Any]:
    """全局错误处理函数
    
    Args:
        error: 错误对象
        context: 错误上下文
        
    Returns:
        Optional[Any]: 恢复结果（如果成功恢复）
    """
    return default_error_handler.handle_error(error, context)


def create_error_context(
    session_id: Optional[str] = None,
    operation: Optional[str] = None,
    component: Optional[str] = None,
    **data
) -> ErrorContext:
    """创建错误上下文的便捷函数
    
    Args:
        session_id: 会话ID
        operation: 操作名称
        component: 组件名称
        **data: 额外的上下文数据
        
    Returns:
        ErrorContext: 错误上下文对象
    """
    return ErrorContext(
        session_id=session_id,
        operation=operation,
        component=component,
        data=data
    )