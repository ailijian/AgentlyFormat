"""模型适配器使用示例

演示如何使用AgentlyFormat的模型适配器功能。
"""

import asyncio
import json
import os
from typing import Dict, Any, List, Optional

from agently_format.adapters.base import BaseModelAdapter
from agently_format.adapters.openai_adapter import OpenAIAdapter
from agently_format.adapters.doubao_adapter import DoubaoAdapter
from agently_format.adapters.custom_adapter import CustomAdapter
from agently_format.adapters.wenxin_adapter import WenxinAdapter
from agently_format.adapters.qianwen_adapter import QianwenAdapter
from agently_format.adapters.deepseek_adapter import DeepSeekAdapter
from agently_format.adapters.kimi_adapter import KimiAdapter
from agently_format.adapters.factory import ModelAdapterFactory
from agently_format.core.types import ModelConfig, ChatMessage


class ModelAdapterDemo:
    """模型适配器演示类"""
    
    def __init__(self):
        self.factory = ModelAdapterFactory()
        self.adapters: Dict[str, BaseModelAdapter] = {}
    
    async def cleanup(self):
        """清理资源"""
        for adapter in self.adapters.values():
            await adapter.close()
        self.adapters.clear()


async def openai_adapter_example():
    """OpenAI适配器示例"""
    print("=== OpenAI适配器示例 ===")
    
    # 注意: 这里使用环境变量或模拟密钥
    api_key = os.getenv('OPENAI_API_KEY', 'sk-mock-key-for-demo')
    
    config = ModelConfig(
        model_type="openai",
        model_name="gpt-3.5-turbo",
        api_key=api_key,
        base_url="https://api.openai.com/v1",
        timeout=30,
        max_retries=3
    )
    
    print(f"配置信息:")
    print(f"  模型类型: {config.model_type}")
    print(f"  模型名称: {config.model_name}")
    print(f"  API端点: {config.base_url}")
    print(f"  超时时间: {config.timeout}秒")
    
    try:
        # 创建适配器
        adapter = OpenAIAdapter(config)
        
        # 验证API密钥
        print(f"\n验证API密钥...")
        is_valid = await adapter.validate_api_key()
        print(f"API密钥有效性: {'✅ 有效' if is_valid else '❌ 无效'}")
        
        if not is_valid:
            print("提示: 请设置有效的OPENAI_API_KEY环境变量")
            return
        
        # 获取模型信息
        model_info = await adapter.get_model_info()
        print(f"\n模型信息:")
        print(f"  支持的功能: {model_info.get('capabilities', [])}")
        print(f"  上下文长度: {model_info.get('context_length', 'Unknown')}")
        print(f"  输入价格: ${model_info.get('input_price', 0)}/1K tokens")
        print(f"  输出价格: ${model_info.get('output_price', 0)}/1K tokens")
        
        # 准备聊天消息
        messages = [
            ChatMessage(
                role="system",
                content="你是一个专业的JSON数据格式化助手。请帮助用户生成和格式化JSON数据。"
            ),
            ChatMessage(
                role="user",
                content="请生成一个包含用户信息的JSON对象，包括姓名、年龄、邮箱和偏好设置。"
            )
        ]
        
        print(f"\n发送聊天请求...")
        
        # 非流式聊天
        response = await adapter.chat_completion(
            messages=messages,
            stream=False,
            temperature=0.7,
            max_tokens=500
        )
        
        print(f"\n聊天响应:")
        print(f"  内容: {response.content}")
        print(f"  模型: {response.model}")
        print(f"  使用量: {response.usage}")
        print(f"  完成原因: {response.finish_reason}")
        
        # 尝试解析响应中的JSON
        try:
            # 提取JSON部分
            content = response.content
            if '```json' in content:
                json_start = content.find('```json') + 7
                json_end = content.find('```', json_start)
                json_str = content[json_start:json_end].strip()
            elif '{' in content and '}' in content:
                json_start = content.find('{')
                json_end = content.rfind('}') + 1
                json_str = content[json_start:json_end]
            else:
                json_str = content
            
            parsed_json = json.loads(json_str)
            print(f"\n解析的JSON:")
            print(json.dumps(parsed_json, indent=2, ensure_ascii=False))
            
        except json.JSONDecodeError:
            print("\n响应内容不是有效的JSON格式")
        
        # 流式聊天示例
        print(f"\n流式聊天示例:")
        
        stream_messages = [
            ChatMessage(
                role="user",
                content="请逐步生成一个复杂的配置文件JSON，包含应用设置、用户偏好和系统配置。"
            )
        ]
        
        print("流式响应:")
        async for chunk in adapter.chat_completion_stream(
            messages=stream_messages,
            temperature=0.5,
            max_tokens=800
        ):
            if chunk.content:
                print(chunk.content, end='', flush=True)
        
        print("\n\n流式聊天完成")
        
        await adapter.close()
        
    except Exception as e:
        print(f"OpenAI适配器示例失败: {e}")
        if "API key" in str(e) or "authentication" in str(e).lower():
            print("提示: 请确保设置了有效的OPENAI_API_KEY环境变量")


