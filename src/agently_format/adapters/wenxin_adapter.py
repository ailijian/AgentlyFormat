"""文心大模型适配器

实现百度文心一言API的适配器，支持ERNIE系列模型。
"""

import json
import hashlib
import hmac
import time
from typing import Any, Dict, List, Optional, AsyncGenerator, Union
from urllib.parse import quote

from .model_adapter import BaseModelAdapter, ModelResponse
from ..types.models import ModelType


class WenxinAdapter(BaseModelAdapter):
    """文心大模型适配器"""
    
    def __init__(self, config):
        """初始化文心适配器
        
        Args:
            config: 模型配置
        """
        # 设置默认base_url
        if not config.base_url:
            config.base_url = "https://aip.baidubce.com"
        
        super().__init__(config)
        
        # 添加必要属性以保持向后兼容
        self.model_name = config.model_name
        self.api_key = config.api_key
        self.base_url = config.base_url
        # 文心API需要access_token
        self.access_token = None
        self.token_expires_at = 0
        
        # 模型映射
        self.model_endpoints = {
            "ernie-4.0-8k": "/rpc/2.0/ai_custom/v1/wenxinworkshop/chat/completions_pro",
            "ernie-4.0-8k-preview": "/rpc/2.0/ai_custom/v1/wenxinworkshop/chat/ernie-4.0-8k-preview",
            "ernie-3.5-8k": "/rpc/2.0/ai_custom/v1/wenxinworkshop/chat/completions",
            "ernie-3.5-8k-0205": "/rpc/2.0/ai_custom/v1/wenxinworkshop/chat/ernie-3.5-8k-0205",
            "ernie-turbo-8k": "/rpc/2.0/ai_custom/v1/wenxinworkshop/chat/eb-instant",
            "ernie-speed-8k": "/rpc/2.0/ai_custom/v1/wenxinworkshop/chat/ernie_speed",
            "ernie-lite-8k": "/rpc/2.0/ai_custom/v1/wenxinworkshop/chat/ernie-lite-8k",
            "ernie-tiny-8k": "/rpc/2.0/ai_custom/v1/wenxinworkshop/chat/ernie-tiny-8k"
        }
    
    async def _get_access_token(self) -> str:
        """获取访问令牌
        
        Returns:
            str: 访问令牌
        """
        current_time = time.time()
        
        # 如果token还有效，直接返回
        if self.access_token and current_time < self.token_expires_at:
            return self.access_token
        
        # 获取新的access_token
        token_url = "/oauth/2.0/token"
        params = {
            "grant_type": "client_credentials",
            "client_id": self.config.api_key,
            "client_secret": getattr(self.config, 'api_secret', '')
        }
        
        response = await self.client.post(token_url, params=params)
        response.raise_for_status()
        
        token_data = response.json()
        
        if "error" in token_data:
            raise Exception(f"获取access_token失败: {token_data['error_description']}")
        
        self.access_token = token_data["access_token"]
        # 提前5分钟过期
        self.token_expires_at = current_time + token_data["expires_in"] - 300
        
        return self.access_token
    
    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        stream: bool = False,
        **kwargs
    ) -> Union[ModelResponse, AsyncGenerator[str, None]]:
        """文心聊天补全
        
        Args:
            messages: 消息列表
            stream: 是否流式返回
            **kwargs: 其他参数
            
        Returns:
            Union[ModelResponse, AsyncGenerator[str, None]]: 响应或流式生成器
        """
        # 获取模型对应的端点
        endpoint = self.model_endpoints.get(self.config.model_name)
        if not endpoint:
            raise ValueError(f"不支持的文心模型: {self.config.model_name}")
        
        # 获取access_token
        access_token = await self._get_access_token()
        endpoint_with_token = f"{endpoint}?access_token={access_token}"
        
        payload = self._build_request_payload(messages, stream=stream, **kwargs)
        
        if stream:
            return self._make_request(endpoint_with_token, payload, stream=True)
        else:
            response_data = await self._make_request(endpoint_with_token, payload, stream=False)
            return self._parse_response(response_data)
    
    def _build_request_payload(self, messages: List[Dict[str, str]], **kwargs) -> Dict[str, Any]:
        """构建文心请求载荷
        
        Args:
            messages: 消息列表
            **kwargs: 其他参数
            
        Returns:
            Dict[str, Any]: 请求载荷
        """
        # 文心API的消息格式转换
        wenxin_messages = []
        for msg in messages:
            role = msg["role"]
            content = msg["content"]
            
            # 文心API支持的角色: user, assistant
            if role == "system":
                # 将system消息合并到第一个user消息中
                if wenxin_messages and wenxin_messages[0]["role"] == "user":
                    wenxin_messages[0]["content"] = f"{content}\n\n{wenxin_messages[0]['content']}"
                else:
                    wenxin_messages.insert(0, {"role": "user", "content": content})
            else:
                wenxin_messages.append({"role": role, "content": content})
        
        payload = {
            "messages": wenxin_messages,
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
        
        # 处理max_tokens
        if self.config.max_tokens:
            payload["max_output_tokens"] = self.config.max_tokens
        
        return payload
    
    def _parse_response(self, response_data: Dict[str, Any]) -> ModelResponse:
        """解析文心响应数据
        
        Args:
            response_data: 响应数据
            
        Returns:
            ModelResponse: 解析后的响应
        """
        if "error_code" in response_data:
            raise Exception(f"文心API错误: {response_data['error_msg']}")
        
        result = response_data.get("result", "")
        
        return ModelResponse(
            content=result,
            usage=response_data.get("usage"),
            model=self.config.model_name,
            finish_reason=response_data.get("finish_reason"),
            metadata={
                "id": response_data.get("id"),
                "created": response_data.get("created"),
                "sentence_id": response_data.get("sentence_id"),
                "is_truncated": response_data.get("is_truncated")
            }
        )
    
    async def _parse_stream_chunk(self, chunk: str) -> Optional[str]:
        """解析文心流式响应块
        
        Args:
            chunk: 响应块
            
        Returns:
            Optional[str]: 解析出的内容
        """
        # 文心流式响应格式: "data: {json}\n\n"
        lines = chunk.strip().split('\n')
        
        for line in lines:
            if line.startswith('data: '):
                data_str = line[6:]  # 移除"data: "前缀
                
                if data_str == '[DONE]':
                    return None
                
                try:
                    data = json.loads(data_str)
                    
                    if "error_code" in data:
                        raise Exception(f"文心流式API错误: {data['error_msg']}")
                    
                    result = data.get("result")
                    if result:
                        return result
                        
                except json.JSONDecodeError:
                    continue
        
        return None
    
    def _get_auth_headers(self) -> Dict[str, str]:
        """获取文心认证头
        
        Returns:
            Dict[str, str]: 认证头
        """
        return {
            "Content-Type": "application/json"
        }
    
    def get_model_info(self) -> Dict[str, Any]:
        """获取模型信息
        
        Returns:
            Dict[str, Any]: 模型信息
        """
        model_info = {
            "provider": "Baidu Wenxin",
            "model_name": self.config.model_name,
            "model_type": self.config.model_type.value,
            "supports_streaming": True,
            "supports_function_calling": False,
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
            "ernie-4.0-8k": 4096,
            "ernie-4.0-8k-preview": 4096,
            "ernie-3.5-8k": 4096,
            "ernie-3.5-8k-0205": 4096,
            "ernie-turbo-8k": 4096,
            "ernie-speed-8k": 4096,
            "ernie-lite-8k": 4096,
            "ernie-tiny-8k": 4096
        }
        
        return model_limits.get(self.config.model_name, 4096)
    
    def _get_context_window(self) -> int:
        """获取上下文窗口大小
        
        Returns:
            int: 上下文窗口大小
        """
        context_windows = {
            "ernie-4.0-8k": 8192,
            "ernie-4.0-8k-preview": 8192,
            "ernie-3.5-8k": 8192,
            "ernie-3.5-8k-0205": 8192,
            "ernie-turbo-8k": 8192,
            "ernie-speed-8k": 8192,
            "ernie-lite-8k": 8192,
            "ernie-tiny-8k": 8192
        }
        
        return context_windows.get(self.config.model_name, 8192)
    
    def _get_mapped_model_name(self, model_name: str) -> str:
        """获取映射的模型名称
        
        Args:
            model_name: 原始模型名称
            
        Returns:
            str: 映射后的模型名称
        """
        model_mapping = {
            "ernie-4.0-8k": "ERNIE-4.0-8K",
            "ernie-3.5-8k": "ERNIE-3.5-8K",
            "ernie-turbo-8k": "ERNIE-Turbo-8K",
            "ernie-speed-8k": "ERNIE-Speed-8K",
            "ernie-lite-8k": "ERNIE-Lite-8K",
            "ernie-tiny-8k": "ERNIE-Tiny-8K"
        }
        return model_mapping.get(model_name, model_name.upper())
    
    async def validate_api_key(self) -> bool:
        """验证API密钥
        
        Returns:
            bool: 是否有效
        """
        try:
            # 尝试获取access_token
            await self._get_access_token()
            return True
            
        except Exception:
            return False


# 注册适配器
from .model_adapter import ModelAdapter
ModelAdapter.register_adapter(ModelType.BAIDU, WenxinAdapter)