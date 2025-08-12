"""Kimi模型适配器

实现月之暗面Kimi API的适配器，支持Moonshot系列模型。
"""

import json
from typing import Any, Dict, List, Optional, AsyncGenerator, Union

from .model_adapter import BaseModelAdapter, ModelResponse
from ..types.models import ModelType


class KimiAdapter(BaseModelAdapter):
    """Kimi模型适配器"""
    
    def __init__(self, config):
        """初始化Kimi适配器
        
        Args:
            config: 模型配置
        """
        # 设置默认base_url
        if not config.base_url:
            config.base_url = "https://api.moonshot.cn/v1"
        
        super().__init__(config)
        
        # 添加必要属性以保持向后兼容
        self.model_name = config.model_name
        self.api_key = config.api_key
        self.base_url = config.base_url
        
        # 模型映射
        self.model_mapping = {
            "moonshot-v1-8k": "moonshot-v1-8k",
            "moonshot-v1-32k": "moonshot-v1-32k",
            "moonshot-v1-128k": "moonshot-v1-128k",
            "kimi-8k": "moonshot-v1-8k",
            "kimi-32k": "moonshot-v1-32k",
            "kimi-128k": "moonshot-v1-128k"
        }
    
    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        stream: bool = False,
        **kwargs
    ) -> Union[ModelResponse, AsyncGenerator[str, None]]:
        """Kimi聊天补全
        
        Args:
            messages: 消息列表
            stream: 是否流式返回
            **kwargs: 其他参数
            
        Returns:
            Union[ModelResponse, AsyncGenerator[str, None]]: 响应或流式生成器
        """
        payload = self._build_request_payload(messages, stream=stream, **kwargs)
        
        if stream:
            return self._make_request("/chat/completions", payload, stream=True)
        else:
            response_data = await self._make_request("/chat/completions", payload, stream=False)
            return self._parse_response(response_data)
    
    def _build_request_payload(self, messages: List[Dict[str, str]], **kwargs) -> Dict[str, Any]:
        """构建Kimi请求载荷
        
        Args:
            messages: 消息列表
            **kwargs: 其他参数
            
        Returns:
            Dict[str, Any]: 请求载荷
        """
        # 获取实际的模型名称
        model_name = self.model_mapping.get(self.config.model_name, self.config.model_name)
        
        payload = {
            "model": model_name,
            "messages": messages,
            "temperature": self.config.temperature,
            "top_p": self.config.top_p,
            "frequency_penalty": self.config.frequency_penalty,
            "presence_penalty": self.config.presence_penalty,
            **self.config.request_params
        }
        
        # 添加额外参数
        for key, value in kwargs.items():
            if key not in ["stream"]:
                payload[key] = value
        
        # 处理流式参数
        if kwargs.get("stream", False):
            payload["stream"] = True
        
        # 处理max_tokens
        if self.config.max_tokens:
            payload["max_tokens"] = self.config.max_tokens
        
        return payload
    
    def _parse_response(self, response_data: Dict[str, Any]) -> ModelResponse:
        """解析Kimi响应数据
        
        Args:
            response_data: 响应数据
            
        Returns:
            ModelResponse: 解析后的响应
        """
        # 检查错误
        if "error" in response_data:
            error = response_data["error"]
            raise Exception(f"Kimi API错误: {error.get('message', '未知错误')}")
        
        choices = response_data.get("choices", [])
        
        if not choices:
            raise Exception("Kimi API返回空响应")
        
        choice = choices[0]
        message = choice.get("message", {})
        
        return ModelResponse(
            content=message.get("content", ""),
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
        """解析Kimi流式响应块
        
        Args:
            chunk: 响应块
            
        Returns:
            Optional[str]: 解析出的内容
        """
        # Kimi流式响应格式: "data: {json}\n\n"
        lines = chunk.strip().split('\n')
        
        for line in lines:
            if line.startswith('data: '):
                data_str = line[6:]  # 移除"data: "前缀
                
                if data_str == '[DONE]':
                    return None
                
                try:
                    data = json.loads(data_str)
                    
                    # 检查错误
                    if "error" in data:
                        error = data["error"]
                        raise Exception(f"Kimi流式API错误: {error.get('message', '未知错误')}")
                    
                    choices = data.get("choices", [])
                    
                    if choices:
                        choice = choices[0]
                        delta = choice.get("delta", {})
                        content = delta.get("content")
                        
                        if content:
                            return content
                        
                except json.JSONDecodeError:
                    continue
        
        return None
    
    def _get_auth_headers(self) -> Dict[str, str]:
        """获取Kimi认证头
        
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
            "provider": "Moonshot Kimi",
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
            "moonshot-v1-8k": 4096,
            "moonshot-v1-32k": 4096,
            "moonshot-v1-128k": 4096,
            "kimi-8k": 4096,
            "kimi-32k": 4096,
            "kimi-128k": 4096
        }
        
        return model_limits.get(self.config.model_name, 4096)
    
    def _get_context_window(self) -> int:
        """获取上下文窗口大小
        
        Returns:
            int: 上下文窗口大小
        """
        context_windows = {
            "moonshot-v1-8k": 8192,
            "moonshot-v1-32k": 32768,
            "moonshot-v1-128k": 131072,
            "kimi-8k": 8192,
            "kimi-32k": 32768,
            "kimi-128k": 131072
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


    def _get_mapped_model_name(self, model_name: str) -> str:
        """获取映射的模型名称
        
        Args:
            model_name: 原始模型名称
            
        Returns:
            str: 映射后的模型名称
        """
        model_mapping = {
            "moonshot-v1-8k": "moonshot-v1-8k",
            "moonshot-v1-32k": "moonshot-v1-32k",
            "moonshot-v1-128k": "moonshot-v1-128k"
        }
        return model_mapping.get(model_name, model_name)


# 注册适配器
from .model_adapter import ModelAdapter
ModelAdapter.register_adapter(ModelType.KIMI, KimiAdapter)