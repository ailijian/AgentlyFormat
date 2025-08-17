#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简单的字段过滤测试
用于验证字段过滤功能是否能输出纯净的字段内容
"""

import asyncio
import json
import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from agently_format.types.models import ModelConfig, ModelType
from agently_format.adapters.doubao_adapter import DoubaoAdapter

async def simple_field_filtering_test():
    """
    简单的字段过滤测试
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
            "content": "请以JSON格式输出一个编程语言的信息，包含name和description字段。确保输出是有效的JSON格式。"
        }
    ]
    
    print("=== 简单字段过滤测试 ===\n")
    
    # 测试1：只输出description字段
    print("测试1：只输出description字段")
    print("期望输出：纯净的description内容，无任何前缀或格式化")
    print("实际输出：")
    
    try:
        output_content = ""
        async for chunk in adapter.chat_completion(
            messages, 
            stream=True, 
            include_fields=["description"]
        ):
            if chunk:
                print(chunk, end='', flush=True)
                output_content += chunk
        
        print("\n\n--- 输出分析 ---")
        print(f"输出长度: {len(output_content)}")
        json_chars = '{}[]",:'
        has_json_chars = any(c in output_content for c in json_chars)
        print(f"是否包含JSON格式字符: {'是' if has_json_chars else '否'}")
        print(f"是否包含字段名: {'是' if 'description' in output_content else '否'}")
        
    except Exception as e:
        print(f"\n测试失败: {e}")

if __name__ == "__main__":
    asyncio.run(simple_field_filtering_test())