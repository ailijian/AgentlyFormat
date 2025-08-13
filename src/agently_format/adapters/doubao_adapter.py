"""豆包模型适配器

实现字节跳动豆包API的适配器。
"""

import json
from typing import Any, Dict, List, Optional, AsyncGenerator, Union

from .model_adapter import BaseModelAdapter, ModelResponse
from ..types.models import ModelType


class DoubaoAdapter(BaseModelAdapter):
    """豆包适配器"""
    
    def __init__(self, config):
        """初始化豆包适配器
        
        Args:
            config: 模型配置
        """
        # 设置默认base_url
        if not config.base_url:
            config.base_url = "https://ark.cn-beijing.volces.com/api/v3"
        
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
        """豆包聊天补全
        
        Args:
            messages: 消息列表
            stream: 是否流式返回
            **kwargs: 其他参数
            
        Returns:
            Union[ModelResponse, AsyncGenerator[str, None]]: 响应或流式生成器
        """
        if stream:
            return self._stream_chat_completion(messages, **kwargs)
        else:
            return self._non_stream_chat_completion(messages, **kwargs)
    
    async def _non_stream_chat_completion(
        self,
        messages: List[Dict[str, str]],
        **kwargs
    ) -> ModelResponse:
        """非流式聊天补全
        
        Args:
            messages: 消息列表
            **kwargs: 其他参数
            
        Returns:
            ModelResponse: 响应
        """
        payload = self._build_request_payload(messages, stream=False, **kwargs)
        response_data = await self._make_request("/chat/completions", payload, stream=False)
        return self._parse_response(response_data)
    
    async def _stream_chat_completion(
        self,
        messages: List[Dict[str, str]],
        **kwargs
    ) -> AsyncGenerator[str, None]:
        """流式聊天补全
        
        Args:
            messages: 消息列表
            **kwargs: 其他参数
            
        Yields:
            str: 流式响应内容
        """
        payload = self._build_request_payload(messages, stream=True, **kwargs)
        headers = self._get_auth_headers()
        
        async for content in self._stream_request("/chat/completions", payload, headers):
            yield content
    
    def _build_request_payload(self, messages: List[Dict[str, str]], **kwargs) -> Dict[str, Any]:
        """构建豆包请求载荷
        
        Args:
            messages: 消息列表
            **kwargs: 其他参数
            
        Returns:
            Dict[str, Any]: 请求载荷
        """
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
        
        return payload
    
    def _parse_response(self, response_data: Dict[str, Any]) -> ModelResponse:
        """解析豆包响应数据
        
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
                "req_id": response_data.get("req_id")
            }
        )
    
    async def _parse_stream_chunk(self, chunk: str) -> Optional[str]:
        """解析豆包流式响应块
        
        Args:
            chunk: 响应块
            
        Returns:
            Optional[str]: 解析出的内容
        """
        # 豆包流式响应格式类似OpenAI: "data: {json}\n\n"
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
        """获取豆包认证头
        
        Returns:
            Dict[str, str]: 认证头
        """
        return {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json"
        }
    
    def get_model_info(self) -> Dict[str, Any]:
        """获取模型信息
        
        Returns:
            Dict[str, Any]: 模型信息
        """
        model_info = {
            "provider": "Doubao",
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
        # 豆包模型的默认限制
        model_limits = {
            "doubao-lite-4k": 4096,
            "doubao-lite-32k": 32768,
            "doubao-lite-128k": 128000,
            "doubao-pro-4k": 4096,
            "doubao-pro-32k": 32768,
            "doubao-pro-128k": 128000
        }
        
        return model_limits.get(self.config.model_name, 4096)
    
    def _get_context_window(self) -> int:
        """获取上下文窗口大小
        
        Returns:
            int: 上下文窗口大小
        """
        context_windows = {
            "doubao-lite-4k": 4096,
            "doubao-lite-32k": 32768,
            "doubao-lite-128k": 128000,
            "doubao-pro-4k": 4096,
            "doubao-pro-32k": 32768,
            "doubao-pro-128k": 128000
        }
        
        return context_windows.get(self.config.model_name, 4096)
    
    async def validate_api_key(self) -> bool:
        """验证API密钥
        
        Returns:
            bool: 是否有效
        """
        try:
            # 发送简单的测试请求
            test_messages = [
                {"role": "user", "content": "你好"}
            ]
            
            payload = self._build_request_payload(
                test_messages,
                max_tokens=1
            )
            
            await self._make_request("/chat/completions", payload)
            return True
            
        except Exception:
            return False
    
    def _format_messages_for_doubao(self, messages: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """格式化消息以适配豆包API
        
        Args:
            messages: 原始消息列表
            
        Returns:
            List[Dict[str, str]]: 格式化后的消息列表
        """
        formatted_messages = []
        
        for message in messages:
            # 确保消息格式正确
            formatted_message = {
                "role": message.get("role", "user"),
                "content": message.get("content", "")
            }
            
            # 豆包可能需要特殊处理某些角色
            if formatted_message["role"] not in ["system", "user", "assistant"]:
                formatted_message["role"] = "user"
            
            formatted_messages.append(formatted_message)
        
        return formatted_messages


# 注册适配器
from .model_adapter import ModelAdapter
ModelAdapter.register_adapter(ModelType.DOUBAO, DoubaoAdapter)