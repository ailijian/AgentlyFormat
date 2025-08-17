#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
调试字段过滤重复输出问题
"""

import asyncio
import sys
sys.path.insert(0, 'E:/project/AgentlyFormat/src')

from agently_format.types.models import ModelConfig, ModelType
from agently_format.adapters.doubao_adapter import DoubaoAdapter

async def debug_field_filtering():
    """调试字段过滤功能"""
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
            "content": "请以JSON格式输出一个编程语言的信息，包含name和description字段。"
        }
    ]
    
    print("=== 调试字段过滤 ===")
    print("测试只输出description字段...")
    print("\n=== 输出开始 ===")
    
    try:
        chunk_count = 0
        total_content = ""
        async for chunk in adapter.chat_completion(
            messages, 
            stream=True, 
            include_fields=["description"]
        ):
            if chunk:
                chunk_count += 1
                total_content += chunk
                print(f"[{chunk_count}]", end='', flush=True)
                print(chunk, end='', flush=True)
        
        print("\n=== 输出结束 ===")
        print(f"总共收到 {chunk_count} 个chunk")
        print(f"总内容长度: {len(total_content)}")
        print(f"总内容: {repr(total_content)}")
        
    except Exception as e:
        print(f"\n调试失败: {e}")

if __name__ == "__main__":
    asyncio.run(debug_field_filtering())