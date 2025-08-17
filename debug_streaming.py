#!/usr/bin/env python3
"""调试流式解析问题的详细测试脚本"""

import asyncio
import json
from src.agently_format.core.streaming_parser import parse_json_stream_with_fields

async def test_streaming_with_field_filtering():
    """测试带字段过滤的流式解析"""
    print("=== 测试流式解析字段过滤 ===")
    
    # 测试数据 - 模拟实际的JSON响应
    test_data = {
        "languages": [
            {
                "name": "Python",
                "description": "一种高级编程语言",
                "year": 1991,
                "creator": "Guido van Rossum",
                "popularity": 9
            },
            {
                "name": "Java",
                "description": "一种面向对象编程语言",
                "year": 1995,
                "creator": "James Gosling",
                "popularity": 8
            }
        ]
    }
    
    json_content = json.dumps(test_data)
    print(f"原始JSON: {json_content}")
    
    # 创建异步生成器
    async def content_stream():
        yield json_content
    
    print("\n=== 测试排除字段 (exclude_fields=['year', 'creator']) ===")
    
    # 测试排除字段
    stream_iter = content_stream()
    async for event in parse_json_stream_with_fields(
        stream_iter,
        include_fields=None,
        exclude_fields=["year", "creator"],
        exact_match=False
    ):
        print(f"事件类型: {event.event_type.value}")
        print(f"路径: {event.data.path}")
        if hasattr(event.data, 'delta_value'):
            print(f"增量值: {repr(event.data.delta_value)} (类型: {type(event.data.delta_value)})")
        if hasattr(event.data, 'value'):
            print(f"完整值: {repr(event.data.value)} (类型: {type(event.data.value)})")
        
        # 特别关注数字类型的输出
        if event.event_type.value == 'delta':
            if hasattr(event.data, 'delta_value') and event.data.delta_value is not None:
                delta_str = str(event.data.delta_value)
                print(f"转换为字符串: '{delta_str}'")
                if delta_str.isdigit():
                    print(f"⚠️  发现数字字符串: '{delta_str}'")
        print("---")

if __name__ == "__main__":
    asyncio.run(test_streaming_with_field_filtering())