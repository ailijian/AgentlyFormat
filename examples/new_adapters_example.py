#!/usr/bin/env python3
"""新适配器使用示例

演示如何使用文心、千问、DeepSeek和Kimi适配器。
"""

import asyncio
import os
from agently_format.adapters import ModelAdapter
from agently_format.types.models import ModelConfig, ModelType


async def test_wenxin_adapter():
    """测试文心大模型适配器"""
    print("\n=== 测试文心大模型适配器 ===")
    
    config = ModelConfig(
        model_type=ModelType.BAIDU,
        model_name="ernie-3.5-8k",
        api_key=os.getenv("WENXIN_API_KEY", "your-api-key"),
        api_secret=os.getenv("WENXIN_SECRET_KEY", "your-secret-key")
    )
    
    adapter = ModelAdapter.create_adapter(config)
    print(f"适配器创建成功: {adapter.__class__.__name__}")
    
    # 获取模型信息
    model_info = adapter.get_model_info()
    print(f"模型信息: {model_info}")
    
    # 注意：实际API调用需要有效的API密钥
    print("提示：需要设置有效的WENXIN_API_KEY和WENXIN_SECRET_KEY环境变量才能进行实际API调用")


async def test_qianwen_adapter():
    """测试千问适配器"""
    print("\n=== 测试千问适配器 ===")
    
    config = ModelConfig(
        model_type=ModelType.QWEN,
        model_name="qwen-max",
        api_key=os.getenv("QIANWEN_API_KEY", "your-api-key")
    )
    
    adapter = ModelAdapter.create_adapter(config)
    print(f"适配器创建成功: {adapter.__class__.__name__}")
    
    # 获取模型信息
    model_info = adapter.get_model_info()
    print(f"模型信息: {model_info}")
    
    print("提示：需要设置有效的QIANWEN_API_KEY环境变量才能进行实际API调用")


async def test_deepseek_adapter():
    """测试DeepSeek适配器"""
    print("\n=== 测试DeepSeek适配器 ===")
    
    config = ModelConfig(
        model_type=ModelType.DEEPSEEK,
        model_name="deepseek-chat",
        api_key=os.getenv("DEEPSEEK_API_KEY", "your-api-key")
    )
    
    adapter = ModelAdapter.create_adapter(config)
    print(f"适配器创建成功: {adapter.__class__.__name__}")
    
    # 获取模型信息
    model_info = adapter.get_model_info()
    print(f"模型信息: {model_info}")
    
    print("提示：需要设置有效的DEEPSEEK_API_KEY环境变量才能进行实际API调用")


async def test_kimi_adapter():
    """测试Kimi适配器"""
    print("\n=== 测试Kimi适配器 ===")
    
    config = ModelConfig(
        model_type=ModelType.KIMI,
        model_name="moonshot-v1-8k",
        api_key=os.getenv("KIMI_API_KEY", "your-api-key")
    )
    
    adapter = ModelAdapter.create_adapter(config)
    print(f"适配器创建成功: {adapter.__class__.__name__}")
    
    # 获取模型信息
    model_info = adapter.get_model_info()
    print(f"模型信息: {model_info}")
    
    print("提示：需要设置有效的KIMI_API_KEY环境变量才能进行实际API调用")


async def test_chat_completion_example():
    """聊天补全示例（需要有效API密钥）"""
    print("\n=== 聊天补全示例 ===")
    
    # 这里以千问为例，其他适配器使用方式类似
    if os.getenv("QIANWEN_API_KEY"):
        config = ModelConfig(
            model_type=ModelType.QWEN,
            model_name="qwen-max",
            api_key=os.getenv("QIANWEN_API_KEY")
        )
        
        adapter = ModelAdapter.create_adapter(config)
        
        messages = [
            {"role": "user", "content": "你好，请简单介绍一下你自己。"}
        ]
        
        try:
            response = await adapter.chat_completion(messages)
            print(f"响应: {response.content}")
        except Exception as e:
            print(f"API调用失败: {e}")
    else:
        print("跳过聊天补全示例，需要设置QIANWEN_API_KEY环境变量")


async def main():
    """主函数"""
    print("AgentlyFormat 新适配器使用示例")
    print("=" * 50)
    
    # 测试所有新适配器
    await test_wenxin_adapter()
    await test_qianwen_adapter()
    await test_deepseek_adapter()
    await test_kimi_adapter()
    
    # 聊天补全示例
    await test_chat_completion_example()
    
    print("\n=== 支持的模型类型 ===")
    supported_models = ModelAdapter.get_supported_models()
    print(f"支持的模型类型: {[model.value for model in supported_models]}")
    
    print("\n示例运行完成！")


if __name__ == "__main__":
    asyncio.run(main())