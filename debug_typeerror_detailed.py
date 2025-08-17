#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
详细TypeError调试脚本
用于捕获和分析StreamingParser中的TypeError异常
"""

import asyncio
import traceback
import sys
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from agently_format.core.streaming_parser import StreamingParser
from agently_format.core.streaming_parser import FieldFilter
from agently_format.core.performance_optimizer import PerformanceOptimizer
from agently_format.core.memory_manager import MemoryManager

async def debug_typeerror():
    """调试TypeError异常"""
    print("=== TypeError详细调试 ===")
    
    try:
        # 创建解析器实例
        field_filter = FieldFilter(
            enabled=True,
            include_paths=['users.*', 'data.*'],
            exclude_paths=['*.password', '*.secret']
        )
        
        parser = StreamingParser(
            field_filter=field_filter
        )
        
        print("解析器创建成功")
        
        # 创建会话
        session_id = "debug_session"
        parser.create_session(session_id)
        print(f"会话创建成功: {session_id}")
        
        # 测试数据
        test_data = '{"users": [{"id": 1, "name": "Alice"}]}'
        print(f"开始解析: {test_data}")
        
        # 逐步解析
        try:
            events = await parser.parse_chunk(session_id, test_data, is_final=True)
            print(f"解析成功，事件数量: {len(events)}")
            
            for i, event in enumerate(events, 1):
                print(f"  事件 {i}: {event.event_type}")
                print(f"    数据类型: {type(event.data)}")
                print(f"    数据: {event.data}")
                
        except Exception as e:
            print(f"解析过程中发生异常: {type(e).__name__}: {str(e)}")
            print("详细堆栈跟踪:")
            traceback.print_exc()
            
            # 尝试获取更多信息
            print("\n=== 异常详细信息 ===")
            print(f"异常类型: {type(e)}")
            print(f"异常参数: {e.args}")
            if hasattr(e, '__cause__'):
                print(f"原因: {e.__cause__}")
            if hasattr(e, '__context__'):
                print(f"上下文: {e.__context__}")
        
        # 检查解析状态
        if session_id in parser.parsing_states:
            state = parser.parsing_states[session_id]
            print(f"\n=== 解析状态信息 ===")
            print(f"总块数: {state.total_chunks}")
            print(f"处理块数: {state.processed_chunks}")
            print(f"当前数据: {state.current_data}")
            print(f"错误数量: {len(state.errors)}")
            if state.errors:
                print("解析错误:")
                for error in state.errors:
                    print(f"  - {error}")
        
        # 清理
        await parser.finalize_session(session_id)
        print("会话已清理")
        
    except Exception as e:
        print(f"顶层异常: {type(e).__name__}: {str(e)}")
        print("详细堆栈跟踪:")
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(debug_typeerror())