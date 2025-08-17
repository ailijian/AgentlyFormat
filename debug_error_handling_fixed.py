#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
调试修复后的错误处理集成测试
验证禁用JSON补全器后错误是否能正确记录到state.errors
"""

import asyncio
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from agently_format.core.streaming_parser import StreamingParser
from agently_format.core.streaming_parser import EventType

async def debug_fixed_error_handling():
    """调试修复后的错误处理逻辑"""
    print("=== 调试修复后的错误处理集成测试 ===")
    
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
    print(f"  - completion_strategy: {error_parser.completion_strategy}")
    
    session_id = error_parser.create_session("error_test")
    print(f"\n创建会话: {session_id}")
    
    events = []
    
    async def event_callback(event):
        events.append(event)
        print(f"收到事件: {event.event_type} - {event.data if hasattr(event, 'data') else 'N/A'}")
    
    error_parser.add_event_callback(EventType.ERROR, event_callback)
    print("已注册错误事件回调")
    
    # 解析无效JSON
    invalid_json = '{"invalid": json syntax here}'
    print(f"\n解析无效JSON: {invalid_json}")
    
    try:
        result = await error_parser.parse_chunk(
            invalid_json,
            session_id,
            is_final=True
        )
        print(f"解析结果: {len(result)} 个事件")
        
        for i, event in enumerate(result):
            print(f"  事件 {i+1}: {event.event_type}")
            if event.event_type == EventType.ERROR:
                print(f"    错误消息: {getattr(event, 'error_message', 'N/A')}")
    except Exception as e:
        print(f"解析过程中发生异常: {e}")
        import traceback
        traceback.print_exc()
    
    # 验证错误处理
    error_events = [e for e in events if e.event_type == EventType.ERROR]
    result_error_events = [e for e in result if e.event_type == EventType.ERROR]
    
    print(f"\n=== 错误事件验证 ===")
    print(f"回调收到的错误事件数量: {len(error_events)}")
    print(f"返回结果中的错误事件数量: {len(result_error_events)}")
    
    # 验证会话状态
    state = error_parser.get_parsing_state(session_id)
    print(f"\n=== 会话状态验证 ===")
    print(f"会话状态存在: {state is not None}")
    
    if state:
        print(f"会话错误列表长度: {len(state.errors)}")
        print(f"会话错误内容: {state.errors}")
        print(f"会话是否完成: {state.is_complete}")
        print(f"当前数据: {state.current_data}")
    
    # 模拟测试断言
    print(f"\n=== 测试断言模拟 ===")
    
    try:
        # 应该有错误事件
        assert len(error_events) > 0 or len(result_error_events) > 0
        print("✓ 错误事件断言通过")
    except AssertionError:
        print("✗ 错误事件断言失败")
    
    try:
        # 验证会话状态
        assert state is not None
        print("✓ 会话状态存在断言通过")
    except AssertionError:
        print("✗ 会话状态存在断言失败")
    
    try:
        # 关键断言：会话错误记录
        assert len(state.errors) > 0
        print("✓ 会话错误记录断言通过")
    except AssertionError:
        print("✗ 会话错误记录断言失败 - 这是导致测试失败的原因")
        print(f"  state.errors 长度: {len(state.errors)}")
        print(f"  期望: > 0")
        print(f"  实际: {len(state.errors)}")
    
    print(f"\n=== 调试总结 ===")
    print(f"1. JSON补全器已禁用: {not error_parser.enable_completion}")
    print(f"2. 错误事件已生成: {len(error_events) > 0 or len(result_error_events) > 0}")
    print(f"3. 会话状态存在: {state is not None}")
    print(f"4. 会话错误记录: {len(state.errors) if state else 'N/A'}")

if __name__ == "__main__":
    asyncio.run(debug_fixed_error_handling())