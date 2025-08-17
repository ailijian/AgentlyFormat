#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
详细调试流式解析过程中多余数字的来源
"""

import sys
import os
import asyncio
import json
from typing import AsyncGenerator

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from agently_format.core.streaming_parser import parse_json_stream_with_fields, StreamingEvent, EventType

async def simulate_doubao_stream() -> AsyncGenerator[str, None]:
    """模拟豆包API的流式响应"""
    # 模拟的JSON响应数据
    json_data = {
        "languages": [
            {
                "name": "Python",
                "year": 1991,
                "creator": "Guido van Rossum",
                "description": "一种简单易学、功能强大的编程语言，具有丰富的库和框架，广泛应用于数据分析、人工智能、Web开发等领域。",
                "popularity": 9
            },
            {
                "name": "Java",
                "year": 1995,
                "creator": "James Gosling",
                "description": "一种面向对象的编程语言，具有良好的跨平台性和性能，广泛应用于企业级应用开发、安卓应用开发等领域。",
                "popularity": 8
            },
            {
                "name": "JavaScript",
                "year": 1995,
                "creator": "Brendan Eich",
                "description": "一种用于网页开发的脚本语言，可实现网页的交互效果和动态内容，也可用于后端开发和移动应用开发。",
                "popularity": 7
            }
        ]
    }
    
    # 将JSON转换为字符串并逐字符流式输出
    json_str = json.dumps(json_data, ensure_ascii=False)
    print(f"完整JSON: {json_str}")
    print(f"JSON长度: {len(json_str)}")
    print()
    
    # 逐字符输出，模拟流式响应
    chunk_size = 10  # 每次输出10个字符
    for i in range(0, len(json_str), chunk_size):
        chunk = json_str[i:i+chunk_size]
        print(f"发送chunk[{i}:{i+chunk_size}]: {repr(chunk)}")
        yield chunk
        await asyncio.sleep(0.01)  # 模拟网络延迟

async def debug_field_filtering():
    """调试字段过滤功能"""
    print("=== 调试字段过滤功能 ===")
    print("排除字段: ['year', 'creator']")
    print()
    
    # 创建流式解析器，排除year和creator字段
    stream = simulate_doubao_stream()
    
    print("=== 开始流式解析 ===")
    event_count = 0
    
    async for event in parse_json_stream_with_fields(
        stream,
        exclude_fields=['year', 'creator']
    ):
        event_count += 1
        print(f"\n事件 #{event_count}:")
        print(f"  类型: {event.event_type}")
        print(f"  路径: {event.data.path}")
        print(f"  数据值: {repr(event.data.value)}")
        print(f"  数据类型: {type(event.data.value)}")
        
        # 特别关注数字类型的数据
        if isinstance(event.data.value, (int, float)):
            print(f"  ⚠️  发现数字数据: {event.data.value}")
            print(f"  ⚠️  路径分析: {event.data.path}")
            
        # 特别关注包含数字的字符串
        if isinstance(event.data.value, str) and event.data.value.isdigit():
            print(f"  ⚠️  发现数字字符串: '{event.data.value}'")
            print(f"  ⚠️  路径分析: {event.data.path}")
            
        # 检查是否为delta事件且包含数字
        if event.event_type == EventType.DELTA and hasattr(event.data, 'delta_value'):
            delta_value = getattr(event.data, 'delta_value', None)
            if delta_value is not None:
                print(f"  Delta值: {repr(delta_value)}")
                print(f"  Delta值类型: {type(delta_value)}")
                if isinstance(delta_value, (int, float)):
                    print(f"  ⚠️  Delta包含数字: {delta_value}")
                elif isinstance(delta_value, str) and delta_value.isdigit():
                    print(f"  ⚠️  Delta包含数字字符串: '{delta_value}'")
    
    print(f"\n=== 解析完成，共处理 {event_count} 个事件 ===")

if __name__ == "__main__":
    asyncio.run(debug_field_filtering())