async def doubao_adapter_example():
    """豆包适配器示例"""
    print("\n=== 豆包适配器示例 ===")
    
    # 豆包API配置
    api_key = os.getenv('DOUBAO_API_KEY', 'mock-doubao-key')
    
    config = ModelConfig(
        model_type="doubao",
        model_name="doubao-pro-4k",
        api_key=api_key,
        base_url="https://ark.cn-beijing.volces.com/api/v3",
        timeout=30
    )
    
    print(f"豆包配置:")
    print(f"  模型: {config.model_name}")
    print(f"  端点: {config.base_url}")
    
    try:
        adapter = DoubaoAdapter(config)
        
        # 获取模型信息
        model_info = await adapter.get_model_info()
        print(f"\n模型信息:")
        print(f"  提供商: {model_info.get('provider', 'Doubao')}")
        print(f"  支持中文: {model_info.get('supports_chinese', True)}")
        print(f"  上下文长度: {model_info.get('context_length', '4K')}")
        
        # 验证API密钥
        is_valid = await adapter.validate_api_key()
        print(f"\nAPI密钥验证: {'✅ 有效' if is_valid else '❌ 无效'}")
        
        if not is_valid:
            print("提示: 请设置有效的DOUBAO_API_KEY环境变量")
            await adapter.close()
            return
        
        # 中文聊天示例
        messages = [
            ChatMessage(
                role="system",
                content="你是一个专业的数据分析师，擅长处理和分析JSON格式的数据。"
            ),
            ChatMessage(
                role="user",
                content="请帮我生成一个电商网站的商品数据JSON结构，包含商品基本信息、价格、库存和评价数据。"
            )
        ]
        
        print(f"\n发送中文聊天请求...")
        
        response = await adapter.chat_completion(
            messages=messages,
            stream=False,
            temperature=0.8
        )
        
        print(f"\n豆包响应:")
        print(f"  内容长度: {len(response.content)} 字符")
        print(f"  模型: {response.model}")
        print(f"  内容预览: {response.content[:200]}...")
        
        await adapter.close()
        
    except Exception as e:
        print(f"豆包适配器示例失败: {e}")
        print("提示: 豆包API需要有效的API密钥和正确的配置")


