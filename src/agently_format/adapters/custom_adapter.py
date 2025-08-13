"""自定义模型适配器

实现自定义API的适配器，支持用户自定义的模型接口。
"""

import json
from typing import Any, Dict, List, Optional, AsyncGenerator, Union, Callable

from .model_adapter import BaseModelAdapter, ModelResponse
from ..types.models import ModelType


class CustomAdapter(BaseModelAdapter):
    """自定义适配器"""
    
    def __init__(
        self, 
        config,
        request_transformer: Optional[Callable] = None,
        response_parser: Optional[Callable] = None,
        stream_parser: Optional[Callable] = None,
        auth_handler: Optional[Callable] = None
    ):
        """初始化自定义适配器
        
        Args:
            config: 模型配置
            request_transformer: 请求转换函数
            response_parser: 响应解析函数
            stream_parser: 流解析函数
            auth_handler: 认证处理函数
        """
        super().__init__(config)
        
        # 设置基本属性
        self.model_name = config.model_name
        self.api_key = config.api_key
        self.base_url = config.base_url or "https://api.openai.com/v1"  # 提供默认值
        
        # 确保config也有正确的base_url
        if not config.base_url:
            config.base_url = self.base_url
        
        # 设置自定义处理函数（优先使用参数传入的）
        custom_handlers = getattr(config, 'custom_handlers', {})
        self.request_transformer = request_transformer or custom_handlers.get('request_transformer')
        self.response_parser = response_parser or custom_handlers.get('response_parser')
        self.stream_parser = stream_parser or custom_handlers.get('stream_parser')
        self.auth_handler = auth_handler or custom_handlers.get('auth_handler')
    
    def chat_completion(
        self,
        messages: List[Dict[str, str]],
        stream: bool = False,
        **kwargs
    ) -> Union[ModelResponse, AsyncGenerator[str, None]]:
        """自定义聊天补全
        
        Args:
            messages: 消息列表
            stream: 是否流式返回
            **kwargs: 其他参数
            
        Returns:
            Union[ModelResponse, AsyncGenerator[str, None]]: 响应或流式生成器
        """
        payload = self._build_request_payload(messages, stream=stream, **kwargs)
        
        # 获取自定义端点
        endpoint = getattr(self.config, 'custom_endpoint', '/chat/completions')
        
        if stream:
            return self._stream_chat_completion(endpoint, payload)
        else:
            return self._non_stream_chat_completion(endpoint, payload)
    
    async def _non_stream_chat_completion(self, endpoint: str, payload: Dict[str, Any]) -> ModelResponse:
        """非流式聊天补全
        
        Args:
            endpoint: API端点
            payload: 请求载荷
            
        Returns:
            ModelResponse: 响应结果
        """
        response_data = await self._make_request(endpoint, payload, stream=False)
        return self._parse_response(response_data)
    
    async def _stream_chat_completion(self, endpoint: str, payload: Dict[str, Any]) -> AsyncGenerator[str, None]:
        """流式聊天补全
        
        Args:
            endpoint: API端点
            payload: 请求载荷
            
        Yields:
            str: 流式响应内容
        """
        headers = self._get_auth_headers()
        async for chunk in self._stream_request(endpoint, payload, headers):
            parsed_chunk = await self._parse_stream_chunk(chunk)
            if parsed_chunk:
                yield parsed_chunk
    
    def _build_request_payload(self, messages: List[Dict[str, str]], **kwargs) -> Dict[str, Any]:
        """构建自定义请求载荷
        
        Args:
            messages: 消息列表
            **kwargs: 其他参数
            
        Returns:
            Dict[str, Any]: 请求载荷
        """
        # 默认载荷格式
        payload = {
            "model": self.config.model_name,
            "messages": messages,
            **self.config.request_params
        }
        
        # 添加额外参数
        for key, value in kwargs.items():
            if key not in ["stream"]:
                payload[key] = value
        
        # 处理流式参数
        if kwargs.get("stream", False):
            payload["stream"] = True
        
        # 使用自定义请求转换器
        if self.request_transformer:
            try:
                payload = self.request_transformer(messages, **kwargs)
            except Exception as e:
                print(f"Warning: Custom request transformer failed: {e}")
        
        return payload
    
    def _parse_response(self, response_data: Dict[str, Any]) -> ModelResponse:
        """解析自定义响应数据
        
        Args:
            response_data: 响应数据
            
        Returns:
            ModelResponse: 解析后的响应
        """
        # 使用自定义响应解析器
        if self.response_parser:
            try:
                return self.response_parser(response_data)
            except Exception as e:
                print(f"Warning: Custom response parser failed: {e}")
                # 继续使用默认解析
        
        # 默认解析逻辑（兼容OpenAI格式）
        try:
            if "choices" in response_data and len(response_data["choices"]) > 0:
                choice = response_data["choices"][0]
                message = choice.get("message", {})
                
                return ModelResponse(
                    content=message.get("content", ""),
                    usage=response_data.get("usage"),
                    model=response_data.get("model"),
                    finish_reason=choice.get("finish_reason"),
                    metadata={
                        "id": response_data.get("id"),
                        "created": response_data.get("created"),
                        "custom_fields": {k: v for k, v in response_data.items() 
                                        if k not in ["choices", "usage", "model", "id", "created"]}
                    }
                )
            else:
                # 尝试直接从响应中提取内容
                content = response_data.get("content") or response_data.get("text") or str(response_data)
                
                return ModelResponse(
                    content=content,
                    usage=response_data.get("usage"),
                    model=response_data.get("model"),
                    finish_reason="stop",
                    metadata={"raw_response": response_data}
                )
                
        except Exception as e:
            # 最后的兜底处理
            return ModelResponse(
                content=str(response_data),
                usage=None,
                model=self.config.model_name,
                finish_reason="error",
                metadata={"parse_error": str(e), "raw_response": response_data}
            )
    
    async def _parse_stream_chunk(self, chunk: str) -> Optional[str]:
        """解析自定义流式响应块
        
        Args:
            chunk: 响应块
            
        Returns:
            Optional[str]: 解析出的内容
        """
        # 使用自定义流解析器
        if self.stream_parser:
            try:
                return await self.stream_parser(chunk)
            except Exception as e:
                print(f"Warning: Custom stream parser failed: {e}")
                # 继续使用默认解析
        
        # 默认解析逻辑（兼容OpenAI格式）
        lines = chunk.strip().split('\n')
        
        for line in lines:
            if line.startswith('data: '):
                data_str = line[6:]  # 移除"data: "前缀
                
                if data_str == '[DONE]':
                    return None
                
                try:
                    data = json.loads(data_str)
                    
                    if "choices" in data and len(data["choices"]) > 0:
                        delta = data["choices"][0].get("delta", {})
                        content = delta.get("content")
                        
                        if content:
                            return content
                    
                    # 尝试其他可能的字段
                    elif "content" in data:
                        return data["content"]
                    elif "text" in data:
                        return data["text"]
                            
                except json.JSONDecodeError:
                    # 如果不是JSON格式，尝试直接返回内容
                    if data_str and data_str != '[DONE]':
                        return data_str
        
        return None
    
    def _get_auth_headers(self) -> Dict[str, str]:
        """获取自定义认证头
        
        Returns:
            Dict[str, str]: 认证头
        """
        # 使用自定义认证处理器
        if self.auth_handler:
            try:
                # 优先尝试传递api_key参数（测试期望的行为）
                try:
                    return self.auth_handler(self.config.api_key)
                except TypeError:
                    # 兼容接受config对象的处理器
                    return self.auth_handler(self.config)
            except Exception as e:
                print(f"Warning: Custom auth handler failed: {e}")
                # 继续使用默认认证
        
        # 默认认证逻辑
        headers = {}
        
        if self.config.api_key:
            # 检查是否有自定义认证格式
            auth_format = getattr(self.config, 'auth_format', 'Bearer')
            
            if auth_format.lower() == 'bearer':
                headers["Authorization"] = f"Bearer {self.config.api_key}"
            elif auth_format.lower() == 'api-key':
                headers["API-Key"] = self.config.api_key
            elif auth_format.lower() == 'x-api-key':
                headers["X-API-Key"] = self.config.api_key
            else:
                # 自定义格式
                headers["Authorization"] = f"{auth_format} {self.config.api_key}"
        
        return headers
    
    def get_model_info(self) -> Dict[str, Any]:
        """获取模型信息
        
        Returns:
            Dict[str, Any]: 模型信息
        """
        model_info = {
            "provider": "Custom",
            "model_name": self.config.model_name,
            "model_type": self.config.model_type.value,
            "supports_streaming": True,
            "supports_function_calling": False,  # 默认不支持，可通过配置覆盖
            "max_tokens": getattr(self.config, 'max_tokens', 4096),
            "context_window": getattr(self.config, 'context_window', 4096),
            "custom_config": {
                "base_url": self.config.base_url,
                "endpoint": getattr(self.config, 'custom_endpoint', '/chat/completions'),
                "auth_format": getattr(self.config, 'auth_format', 'Bearer')
            }
        }
        
        return model_info
    
    async def validate_api_key(self) -> bool:
        """验证API密钥
        
        Returns:
            bool: 是否有效
        """
        try:
            # 发送简单的测试请求
            test_messages = [
                {"role": "user", "content": "Hello"}
            ]
            
            payload = self._build_request_payload(
                test_messages,
                max_tokens=1
            )
            
            endpoint = getattr(self.config, 'custom_endpoint', '/chat/completions')
            await self._make_request(endpoint, payload)
            return True
            
        except Exception:
            return False
    
    def set_custom_handlers(
        self,
        request_transformer: Optional[Callable] = None,
        response_parser: Optional[Callable] = None,
        stream_parser: Optional[Callable] = None,
        auth_handler: Optional[Callable] = None
    ):
        """设置自定义处理函数
        
        Args:
            request_transformer: 请求转换函数
            response_parser: 响应解析函数
            stream_parser: 流解析函数
            auth_handler: 认证处理函数
        """
        if request_transformer:
            self.request_transformer = request_transformer
        if response_parser:
            self.response_parser = response_parser
        if stream_parser:
            self.stream_parser = stream_parser
        if auth_handler:
            self.auth_handler = auth_handler


