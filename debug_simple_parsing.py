#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简单的解析调试脚本
用于捕获具体的TypeError错误
"""

import asyncio
import json
import sys
import traceback
sys.path.insert(0, 'src')

from agently_format.core.streaming_parser import StreamingParser, FieldFilter
from agently_format.types.events import EventType

async def debug_simple_parsing():
    """简单的解析调试"""
    print("=== 简单解析调试 ===")
    
    try:
        # 创建最简单的解析器
        parser = StreamingParser()
        
        # 创建会话
        session_id = parser.create_session()
        print(f"创建会话: {session_id}")
        
        # 简单的JSON数据
        json_data = '{"name": "Alice", "age": 30}'
        
        print(f"开始解析: {json_data}")
        
        # 解析数据
        events = await parser.parse_chunk(
            session_id=session_id,
            chunk=json_data,
            is_final=True
        )
        
        print(f"解析完成，事件数量: {len(events)}")
        
        for i, event in enumerate(events):
            print(f"事件 {i+1}: {event.event_type}")
            if hasattr(event, 'data'):
                print(f"  数据: {event.data}")
                if hasattr(event.data, 'path'):
                    print(f"  路径: {event.data.path}")
                
    except Exception as e:
        print(f"❌ 发生错误: {type(e).__name__}: {str(e)}")
        print("\n完整错误堆栈:")
        traceback.print_exc()
        
        # 尝试分析错误位置
        tb = traceback.extract_tb(e.__traceback__)
        print("\n错误位置分析:")
        for frame in tb:
            if 'streaming_parser.py' in frame.filename:
                print(f"  文件: {frame.filename}")
                print(f"  行号: {frame.lineno}")
                print(f"  函数: {frame.name}")
                print(f"  代码: {frame.line}")

if __name__ == "__main__":
    asyncio.run(debug_simple_parsing())