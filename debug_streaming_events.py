#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
流式事件调试脚本
详细追踪流式解析过程中的每个事件
"""

import asyncio
import json
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from agently_format.core.streaming_parser import StreamingParser
from agently_format.core.streaming_parser import FieldFilter

async def simulate_doubao_stream():
    """模拟豆包API的流式响应"""
    # 模拟完整的JSON响应
    json_response = {
        "languages": [
            {
                "name": "Python",
                "year": 1991,
                "creator": "Guido van Rossum",
                "description": "一种解释型、面向对象、动态数据类型的高级程序设计语言，以其简洁的语法和强大的功能而受到广泛欢迎。",
                "popularity": 9
            },
            {
                "name": "Java", 
                "year": 1995,
                "creator": "James Gosling",
                "description": "一种广泛使用的编程语言和平台，具有跨平台、面向对象、高性能等特点，被广泛应用于企业级应用开发、移动应用开发等领域。",
                "popularity": 8
            },
            {
                "name": "JavaScript",
                "year": 1995, 
                "creator": "Brendan Eich",
                "description": "一种基于对象和事件驱动的脚本语言，主要用于网页开发，能够实现网页的交互效果和动态内容更新。",
                "popularity": 7
            }
        ]
    }
    
    # 将JSON转换为字符串并一次性返回（模拟完整响应）
    json_str = json.dumps(json_response, ensure_ascii=False, indent=2)
    yield json_str

async def debug_streaming_events():
    """调试流式事件生成过程"""
    print("=== 调试流式事件生成过程 ===")
    print("排除字段: ['year', 'creator']")
    print()
    
    # 创建流式解析器，排除year和creator字段
    stream = simulate_doubao_stream()
    
    # 创建字段过滤器
    field_filter = FieldFilter(
        enabled=True,
        exclude_paths=['year', 'creator'],
        mode='exclude'
    )
    
    # 创建流式解析器
    parser = StreamingParser(field_filter=field_filter)
    
    event_count = 0
    collected_output = ""
    
    # 使用parse_stream方法
    async for event in parser.parse_stream(stream):
        event_count += 1
        print(f"事件 #{event_count}:")
        print(f"  类型: {event.event_type.value}")
        print(f"  路径: {event.data.path}")
        print(f"  数据值: {repr(event.data.value)}")
        print(f"  数据类型: {type(event.data.value)}")
        
        if hasattr(event.data, 'delta_value') and event.data.delta_value is not None:
            delta_value = event.data.delta_value
            print(f"  Delta值: {repr(delta_value)}")
            print(f"  Delta类型: {type(delta_value)}")
            
            # 检查是否为数字或包含数字的字符串
            if isinstance(delta_value, (int, float)):
                print(f"  ⚠️  Delta包含数字: {delta_value}")
            elif isinstance(delta_value, str):
                if delta_value.isdigit():
                    print(f"  ⚠️  Delta是纯数字字符串: '{delta_value}'")
                elif any(char.isdigit() for char in delta_value):
                    print(f"  ⚠️  Delta包含数字字符: '{delta_value}'")
                    
            # 如果是DELTA事件，收集输出
            if event.event_type.value == 'delta':
                collected_output += str(delta_value)
                print(f"  累积输出: {repr(collected_output)}")
        
        print()
    
    print(f"=== 解析完成，共处理 {event_count} 个事件 ===")
    print(f"最终累积输出: {repr(collected_output)}")
    print()
    
    # 分析输出中的数字
    digits_in_output = [char for char in collected_output if char.isdigit()]
    if digits_in_output:
        print(f"输出中包含的数字字符: {digits_in_output}")
        print("这些数字可能来自:")
        print("- popularity字段的值 (9, 8, 7)")
        print("- year字段的值 (1991, 1995, 1995) - 应该被排除")
    else:
        print("输出中没有数字字符")

if __name__ == "__main__":
    asyncio.run(debug_streaming_events())