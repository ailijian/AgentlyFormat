#!/usr/bin/env python3
"""
调试脚本：完全模拟test_error_handling_integration测试
"""

import asyncio
import sys
import os

# 添加src目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from agently_format.core.streaming_parser import StreamingParser
from agently_format.types.events import EventType

async def debug_test_exact():
    """完全模拟测试的行为"""
    print("=== 完全模拟test_error_handling_integration测试 ===")
    
    # 创建专门用于错误处理测试的解析器，禁用JSON补全器
    error_parser = StreamingParser(
        enable_completion=False,  # 禁用JSON补全器以确保错误被正确记录
        enable_diff_engine=True,
        max_depth=10,
        chunk_timeout=30.0
    )
    
    print(f"解析器配置:")
    print(f"  - enable_completion: {error_parser.enable_completion}")
    print(f"  - enable_diff_engine: {error_parser.enable_diff_engine}")
    print(f"  - max_depth: {error_parser.max_depth}")
    print(f"  - chunk_timeout: {error_parser.chunk_timeout}")
    
    session_id = "error_test"
    print(f"\n使用会话ID: {session_id}")
    
    events = []
    
    async def event_callback(event):
        events.append(event)
        print(f"收到事件回调: {event.event_type} - {type(event.data).__name__}")
        if hasattr(event.data, 'error_message'):
            print(f"  错误消息: {event.data.error_message}")
    
    error_parser.add_event_callback(EventType.ERROR, event_callback)
    print("已注册ERROR事件回调")
    
    # 解析前状态检查
    state_before = error_parser.get_parsing_state(session_id)
    print(f"\n解析前状态:")
    if state_before:
        print(f"  - errors列表长度: {len(state_before.errors)}")
        print(f"  - current_data: {state_before.current_data}")
    else:
        print(f"  - 会话不存在，这是预期的")
    
    # 解析无效JSON
    print(f"\n解析无效JSON: {{'invalid': json syntax here}}")
    result = await error_parser.parse_chunk(
        session_id,
        '{"invalid": json syntax here}',
        is_final=True
    )
    
    print(f"\n解析结果: {len(result)} 个事件")
    for i, event in enumerate(result, 1):
        print(f"  事件 {i}: {event.event_type}")
        if hasattr(event.data, 'error_message'):
            print(f"    错误消息: {event.data.error_message}")
    
    # 验证错误处理
    error_events = [e for e in events if e.event_type == EventType.ERROR]
    result_error_events = [e for e in result if e.event_type == EventType.ERROR]
    
    print(f"\n=== 错误事件验证 ===")
    print(f"回调收到的错误事件数量: {len(error_events)}")
    print(f"返回结果中的错误事件数量: {len(result_error_events)}")
    
    # 验证会话状态
    state = error_parser.get_parsing_state(session_id)
    print(f"\n=== 最终状态验证 ===")
    print(f"会话状态存在: {state is not None}")
    if state:
        print(f"会话错误列表长度: {len(state.errors)}")
        print(f"会话错误内容: {state.errors}")
        print(f"当前数据: {state.current_data}")
        print(f"处理的块数: {state.processed_chunks}")
        print(f"总块数: {state.total_chunks}")
    
    # 模拟测试断言
    print(f"\n=== 测试断言模拟 ===")
    
    # 应该有错误事件
    error_assertion_1 = len(error_events) > 0 or len(result_error_events) > 0
    print(f"✓ 错误事件断言: {error_assertion_1}" if error_assertion_1 else "✗ 错误事件断言失败")
    
    # 验证会话状态
    state_assertion = state is not None
    print(f"✓ 会话状态存在断言: {state_assertion}" if state_assertion else "✗ 会话状态存在断言失败")
    
    # 关键断言：state.errors应该有内容
    errors_assertion = len(state.errors) > 0 if state else False
    print(f"✓ 会话错误记录断言: {errors_assertion}" if errors_assertion else "✗ 会话错误记录断言失败 - 这是导致测试失败的原因")
    
    if not errors_assertion and state:
        print(f"  state.errors 长度: {len(state.errors)}")
        print(f"  期望: > 0")
        print(f"  实际: {len(state.errors)}")
    
    print(f"\n=== 调试总结 ===")
    print(f"1. JSON补全器已禁用: {not error_parser.enable_completion}")
    print(f"2. 错误事件已生成: {len(error_events) > 0 or len(result_error_events) > 0}")
    print(f"3. 会话状态存在: {state is not None}")
    print(f"4. 会话错误记录: {len(state.errors) if state else 0}")

if __name__ == "__main__":
    asyncio.run(debug_test_exact())