async def custom_adapter_example():
    """自定义适配器示例"""
    print("\n=== 自定义适配器示例 ===")
    
    # 自定义响应转换器
    def custom_response_transformer(raw_response: Dict[str, Any]) -> Dict[str, Any]:
        """自定义响应转换器"""
        return {
            "content": raw_response.get("text", ""),
            "model": raw_response.get("model_id", "custom-model"),
            "usage": {
                "prompt_tokens": raw_response.get("input_tokens", 0),
                "completion_tokens": raw_response.get("output_tokens", 0),
                "total_tokens": raw_response.get("total_tokens", 0)
            },
            "finish_reason": raw_response.get("stop_reason", "stop")
        }
    
    config = ModelConfig(
        model_type="custom",
        model_name="my-custom-model",
        api_key="custom-api-key",
        base_url="https://api.example.com/v1",
        timeout=30
    )
    
    print(f"自定义适配器配置:")
    print(f"  模型类型: {config.model_type}")
    print(f"  模型名称: {config.model_name}")
    print(f"  API端点: {config.base_url}")
    
    try:
        # 创建自定义适配器
        adapter = CustomAdapter(
            config=config,
            response_transformer=custom_response_transformer
        )
        
        print(f"\n自定义适配器创建成功")
        
        # 获取认证头
        auth_headers = await adapter.get_auth_headers()
        print(f"认证头: {auth_headers}")
        
        # 获取模型信息
        model_info = await adapter.get_model_info()
        print(f"\n模型信息:")
        for key, value in model_info.items():
            print(f"  {key}: {value}")
        
        # 模拟聊天请求（由于是自定义适配器，这里只是演示结构）
        print(f"\n自定义适配器已准备就绪，可以根据具体API进行定制")
        
        await adapter.close()
        
    except Exception as e:
        print(f"自定义适配器示例失败: {e}")


async def adapter_factory_example():
    """适配器工厂示例"""
    print("\n=== 适配器工厂示例 ===")
    
    factory = ModelAdapterFactory()
    
    # 获取支持的模型类型
    supported_models = factory.get_supported_models()
    print(f"支持的模型类型: {supported_models}")
    
    # 注册自定义适配器
    def create_mock_adapter(config: ModelConfig) -> BaseModelAdapter:
        """创建模拟适配器"""
        return CustomAdapter(config)
    
    factory.register_adapter("mock", create_mock_adapter)
    print(f"\n注册自定义适配器后支持的模型: {factory.get_supported_models()}")
    
    # 创建不同类型的适配器
    configs = [
        ModelConfig(
            model_type="openai",
            model_name="gpt-3.5-turbo",
            api_key="mock-openai-key"
        ),
        ModelConfig(
            model_type="doubao",
            model_name="doubao-pro-4k",
            api_key="mock-doubao-key"
        ),
        ModelConfig(
            model_type="mock",
            model_name="mock-model",
            api_key="mock-key"
        )
    ]
    
    adapters = []
    
    print(f"\n创建适配器:")
    for config in configs:
        try:
            adapter = factory.create_adapter(config)
            adapters.append(adapter)
            print(f"  ✅ {config.model_type} 适配器创建成功")
        except Exception as e:
            print(f"  ❌ {config.model_type} 适配器创建失败: {e}")
    
    # 测试适配器
    print(f"\n测试适配器:")
    for adapter in adapters:
        try:
            # 测试适配器基本功能
            test_result = await factory.test_adapter(adapter)
            status = "✅ 通过" if test_result else "❌ 失败"
            print(f"  {adapter.config.model_type}: {status}")
        except Exception as e:
            print(f"  {adapter.config.model_type}: ❌ 测试异常 - {e}")
    
    # 清理资源
    for adapter in adapters:
        await adapter.close()


async def adapter_performance_example():
    """适配器性能示例"""
    print("\n=== 适配器性能示例 ===")
    
    import time
    
    factory = ModelAdapterFactory()
    
    # 性能测试配置
    config = ModelConfig(
        model_type="openai",
        model_name="gpt-3.5-turbo",
        api_key="mock-key-for-performance-test"
    )
    
    # 测试适配器创建性能
    print(f"测试适配器创建性能...")
    
    start_time = time.time()
    adapters = []
    
    for i in range(10):
        adapter = factory.create_adapter(config)
        adapters.append(adapter)
    
    creation_time = time.time() - start_time
    
    print(f"创建10个适配器耗时: {creation_time:.3f}秒")
    print(f"平均创建时间: {creation_time / 10:.3f}秒/个")
    
    # 测试并发请求性能（模拟）
    print(f"\n测试并发处理性能...")
    
    async def mock_request(adapter: BaseModelAdapter, request_id: int):
        """模拟请求"""
        await asyncio.sleep(0.1)  # 模拟网络延迟
        return f"Response {request_id}"
    
    start_time = time.time()
    
    # 并发执行多个模拟请求
    tasks = [
        mock_request(adapters[i % len(adapters)], i)
        for i in range(50)
    ]
    
    results = await asyncio.gather(*tasks)
    
    concurrent_time = time.time() - start_time
    
    print(f"50个并发请求耗时: {concurrent_time:.3f}秒")
    print(f"平均请求时间: {concurrent_time / 50:.3f}秒/个")
    print(f"请求吞吐量: {50 / concurrent_time:.1f} 请求/秒")
    
    # 清理资源
    for adapter in adapters:
        await adapter.close()


