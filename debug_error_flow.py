#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
调试错误处理流程的详细脚本
追踪_handle_parsing_error方法是否被调用
"""

import asyncio
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from agently_format.core.streaming_parser import StreamingParser, EventType
from agently_format.core.json_completer import CompletionStrategy

async def debug_error_flow():
    print("=== 调试错误处理流程 ===")
    
    # 创建解析器，明确禁用JSON补全器
    parser = StreamingParser(
        enable_completion=False,  # 明确禁用
        enable_diff_engine=True,
        completion_strategy=CompletionStrategy.SMART
    )
    
    print(f"解析器配置:")
    print(f"  - enable_completion: {parser.enable_completion}")
    print(f"  - json_completer: {parser.json_completer}")
    print(f"  - enable_diff_engine: {parser.enable_diff_engine}")
    print(f"  - completion_strategy: {parser.completion_strategy}")
    
    # 创建会话
    session_id = "debug_flow"
    parser.create_session(session_id)
    print(f"\n创建会话: {session_id}")
    
    # 收集事件
    events_received = []
    
    async def event_callback(event):
        events_received.append(event)
        print(f"收到事件: {event.event_type} - {type(event.data).__name__}")
        if hasattr(event.data, 'error_message'):
            print(f"  错误消息: {event.data.error_message}")
        elif hasattr(event.data, 'metadata') and 'error_type' in event.data.metadata:
            print(f"  错误类型: {event.data.metadata['error_type']}")
    
    # 注册所有事件类型的回调
    from agently_format.types.events import EventType
    for event_type in [EventType.ERROR, EventType.DELTA, EventType.DONE, EventType.START, EventType.FINISH]:
        parser.add_event_callback(event_type, event_callback)
    print("已注册事件回调")
    
    # 在解析前检查状态
    state = parser.parsing_states[session_id]
    print(f"\n解析前状态:")
    print(f"  - errors列表长度: {len(state.errors)}")
    print(f"  - current_data: {state.current_data}")
    
    # 解析无效JSON
    invalid_json = '{"invalid": json syntax here}'
    print(f"\n解析无效JSON: {invalid_json}")
    
    try:
        # 添加调试信息到解析器
        original_handle_parsing_error = parser._handle_parsing_error
        original_parse_json_chunk = parser._parse_json_chunk
        
        async def debug_handle_parsing_error(*args, **kwargs):
            print(f"[DEBUG] _handle_parsing_error 被调用")
            print(f"[DEBUG] 参数: args={len(args)}, kwargs={kwargs.keys()}")
            result = await original_handle_parsing_error(*args, **kwargs)
            print(f"[DEBUG] _handle_parsing_error 返回 {len(result)} 个事件")
            return result
        
        async def debug_parse_json_chunk(*args, **kwargs):
            print(f"[DEBUG] _parse_json_chunk 被调用")
            print(f"[DEBUG] 输入chunk: {args[1][:50] if len(args) > 1 else 'N/A'}...")
            try:
                result = await original_parse_json_chunk(*args, **kwargs)
                print(f"[DEBUG] _parse_json_chunk 返回: {type(result)} - {result is None}")
                return result
            except Exception as e:
                print(f"[DEBUG] _parse_json_chunk 抛出异常: {type(e).__name__}: {e}")
                raise
        
        # 替换方法进行调试
        parser._handle_parsing_error = debug_handle_parsing_error
        parser._parse_json_chunk = debug_parse_json_chunk
        
        events = await parser.parse_chunk(session_id, invalid_json, is_final=True)
        
        print(f"\n解析结果: {len(events)} 个事件")
        for i, event in enumerate(events, 1):
            print(f"  事件 {i}: {event.event_type}")
            if hasattr(event.data, 'error_message'):
                print(f"    错误消息: {event.data.error_message}")
            elif hasattr(event.data, 'metadata'):
                print(f"    元数据: {event.data.metadata}")
        
    except Exception as e:
        print(f"解析过程中发生异常: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
    
    # 检查最终状态
    print(f"\n=== 最终状态验证 ===")
    final_state = parser.parsing_states[session_id]
    print(f"会话状态存在: {session_id in parser.parsing_states}")
    print(f"会话错误列表长度: {len(final_state.errors)}")
    print(f"会话错误内容: {final_state.errors}")
    print(f"当前数据: {final_state.current_data}")
    print(f"处理的块数: {getattr(final_state, 'processed_chunks', 'N/A')}")
    print(f"总块数: {getattr(final_state, 'total_chunks', 'N/A')}")
    
    print(f"\n=== 事件验证 ===")
    print(f"回调收到的事件数量: {len(events_received)}")
    print(f"返回结果中的事件数量: {len(events)}")
    
    error_events = [e for e in events if e.event_type == EventType.ERROR]
    print(f"错误事件数量: {len(error_events)}")
    
    print(f"\n=== 测试断言模拟 ===")
    try:
        assert len(error_events) > 0, "应该有错误事件"
        print("✓ 错误事件断言通过")
    except AssertionError as e:
        print(f"✗ 错误事件断言失败: {e}")
    
    try:
        assert session_id in parser.parsing_states, "会话状态应该存在"
        print("✓ 会话状态存在断言通过")
    except AssertionError as e:
        print(f"✗ 会话状态存在断言失败: {e}")
    
    try:
        assert len(final_state.errors) > 0, "会话错误列表应该不为空"
        print("✓ 会话错误记录断言通过")
    except AssertionError as e:
        print(f"✗ 会话错误记录断言失败 - 这是导致测试失败的原因")
        print(f"  state.errors 长度: {len(final_state.errors)}")
        print(f"  期望: > 0")
        print(f"  实际: {len(final_state.errors)}")
    
    print(f"\n=== 调试总结 ===")
    print(f"1. JSON补全器已禁用: {parser.json_completer is None}")
    print(f"2. 错误事件已生成: {len(error_events) > 0}")
    print(f"3. 会话状态存在: {session_id in parser.parsing_states}")
    print(f"4. 会话错误记录: {len(final_state.errors)}")

if __name__ == "__main__":
    asyncio.run(debug_error_flow())