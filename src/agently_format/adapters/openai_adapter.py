"""OpenAI模型适配器

实现OpenAI API的适配器，支持GPT系列模型。
"""

import json
import re
from typing import Any, Dict, List, Optional, AsyncGenerator, Union

from .model_adapter import BaseModelAdapter, ModelResponse
from ..types.models import ModelType


class OpenAIAdapter(BaseModelAdapter):
    """OpenAI适配器"""
    
    def __init__(self, config):
        """初始化OpenAI适配器
        
        Args:
            config: 模型配置
        """
        # 设置默认base_url
        if not config.base_url:
            config.base_url = "https://api.openai.com/v1"
        
        super().__init__(config)
        
        # 添加必要属性以保持向后兼容
        self.model_name = config.model_name
        self.api_key = config.api_key
        self.base_url = config.base_url
    
    def chat_completion(
        self, 
        messages: List[Dict[str, str]], 
        stream: bool = False, 
        **kwargs
    ) -> Union[ModelResponse, AsyncGenerator[str, None]]:
        """OpenAI聊天补全
        
        Args:
            messages: 消息列表
            stream: 是否流式返回
            **kwargs: 其他参数
            
        Returns:
            Union[ModelResponse, AsyncGenerator[str, None]]: 响应或流式生成器
        """
        payload = self._build_request_payload(messages, stream=stream, **kwargs)
        
        if stream:
            return self._stream_chat_completion(payload)
        else:
            return self._non_stream_chat_completion(payload)
    
    async def _non_stream_chat_completion(self, payload: Dict[str, Any]) -> ModelResponse:
        """非流式聊天补全
        
        Args:
            payload: 请求载荷
            
        Returns:
            ModelResponse: 响应结果
        """
        response_data = await self._make_request("/chat/completions", payload, stream=False)
        return self._parse_response(response_data)
    
    async def _stream_chat_completion(self, payload: Dict[str, Any]) -> AsyncGenerator[str, None]:
        """流式聊天补全
        
        Args:
            payload: 请求载荷
            
        Yields:
            str: 流式响应内容
        """
        headers = self._get_auth_headers()
        async for chunk in self._stream_request("/chat/completions", payload, headers):
            parsed_chunk = await self._parse_stream_chunk(chunk)
            if parsed_chunk:
                yield parsed_chunk
    
    def _build_request_payload(self, messages: List[Dict[str, str]], **kwargs) -> Dict[str, Any]:
        """构建OpenAI请求载荷
        
        Args:
            messages: 消息列表
            **kwargs: 其他参数
            
        Returns:
            Dict[str, Any]: 请求载荷
        """
        payload = {
            "model": self.config.model_name,
            "messages": messages,
            "temperature": 0.7,
            "max_tokens": 1000,
            **self.config.request_params
        }
        
        # 添加额外参数
        for key, value in kwargs.items():
            if key not in ["stream"]:
                payload[key] = value
        
        # 处理流式参数
        if kwargs.get("stream", False):
            payload["stream"] = True
            payload["stream_options"] = {"include_usage": True}
        
        return payload
    
    def _parse_response(self, response_data: Dict[str, Any]) -> ModelResponse:
        """解析OpenAI响应数据
        
        Args:
            response_data: 响应数据
            
        Returns:
            ModelResponse: 解析后的响应
        """
        choice = response_data["choices"][0]
        message = choice["message"]
        
        return ModelResponse(
            content=message["content"],
            usage=response_data.get("usage"),
            model=response_data.get("model"),
            finish_reason=choice.get("finish_reason"),
            metadata={
                "id": response_data.get("id"),
                "created": response_data.get("created"),
                "system_fingerprint": response_data.get("system_fingerprint")
            }
        )
    
    async def _parse_stream_chunk(self, chunk: str) -> Optional[str]:
        """解析OpenAI流式响应块
        
        Args:
            chunk: 响应块
            
        Returns:
            Optional[str]: 解析出的内容
        """
        # OpenAI流式响应格式: "data: {json}\n\n"
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
                            
                except json.JSONDecodeError:
                    continue
        
        return None
    
    def _get_auth_headers(self) -> Dict[str, str]:
        """获取OpenAI认证头
        
        Returns:
            Dict[str, str]: 认证头
        """
        headers = {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json"
        }
        
        # 添加组织ID（如果有）
        if hasattr(self.config, 'organization_id') and self.config.organization_id:
            headers["OpenAI-Organization"] = self.config.organization_id
        
        return headers
    
    def get_model_info(self) -> Dict[str, Any]:
        """获取模型信息
        
        Returns:
            Dict[str, Any]: 模型信息
        """
        model_info = {
            "provider": "OpenAI",
            "model_name": self.config.model_name,
            "model_type": self.config.model_type.value,
            "supports_streaming": True,
            "supports_function_calling": True,
            "max_tokens": self._get_max_tokens(),
            "context_window": self._get_context_window()
        }
        
        return model_info
    
    def _get_max_tokens(self) -> int:
        """获取最大输出token数
        
        Returns:
            int: 最大token数
        """
        model_limits = {
            "gpt-4": 8192,
            "gpt-4-32k": 32768,
            "gpt-4-turbo": 4096,
            "gpt-4o": 4096,
            "gpt-4o-mini": 16384,
            "gpt-3.5-turbo": 4096,
            "gpt-3.5-turbo-16k": 16384
        }
        
        return model_limits.get(self.config.model_name, 4096)
    
    def _get_context_window(self) -> int:
        """获取上下文窗口大小
        
        Returns:
            int: 上下文窗口大小
        """
        context_windows = {
            "gpt-4": 8192,
            "gpt-4-32k": 32768,
            "gpt-4-turbo": 128000,
            "gpt-4o": 128000,
            "gpt-4o-mini": 128000,
            "gpt-3.5-turbo": 16385,
            "gpt-3.5-turbo-16k": 16385
        }
        
        return context_windows.get(self.config.model_name, 8192)
    
    async def validate_api_key(self) -> bool:
        """验证API密钥
        
        Returns:
            bool: 是否有效
        """
        try:
            # 发送简单的测试请求
            test_messages = [
                {"role": "user", "content": "Hi"}
            ]
            
            payload = self._build_request_payload(
                test_messages,
                max_tokens=1
            )
            
            await self._make_request("/chat/completions", payload)
            return True
            
        except Exception:
            return False


# 注册适配器
from .model_adapter import ModelAdapter
ModelAdapter.register_adapter(ModelType.OPENAI, OpenAIAdapter)