async def adapter_integration_example():
    """适配器集成示例"""
    print("\n=== 适配器集成示例 ===")
    
    demo = ModelAdapterDemo()
    
    try:
        # 创建多个适配器
        configs = {
            "openai": ModelConfig(
                model_type="openai",
                model_name="gpt-3.5-turbo",
                api_key=os.getenv('OPENAI_API_KEY', 'mock-openai-key')
            ),
            "doubao": ModelConfig(
                model_type="doubao",
                model_name="doubao-pro-4k",
                api_key=os.getenv('DOUBAO_API_KEY', 'mock-doubao-key')
            )
        }
        
        print(f"初始化适配器...")
        
        for name, config in configs.items():
            try:
                if config.model_type == "openai":
                    adapter = OpenAIAdapter(config)
                elif config.model_type == "doubao":
                    adapter = DoubaoAdapter(config)
                else:
                    continue
                
                demo.adapters[name] = adapter
                print(f"  ✅ {name} 适配器初始化成功")
                
            except Exception as e:
                print(f"  ❌ {name} 适配器初始化失败: {e}")
        
        # 测试适配器功能
        print(f"\n测试适配器功能:")
        
        test_message = ChatMessage(
            role="user",
            content="请生成一个简单的JSON示例"
        )
        
        for name, adapter in demo.adapters.items():
            try:
                print(f"\n测试 {name} 适配器:")
                
                # 验证API密钥
                is_valid = await adapter.validate_api_key()
                print(f"  API密钥: {'✅ 有效' if is_valid else '❌ 无效'}")
                
                if is_valid:
                    # 获取模型信息
                    model_info = await adapter.get_model_info()
                    print(f"  模型信息: {model_info.get('name', 'Unknown')}")
                    
                    # 发送测试请求
                    response = await adapter.chat_completion(
                        messages=[test_message],
                        stream=False,
                        max_tokens=100
                    )
                    
                    print(f"  响应长度: {len(response.content)} 字符")
                    print(f"  使用量: {response.usage}")
                
            except Exception as e:
                print(f"  ❌ 测试失败: {e}")
        
        print(f"\n集成测试完成")
        
    finally:
        await demo.cleanup()


async def wenxin_adapter_example():
    """文心大模型适配器示例"""
    print("\n=== 文心大模型适配器示例 ===")
    
    # 文心API配置
    api_key = os.getenv('WENXIN_API_KEY', 'mock-wenxin-key')
    api_secret = os.getenv('WENXIN_SECRET_KEY', 'mock-wenxin-secret')
    
    config = ModelConfig(
        model_type="baidu",
        model_name="ernie-4.0-8k",
        api_key=api_key,
        api_secret=api_secret,
        base_url="https://aip.baidubce.com",
        timeout=30
    )
    
    print(f"文心配置:")
    print(f"  模型: {config.model_name}")
    print(f"  端点: {config.base_url}")
    
    try:
        adapter = WenxinAdapter(config)
        
        # 获取模型信息
        model_info = adapter.get_model_info()
        print(f"\n模型信息:")
        print(f"  提供商: 百度")
        print(f"  支持中文: 是")
        print(f"  上下文长度: {model_info.get('context_window', '8K')}")
        
        # 验证API密钥
        is_valid = await adapter.validate_api_key()
        print(f"\nAPI密钥验证: {'✅ 有效' if is_valid else '❌ 无效'}")
        
        if not is_valid:
            print("提示: 请设置有效的WENXIN_API_KEY和WENXIN_SECRET_KEY环境变量")
            await adapter.close()
            return
        
        # 中文聊天示例
        messages = [
            ChatMessage(
                role="system",
                content="你是一个专业的JSON数据处理专家，擅长生成和格式化各种JSON数据结构。"
            ),
            ChatMessage(
                role="user",
                content="请生成一个电商产品信息的JSON数据，包含产品名称、价格、分类、库存等信息。"
            )
        ]
        
        print(f"\n发送聊天请求...")
        
        response = await adapter.chat_completion(
            messages=messages,
            stream=False,
            temperature=0.7,
            max_tokens=500
        )
        
        print(f"\n聊天响应:")
        print(f"  内容: {response.content[:200]}...")
        print(f"  模型: {response.model}")
        print(f"  使用量: {response.usage}")
        
        await adapter.close()
        
    except Exception as e:
        print(f"文心适配器示例失败: {e}")


