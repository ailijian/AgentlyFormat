#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
字段过滤TypeError错误调试脚本
专门用于捕获和分析字段过滤功能中的TypeError错误
"""

import sys
import traceback
import json
import asyncio
from src.agently_format.core.streaming_parser import StreamingParser, FieldFilter

async def debug_field_filter_error():
    """调试字段过滤TypeError错误"""
    print("=== 字段过滤TypeError错误调试 ===")
    
    try:
        # 创建字段过滤器
        print("\n1. 创建字段过滤器...")
        field_filter = FieldFilter(
            enabled=True,
            mode='include',
            include_paths=['users', 'data'],
            exclude_paths=[]
        )
        print(f"字段过滤器创建成功: {field_filter}")
        
        # 创建解析器
        print("\n2. 创建StreamingParser...")
        parser = StreamingParser(
            field_filter=field_filter
        )
        print(f"解析器创建成功: {parser}")
        
        # 创建会话
        print("\n3. 创建解析会话...")
        session_id = parser.create_session()
        print(f"会话创建成功: {session_id}")
        
        # 准备测试数据
        test_data = {
            "users": [
                {
                    "id": 1,
                    "name": "Alice"
                }
            ]
        }
        
        json_chunk = json.dumps(test_data)
        print(f"\n4. 测试数据: {json_chunk}")
        
        # 尝试解析数据
        print("\n5. 开始解析数据...")
        events = await parser.parse_chunk(session_id, json_chunk, is_final=True)
        
        print(f"\n6. 解析完成，事件数量: {len(events)}")
        for i, event in enumerate(events):
            print(f"事件 {i}: {event.event_type}")
            if hasattr(event, 'data') and hasattr(event.data, 'metadata'):
                metadata = event.data.metadata
                if 'error_type' in metadata:
                    print(f"  错误类型: {metadata['error_type']}")
                if 'error_message' in metadata:
                    print(f"  错误信息: {metadata['error_message']}")
                if 'traceback' in metadata:
                    print(f"  错误堆栈: {metadata['traceback']}")
        
        print("\n=== 调试完成 ===")
        
    except Exception as e:
        print(f"\n!!! 捕获到异常: {type(e).__name__}: {e}")
        print("\n完整错误堆栈:")
        traceback.print_exc()
        return False
    
    return True

if __name__ == "__main__":
    success = asyncio.run(debug_field_filter_error())
    print(f"\n调试结果: {'成功' if success else '失败'}")