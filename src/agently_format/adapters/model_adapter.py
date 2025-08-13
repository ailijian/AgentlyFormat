"""模型适配器基类和工厂

定义模型适配器的基础接口和工厂模式实现。
"""

import asyncio
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, AsyncGenerator, Union
from dataclasses import dataclass
import httpx
import json

from ..types.models import ModelConfig, ModelType, ParseRequest, ParseResponse
from ..types.events import StreamingEvent


@dataclass
class ModelResponse:
    """模型响应数据"""
    content: str
    usage: Optional[Dict[str, Any]] = None
    model: Optional[str] = None
    finish_reason: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class BaseModelAdapter(ABC):
    """模型适配器基类"""
    
    def __init__(self, config: ModelConfig):
        """初始化适配器
        
        Args:
            config: 模型配置
        """
        self.config = config
        self.model_name = config.model_name
        self.api_key = config.api_key
        self.base_url = config.base_url
        self.client = None  # 延迟初始化
    
    def _setup_client(self):
        """确保HTTP客户端已初始化"""
        if self.client is None:
            headers = {
                "Content-Type": "application/json",
                **self.config.headers
            }
            
            self.client = httpx.AsyncClient(
                base_url=self.config.base_url,
                headers=headers,
                timeout=self.config.timeout
            )
    
    @abstractmethod
    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        stream: bool = False,
        **kwargs
    ) -> Union[ModelResponse, AsyncGenerator[str, None]]:
        """聊天补全
        
        Args:
            messages: 消息列表
            stream: 是否流式返回
            **kwargs: 其他参数
            
        Returns:
            Union[ModelResponse, AsyncGenerator[str, None]]: 响应或流式生成器
        """
        pass
    
    @abstractmethod
    def _build_request_payload(self, messages: List[Dict[str, str]], **kwargs) -> Dict[str, Any]:
        """构建请求载荷
        
        Args:
            messages: 消息列表
            **kwargs: 其他参数
            
        Returns:
            Dict[str, Any]: 请求载荷
        """
        pass
    
    @abstractmethod
    def _parse_response(self, response_data: Dict[str, Any]) -> ModelResponse:
        """解析响应数据
        
        Args:
            response_data: 响应数据
            
        Returns:
            ModelResponse: 解析后的响应
        """
        pass
    
    @abstractmethod
    async def _parse_stream_chunk(self, chunk: str) -> Optional[str]:
        """解析流式响应块
        
        Args:
            chunk: 响应块
            
        Returns:
            Optional[str]: 解析出的内容
        """
        pass
    
    async def _make_request(
        self,
        endpoint: str,
        payload: Dict[str, Any],
        stream: bool = False
    ) -> Union[Dict[str, Any], AsyncGenerator[str, None]]:
        """发起HTTP请求
        
        Args:
            endpoint: 请求端点
            payload: 请求载荷
            stream: 是否流式请求
            
        Returns:
            Union[Dict[str, Any], AsyncGenerator[str, None]]: 响应数据或流式生成器
        """
        self._setup_client()  # 延迟初始化客户端
        headers = self._get_auth_headers()
        
        if stream:
            return self._stream_request(endpoint, payload, headers)
        else:
            response = await self.client.post(
                endpoint,
                json=payload,
                headers=headers
            )
            response.raise_for_status()
            return response.json()
    
    async def _stream_request(
        self,
        endpoint: str,
        payload: Dict[str, Any],
        headers: Dict[str, str]
    ) -> AsyncGenerator[str, None]:
        """流式请求
        
        Args:
            endpoint: 请求端点
            payload: 请求载荷
            headers: 请求头
            
        Yields:
            str: 响应块
        """
        self._setup_client()  # 确保客户端已初始化
        async with self.client.stream(
            "POST",
            endpoint,
            json=payload,
            headers=headers
        ) as response:
            response.raise_for_status()
            
            async for chunk in response.aiter_text():
                if chunk.strip():
                    content = await self._parse_stream_chunk(chunk)
                    if content:
                        yield content
    
    @abstractmethod
    def _get_auth_headers(self) -> Dict[str, str]:
        """获取认证头
        
        Returns:
            Dict[str, str]: 认证头
        """
        pass
    
    async def close(self):
        """关闭客户端"""
        if self.client and not self.client.is_closed:
            await self.client.aclose()
    
    def __del__(self):
        """析构函数"""
        if self.client and not self.client.is_closed:
            try:
                # 在事件循环中创建任务
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    loop.create_task(self.client.aclose())
                else:
                    loop.run_until_complete(self.client.aclose())
            except Exception:
                pass


class ModelAdapter:
    """模型适配器工厂"""
    
    _adapters = {}
    
    @classmethod
    def register_adapter(cls, model_type: ModelType, adapter_class: type):
        """注册适配器
        
        Args:
            model_type: 模型类型
            adapter_class: 适配器类
        """
        cls._adapters[model_type] = adapter_class
    
    @classmethod
    def create_adapter(cls, config: ModelConfig) -> BaseModelAdapter:
        """创建适配器
        
        Args:
            config: 模型配置
            
        Returns:
            BaseModelAdapter: 适配器实例
        """
        if config.model_type not in cls._adapters:
            raise ValueError(f"Unsupported model type: {config.model_type}")
        
        adapter_class = cls._adapters[config.model_type]
        return adapter_class(config)
    
    @classmethod
    def get_supported_models(cls) -> List[ModelType]:
        """获取支持的模型类型
        
        Returns:
            List[ModelType]: 支持的模型类型列表
        """
        return list(cls._adapters.keys())
    
    @classmethod
    async def test_adapter(cls, config: ModelConfig) -> Dict[str, Any]:
        """测试适配器
        
        Args:
            config: 模型配置
            
        Returns:
            Dict[str, Any]: 测试结果
        """
        try:
            adapter = cls.create_adapter(config)
            
            # 发送测试消息
            test_messages = [
                {"role": "user", "content": "Hello, this is a test message."}
            ]
            
            response = await adapter.chat_completion(test_messages)
            
            await adapter.close()
            
            return {
                "success": True,
                "model_type": config.model_type.value,
                "model_name": config.model_name,
                "response_length": len(response.content) if hasattr(response, 'content') else 0,
                "usage": response.usage if hasattr(response, 'usage') else None
            }
            
        except Exception as e:
            return {
                "success": False,
                "model_type": config.model_type.value,
                "model_name": config.model_name,
                "error": str(e)
            }


# 便捷函数
def create_adapter(model_type: ModelType, model_name: str, api_key: str, **kwargs) -> BaseModelAdapter:
    """创建适配器的便捷函数
    
    Args:
        model_type: 模型类型
        model_name: 模型名称
        api_key: API密钥
        **kwargs: 其他配置参数
        
    Returns:
        BaseModelAdapter: 适配器实例
    """
    from ..types.models import create_model_config
    
    config = create_model_config(
        model_type=model_type,
        model_name=model_name,
        api_key=api_key,
        **kwargs
    )
    
    return ModelAdapter.create_adapter(config)


async def test_model_connection(
    model_type: ModelType,
    model_name: str,
    api_key: str,
    **kwargs
) -> Dict[str, Any]:
    """测试模型连接的便捷函数
    
    Args:
        model_type: 模型类型
        model_name: 模型名称
        api_key: API密钥
        **kwargs: 其他配置参数
        
    Returns:
        Dict[str, Any]: 测试结果
    """
    from ..types.models import create_model_config
    
    config = create_model_config(
        model_type=model_type,
        model_name=model_name,
        api_key=api_key,
        **kwargs
    )
    
    return await ModelAdapter.test_adapter(config)