async def qianwen_adapter_example():
    """千问适配器示例"""
    print("\n=== 千问适配器示例 ===")
    
    # 千问API配置
    api_key = os.getenv('QIANWEN_API_KEY', 'mock-qianwen-key')
    
    config = ModelConfig(
        model_type="qwen",
        model_name="qwen-turbo",
        api_key=api_key,
        base_url="https://dashscope.aliyuncs.com/api/v1",
        timeout=30
    )
    
    print(f"千问配置:")
    print(f"  模型: {config.model_name}")
    print(f"  端点: {config.base_url}")
    
    try:
        adapter = QianwenAdapter(config)
        
        # 获取模型信息
        model_info = adapter.get_model_info()
        print(f"\n模型信息:")
        print(f"  提供商: 阿里云")
        print(f"  支持中文: 是")
        print(f"  上下文长度: {model_info.get('context_window', '8K')}")
        
        # 验证API密钥
        is_valid = await adapter.validate_api_key()
        print(f"\nAPI密钥验证: {'✅ 有效' if is_valid else '❌ 无效'}")
        
        if not is_valid:
            print("提示: 请设置有效的QIANWEN_API_KEY环境变量")
            await adapter.close()
            return
        
        # 聊天示例
        messages = [
            ChatMessage(
                role="user",
                content="请生成一个用户配置文件的JSON结构，包含个人信息、偏好设置和权限配置。"
            )
        ]
        
        print(f"\n发送聊天请求...")
        
        response = await adapter.chat_completion(
            messages=messages,
            stream=False,
            temperature=0.5,
            max_tokens=600
        )
        
        print(f"\n聊天响应:")
        print(f"  内容: {response.content[:200]}...")
        print(f"  模型: {response.model}")
        print(f"  使用量: {response.usage}")
        
        await adapter.close()
        
    except Exception as e:
        print(f"千问适配器示例失败: {e}")


async def deepseek_adapter_example():
    """DeepSeek适配器示例"""
    print("\n=== DeepSeek适配器示例 ===")
    
    # DeepSeek API配置
    api_key = os.getenv('DEEPSEEK_API_KEY', 'mock-deepseek-key')
    
    config = ModelConfig(
        model_type="deepseek",
        model_name="deepseek-chat",
        api_key=api_key,
        base_url="https://api.deepseek.com/v1",
        timeout=30
    )
    
    print(f"DeepSeek配置:")
    print(f"  模型: {config.model_name}")
    print(f"  端点: {config.base_url}")
    
    try:
        adapter = DeepSeekAdapter(config)
        
        # 获取模型信息
        model_info = adapter.get_model_info()
        print(f"\n模型信息:")
        print(f"  提供商: DeepSeek")
        print(f"  擅长领域: 代码生成和推理")
        print(f"  上下文长度: {model_info.get('context_window', '4K')}")
        
        # 验证API密钥
        is_valid = await adapter.validate_api_key()
        print(f"\nAPI密钥验证: {'✅ 有效' if is_valid else '❌ 无效'}")
        
        if not is_valid:
            print("提示: 请设置有效的DEEPSEEK_API_KEY环境变量")
            await adapter.close()
            return
        
        # 代码生成示例
        messages = [
            ChatMessage(
                role="user",
                content="请生成一个Python函数，用于解析和验证JSON配置文件，包含错误处理和类型检查。"
            )
        ]
        
        print(f"\n发送聊天请求...")
        
        response = await adapter.chat_completion(
            messages=messages,
            stream=False,
            temperature=0.3,
            max_tokens=800
        )
        
        print(f"\n聊天响应:")
        print(f"  内容: {response.content[:200]}...")
        print(f"  模型: {response.model}")
        print(f"  使用量: {response.usage}")
        
        await adapter.close()
        
    except Exception as e:
        print(f"DeepSeek适配器示例失败: {e}")


