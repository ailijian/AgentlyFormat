#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
豆包大模型调用示例
演示如何使用豆包API进行文本生成和AgentlyFormat框架调用
"""

import requests
import json
import asyncio

# 导入AgentlyFormat相关模块
from agently_format.types.models import ModelConfig, ModelType
from agently_format.adapters.doubao_adapter import DoubaoAdapter

def call_doubao_model(prompt: str, model_name: str, api_key: str) -> str:
    """
    调用豆包大模型API
    
    Args:
        prompt: 输入提示文本
        model_name: 模型名称
        api_key: API密钥
        
    Returns:
        str: 模型生成的响应文本
    """
    # 豆包API端点（示例URL，实际使用时需要替换为正确的API地址）
    url = "https://ark.cn-beijing.volces.com/api/v3/chat/completions"
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    
    data = {
        "model": model_name,
        "messages": [
            {
                "role": "user",
                "content": prompt
            }
        ],
        "max_tokens": 1000,
        "temperature": 0.7
    }
    
    try:
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()
        
        result = response.json()
        return result["choices"][0]["message"]["content"]
        
    except requests.exceptions.RequestException as e:
        return f"API调用失败: {e}"
    except KeyError as e:
        return f"响应格式错误: {e}"

async def agently_format_doubao_example():
    """
    使用AgentlyFormat框架调用豆包模型的最简单实例
    """
    # 配置参数
    model_name = "doubao-1-5-pro-32k-character-250715"
    api_key = "4ed46be9-4eb4-45f1-8576-d2fc3d115026"
    
    # 创建模型配置
    config = ModelConfig(
        model_type=ModelType.DOUBAO,
        model_name=model_name,
        api_key=api_key
    )
    
    # 创建豆包适配器
    adapter = DoubaoAdapter(config)
    
    # 准备消息
    messages = [
        {
            "role": "user",
            "content": "请用一句话介绍什么是人工智能。"
        }
    ]
    
    print("\n=== AgentlyFormat豆包调用示例 ===")
    print(f"模型: {model_name}")
    print(f"提示: {messages[0]['content']}")
    print("\n正在使用AgentlyFormat调用...")
    
    try:
        # 调用模型
        response = await adapter.chat_completion(messages, stream=False)
        
        print("\n=== AgentlyFormat响应 ===")
        print(f"内容: {response.content}")
        print(f"模型: {response.model}")
        print(f"完成原因: {response.finish_reason}")
        if response.usage:
            print(f"Token使用: {response.usage}")
            
    except Exception as e:
        print(f"\nAgentlyFormat调用失败: {e}")


async def agently_format_doubao_stream_example():
    """
    使用AgentlyFormat框架调用豆包模型的流式输出示例
    """
    # 配置参数
    model_name = "doubao-1-5-pro-32k-character-250715"
    api_key = "4ed46be9-4eb4-45f1-8576-d2fc3d115026"
    
    # 创建模型配置
    config = ModelConfig(
        model_type=ModelType.DOUBAO,
        model_name=model_name,
        api_key=api_key
    )
    
    # 创建豆包适配器
    adapter = DoubaoAdapter(config)
    
    # 准备消息
    messages = [
        {
            "role": "user",
            "content": "请详细介绍人工智能的发展历程，包括主要里程碑和技术突破。"
        }
    ]
    
    print("\n=== AgentlyFormat豆包流式调用示例 ===")
    print(f"模型: {model_name}")
    print(f"提示: {messages[0]['content']}")
    print("\n正在使用AgentlyFormat流式调用...")
    print("\n=== 流式响应 ===")
    
    try:
        # 流式调用模型
        async for chunk in adapter.chat_completion(messages, stream=True):
            if chunk:
                # 实时输出每个响应块的内容
                print(chunk, end='', flush=True)
        
        print("\n\n=== 流式调用完成 ===")
        
    except Exception as e:
        print(f"\n\nAgentlyFormat流式调用失败: {e}")


async def agently_format_doubao_json_stream_example():
    """
    使用AgentlyFormat框架调用豆包模型的JSON格式流式输出示例
    测试结构化数据的流式解析能力
    """
    # 配置参数
    model_name = "doubao-1-5-pro-32k-character-250715"
    api_key = "4ed46be9-4eb4-45f1-8576-d2fc3d115026"
    
    # 创建模型配置
    config = ModelConfig(
        model_type=ModelType.DOUBAO,
        model_name=model_name,
        api_key=api_key
    )
    
    # 创建豆包适配器
    adapter = DoubaoAdapter(config)
    
    # 准备消息 - 要求模型输出JSON格式的结构化数据
    messages = [
        {
            "role": "user",
            "content": "请以JSON格式输出3个热门编程语言的信息，包含以下字段：name（语言名称）、year（发布年份）、creator（创建者）、description（简短描述）。请确保输出是有效的JSON格式。"
        }
    ]
    
    print("\n=== AgentlyFormat豆包JSON流式调用示例 ===")
    print(f"模型: {model_name}")
    print(f"提示: {messages[0]['content']}")
    print("\n正在使用AgentlyFormat JSON流式调用...")
    print("\n=== JSON流式响应 ===")
    
    try:
        # 流式调用模型
        full_response = ""
        async for chunk in adapter.chat_completion(messages, stream=True):
            if chunk:
                # 实时输出每个响应块的内容
                print(chunk, end='', flush=True)
                full_response += chunk
        
        print("\n\n=== JSON流式调用完成 ===")
        
        # 尝试解析完整的JSON响应
        try:
            json_data = json.loads(full_response.strip())
            print("\n=== JSON解析成功 ===")
            print(f"解析后的数据: {json.dumps(json_data, ensure_ascii=False, indent=2)}")
        except json.JSONDecodeError as e:
            print(f"\n=== JSON解析失败 ===")
            print(f"错误: {e}")
            print(f"原始响应: {full_response}")
        
    except Exception as e:
        print(f"\n\nAgentlyFormat JSON流式调用失败: {e}")


async def main_async():
    """
    异步主函数：演示豆包大模型调用
    """
    # 调用AgentlyFormat非流式示例
    await agently_format_doubao_example()
    
    # 调用AgentlyFormat流式示例
    await agently_format_doubao_stream_example()
    
    # 调用AgentlyFormat JSON流式示例
    await agently_format_doubao_json_stream_example()


def main():
    """
    主函数：演示豆包大模型调用
    """
    # 配置参数
    # model_name = "doubao-1-5-pro-32k-character-250715"
    # api_key = "4ed46be9-4eb4-45f1-8576-d2fc3d115026"
    
    # # 测试提示
    # prompt = "请介绍一下人工智能的发展历程，用简洁的语言概括主要里程碑。"
    
    # print("=== 豆包大模型调用示例 ===")
    # print(f"模型: {model_name}")
    # print(f"提示: {prompt}")
    # print("\n正在调用API...")
    
    # # 调用模型
    # response = call_doubao_model(prompt, model_name, api_key)
    
    # print("\n=== 模型响应 ===")
    # print(response)
    
    # 调用AgentlyFormat示例
    asyncio.run(main_async())

if __name__ == "__main__":
    main()