# 注册适配器
from .model_adapter import ModelAdapter
ModelAdapter.register_adapter(ModelType.CUSTOM, CustomAdapter)


# 便捷函数
def create_custom_adapter(
    model_name: str,
    base_url: str,
    api_key: str,
    endpoint: str = "/chat/completions",
    auth_format: str = "Bearer",
    request_transformer: Optional[Callable] = None,
    response_parser: Optional[Callable] = None,
    stream_parser: Optional[Callable] = None,
    auth_handler: Optional[Callable] = None,
    **kwargs
) -> CustomAdapter:
    """创建自定义适配器的便捷函数
    
    Args:
        model_name: 模型名称
        base_url: 基础URL
        api_key: API密钥
        endpoint: 自定义端点
        auth_format: 认证格式
        request_transformer: 请求转换函数
        response_parser: 响应解析函数
        stream_parser: 流解析函数
        auth_handler: 认证处理函数
        **kwargs: 其他配置参数
        
    Returns:
        CustomAdapter: 自定义适配器实例
    """
    from ..types.models import ModelConfig
    
    # 准备自定义处理函数
    custom_handlers = {}
    if request_transformer:
        custom_handlers['request_transformer'] = request_transformer
    if response_parser:
        custom_handlers['response_parser'] = response_parser
    if stream_parser:
        custom_handlers['stream_parser'] = stream_parser
    if auth_handler:
        custom_handlers['auth_handler'] = auth_handler
    
    config = ModelConfig(
        model_type=ModelType.CUSTOM,
        model_name=model_name,
        api_key=api_key,
        base_url=base_url,
        **kwargs
    )
    
    # 添加自定义属性
    config.custom_endpoint = endpoint
    config.auth_format = auth_format
    config.custom_handlers = custom_handlers
    
    return CustomAdapter(config)