async def kimi_adapter_example():
    """Kimi适配器示例"""
    print("\n=== Kimi适配器示例 ===")
    
    # Kimi API配置
    api_key = os.getenv('KIMI_API_KEY', 'mock-kimi-key')
    
    config = ModelConfig(
        model_type="kimi",
        model_name="moonshot-v1-8k",
        api_key=api_key,
        base_url="https://api.moonshot.cn/v1",
        timeout=30
    )
    
    print(f"Kimi配置:")
    print(f"  模型: {config.model_name}")
    print(f"  端点: {config.base_url}")
    
    try:
        adapter = KimiAdapter(config)
        
        # 获取模型信息
        model_info = adapter.get_model_info()
        print(f"\n模型信息:")
        print(f"  提供商: 月之暗面")
        print(f"  支持长文本: 是")
        print(f"  上下文长度: {model_info.get('context_window', '8K')}")
        
        # 验证API密钥
        is_valid = await adapter.validate_api_key()
        print(f"\nAPI密钥验证: {'✅ 有效' if is_valid else '❌ 无效'}")
        
        if not is_valid:
            print("提示: 请设置有效的KIMI_API_KEY环境变量")
            await adapter.close()
            return
        
        # 长文本处理示例
        messages = [
            ChatMessage(
                role="user",
                content="请生成一个完整的API文档JSON结构，包含端点定义、参数说明、响应格式和错误代码。"
            )
        ]
        
        print(f"\n发送聊天请求...")
        
        response = await adapter.chat_completion(
            messages=messages,
            stream=False,
            temperature=0.6,
            max_tokens=1000
        )
        
        print(f"\n聊天响应:")
        print(f"  内容: {response.content[:200]}...")
        print(f"  模型: {response.model}")
        print(f"  使用量: {response.usage}")
        
        await adapter.close()
        
    except Exception as e:
        print(f"Kimi适配器示例失败: {e}")


async def main():
    """主函数 - 运行所有模型适配器示例"""
    print("Agently Format - 模型适配器示例")
    print("=" * 50)
    
    try:
        await openai_adapter_example()
        await doubao_adapter_example()
        await wenxin_adapter_example()
        await qianwen_adapter_example()
        await deepseek_adapter_example()
        await kimi_adapter_example()
        await custom_adapter_example()
        await adapter_factory_example()
        await adapter_performance_example()
        await adapter_integration_example()
        
        print("\n=== 所有模型适配器示例运行完成 ===")
        print("\n支持的功能:")
        print("✅ OpenAI API集成")
        print("✅ 豆包API集成")
        print("✅ 自定义适配器")
        print("✅ 适配器工厂模式")
        print("✅ 并发处理")
        print("✅ 性能优化")
        
        print("\n注意事项:")
        print("1. 需要有效的API密钥才能测试真实的模型功能")
        print("2. 设置环境变量: OPENAI_API_KEY, DOUBAO_API_KEY")
        print("3. 某些示例使用模拟数据进行演示")
        
    except Exception as e:
        print(f"\n运行模型适配器示例时发生错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    # 运行示例
    asyncio.run(main())