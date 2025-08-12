"""千问模型适配器

实现阿里云通义千问API的适配器，支持Qwen系列模型。
"""

import json
from typing import Any, Dict, List, Optional, AsyncGenerator, Union

from .model_adapter import BaseModelAdapter, ModelResponse
from ..types.models import ModelType


class QianwenAdapter(BaseModelAdapter):
    """千问模型适配器"""
    
    def __init__(self, config):
        """初始化千问适配器
        
        Args:
            config: 模型配置
        """
        # 设置默认base_url
        if not config.base_url:
            config.base_url = "https://dashscope.aliyuncs.com/api/v1"
        
        super().__init__(config)
        
        # 添加必要属性以保持向后兼容
        self.model_name = config.model_name
        self.api_key = config.api_key
        self.base_url = config.base_url
        
        # 模型映射
        self.model_mapping = {
            "qwen-turbo": "qwen-turbo",
            "qwen-plus": "qwen-plus",
            "qwen-max": "qwen-max",
            "qwen-max-1201": "qwen-max-1201",
            "qwen-max-longcontext": "qwen-max-longcontext",
            "qwen1.5-72b-chat": "qwen1.5-72b-chat",
            "qwen1.5-14b-chat": "qwen1.5-14b-chat",
            "qwen1.5-7b-chat": "qwen1.5-7b-chat",
            "qwen1.5-1.8b-chat": "qwen1.5-1.8b-chat",
            "qwen1.5-0.5b-chat": "qwen1.5-0.5b-chat",
            "qwen2-72b-instruct": "qwen2-72b-instruct",
            "qwen2-7b-instruct": "qwen2-7b-instruct",
            "qwen2-1.5b-instruct": "qwen2-1.5b-instruct",
            "qwen2-0.5b-instruct": "qwen2-0.5b-instruct"
        }
    
    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        stream: bool = False,
        **kwargs
    ) -> Union[ModelResponse, AsyncGenerator[str, None]]:
        """千问聊天补全
        
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
        """构建千问请求载荷
        
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
            **self.config.request_params
        }
        
        # 添加额外参数
        for key, value in kwargs.items():
            if key not in ["stream"]:
                payload[key] = value
        
        # 处理流式参数
        if kwargs.get("stream", False):
            payload["stream"] = True
            payload["incremental_output"] = True
        
        # 处理max_tokens
        if self.config.max_tokens:
            payload["max_tokens"] = self.config.max_tokens
        
        # 处理repetition_penalty
        if self.config.frequency_penalty != 0.0:
            payload["repetition_penalty"] = 1.0 + self.config.frequency_penalty
        
        return payload
    
    def _parse_response(self, response_data: Dict[str, Any]) -> ModelResponse:
        """解析千问响应数据
        
        Args:
            response_data: 响应数据
            
        Returns:
            ModelResponse: 解析后的响应
        """
        # 检查错误
        if "error" in response_data:
            error = response_data["error"]
            raise Exception(f"千问API错误: {error.get('message', '未知错误')}")
        
        output = response_data.get("output", {})
        choices = output.get("choices", [])
        
        if not choices:
            raise Exception("千问API返回空响应")
        
        choice = choices[0]
        message = choice.get("message", {})
        
        return ModelResponse(
            content=message.get("content", ""),
            usage=response_data.get("usage"),
            model=self.config.model_name,
            finish_reason=choice.get("finish_reason"),
            metadata={
                "request_id": response_data.get("request_id"),
                "created": response_data.get("created"),
                "model": output.get("model")
            }
        )
    
    async def _parse_stream_chunk(self, chunk: str) -> Optional[str]:
        """解析千问流式响应块
        
        Args:
            chunk: 响应块
            
        Returns:
            Optional[str]: 解析出的内容
        """
        # 千问流式响应格式: "data: {json}\n\n"
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
                        raise Exception(f"千问流式API错误: {error.get('message', '未知错误')}")
                    
                    output = data.get("output", {})
                    choices = output.get("choices", [])
                    
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
        """获取千问认证头
        
        Returns:
            Dict[str, str]: 认证头
        """
        return {
            "Authorization": f"Bearer {self.config.api_key}",
            "X-DashScope-SSE": "enable",  # 启用SSE流式传输
            "Content-Type": "application/json"
        }
    
    def get_model_info(self) -> Dict[str, Any]:
        """获取模型信息
        
        Returns:
            Dict[str, Any]: 模型信息
        """
        model_info = {
            "provider": "Alibaba Qianwen",
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
            "qwen-turbo": 8192,
            "qwen-plus": 8192,
            "qwen-max": 8192,
            "qwen-max-1201": 8192,
            "qwen-max-longcontext": 8192,
            "qwen1.5-72b-chat": 8192,
            "qwen1.5-14b-chat": 8192,
            "qwen1.5-7b-chat": 8192,
            "qwen1.5-1.8b-chat": 8192,
            "qwen1.5-0.5b-chat": 8192,
            "qwen2-72b-instruct": 8192,
            "qwen2-7b-instruct": 8192,
            "qwen2-1.5b-instruct": 8192,
            "qwen2-0.5b-instruct": 8192
        }
        
        return model_limits.get(self.config.model_name, 8192)
    
    def _get_context_window(self) -> int:
        """获取上下文窗口大小
        
        Returns:
            int: 上下文窗口大小
        """
        context_windows = {
            "qwen-turbo": 8192,
            "qwen-plus": 32768,
            "qwen-max": 8192,
            "qwen-max-1201": 8192,
            "qwen-max-longcontext": 1000000,  # 1M tokens
            "qwen1.5-72b-chat": 32768,
            "qwen1.5-14b-chat": 8192,
            "qwen1.5-7b-chat": 8192,
            "qwen1.5-1.8b-chat": 8192,
            "qwen1.5-0.5b-chat": 8192,
            "qwen2-72b-instruct": 131072,
            "qwen2-7b-instruct": 131072,
            "qwen2-1.5b-instruct": 32768,
            "qwen2-0.5b-instruct": 32768
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
        return self.model_mapping.get(model_name, model_name)


# 注册适配器
from .model_adapter import ModelAdapter
ModelAdapter.register_adapter(ModelType.QWEN, QianwenAdapter)