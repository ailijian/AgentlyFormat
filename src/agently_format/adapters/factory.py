"""模型适配器工厂

提供统一的模型适配器创建接口。
"""

from typing import Dict, Type
from ..types.models import ModelConfig, ModelType
from .model_adapter import BaseModelAdapter
from .openai_adapter import OpenAIAdapter
from .doubao_adapter import DoubaoAdapter
from .wenxin_adapter import WenxinAdapter
from .qianwen_adapter import QianwenAdapter
from .deepseek_adapter import DeepSeekAdapter
from .kimi_adapter import KimiAdapter
from .custom_adapter import CustomAdapter


class ModelAdapterFactory:
    """模型适配器工厂类"""
    
    # 模型类型到适配器类的映射
    _adapter_registry: Dict[ModelType, Type[BaseModelAdapter]] = {
        ModelType.OPENAI: OpenAIAdapter,
        ModelType.DOUBAO: DoubaoAdapter,
        ModelType.BAIDU: WenxinAdapter,
        ModelType.QWEN: QianwenAdapter,
        ModelType.DEEPSEEK: DeepSeekAdapter,
        ModelType.KIMI: KimiAdapter,
        ModelType.CUSTOM: CustomAdapter,
    }
    
    @classmethod
    def create_adapter(cls, config: ModelConfig) -> BaseModelAdapter:
        """创建模型适配器
        
        Args:
            config: 模型配置
            
        Returns:
            BaseModelAdapter: 模型适配器实例
            
        Raises:
            ValueError: 不支持的模型类型
        """
        adapter_class = cls._adapter_registry.get(config.model_type)
        if adapter_class is None:
            raise ValueError(f"Unsupported model type: {config.model_type}")
        
        return adapter_class(config)
    
    @classmethod
    def register_adapter(cls, model_type: ModelType, adapter_class: Type[BaseModelAdapter]):
        """注册新的适配器类
        
        Args:
            model_type: 模型类型
            adapter_class: 适配器类
        """
        cls._adapter_registry[model_type] = adapter_class
    
    @classmethod
    def get_supported_models(cls) -> list[ModelType]:
        """获取支持的模型类型列表
        
        Returns:
            list[ModelType]: 支持的模型类型列表
        """
        return list(cls._adapter_registry.keys())
    
    @classmethod
    def is_supported(cls, model_type: ModelType) -> bool:
        """检查是否支持指定的模型类型
        
        Args:
            model_type: 模型类型
            
        Returns:
            bool: 是否支持
        """
        return model_type in cls._adapter_registry