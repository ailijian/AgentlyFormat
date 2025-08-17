#!/usr/bin/env python3
"""
详细调试错误处理集成测试失败问题
"""

import asyncio
import json
from src.agently_format.core.streaming_parser import StreamingParser, FieldFilter
from src.agently_format.types.events import EventType

async def debug_error_handling():
    print("=== 详细调试错误处理集成测试 ===")
    
    try:
        # 创建字段过滤器
        field_filter = FieldFilter(
            enabled=True,
            include_paths=["users"],
            exclude_paths=[],
            mode="include",
            exact_match=False
        )
        
        # 创建集成解析器 - 禁用JSON补全器以重现测试失败
        integrated_parser = StreamingParser(
            enable_completion=False  # 禁用JSON补全器
        )
        
        print("✓ 解析器创建成功")
        
        # 创建会话
        session_id = integrated_parser.create_session("error_test")
        print(f"✓ 会话创建成功: {session_id}")
        
        # 设置事件回调
        events = []
        
        async def event_callback(event):
            events.append(event)
            print(f"收到事件: {event.event_type} - {event.data}")
        
        integrated_parser.add_event_callback(EventType.ERROR, event_callback)
        print("✓ 错误事件回调设置成功")
        
        # 解析无效JSON
        invalid_json = '{"invalid": json syntax here}'
        print(f"解析无效JSON: {invalid_json}")
        
        try:
            result = await integrated_parser.parse_chunk(
                invalid_json,
                session_id,
                is_final=True
            )
            print(f"解析结果: {len(result)} 个事件")
            for i, event in enumerate(result):
                print(f"  事件 {i+1}: {event.event_type} - {event.data}")
        except Exception as parse_error:
            print(f"解析过程中发生异常: {parse_error}")
            print(f"异常类型: {type(parse_error)}")
        
        # 检查事件
        print(f"\n=== 事件分析 ===")
        print(f"总事件数: {len(events)}")
        error_events = [e for e in events if e.event_type == EventType.ERROR]
        print(f"错误事件数: {len(error_events)}")
        
        result_error_events = [e for e in result if e.event_type == EventType.ERROR]
        print(f"结果中错误事件数: {len(result_error_events)}")
        
        # 检查会话状态
        print(f"\n=== 会话状态分析 ===")
        state = integrated_parser.get_parsing_state(session_id)
        if state:
            print(f"会话状态存在: {state.session_id}")
            print(f"会话错误数量: {len(state.errors)}")
            if state.errors:
                for i, error in enumerate(state.errors):
                    print(f"  错误 {i+1}: {error}")
            else:
                print("⚠️ 会话状态中没有错误记录！")
        else:
            print("❌ 会话状态不存在")
        
        # 模拟测试断言
        print(f"\n=== 测试断言分析 ===")
        
        # 第一个断言: assert len(error_events) > 0 or len(result_error_events) > 0
        assertion1 = len(error_events) > 0 or len(result_error_events) > 0
        print(f"断言1 (错误事件): {assertion1}")
        print(f"  len(error_events) = {len(error_events)}")
        print(f"  len(result_error_events) = {len(result_error_events)}")
        
        # 第二个断言: assert state is not None
        assertion2 = state is not None
        print(f"断言2 (会话状态存在): {assertion2}")
        
        # 第三个断言: assert len(state.errors) > 0
        if state:
            assertion3 = len(state.errors) > 0
            print(f"断言3 (会话错误记录): {assertion3}")
            print(f"  len(state.errors) = {len(state.errors)}")
            
            if not assertion3:
                print("❌ 这是失败的断言！state.errors为空")
                print("这可能对应测试中的 assert 0 > 0")
        else:
            print("断言3: 无法检查，会话状态不存在")
        
        # 检查JSON解析是否真的失败了
        print(f"\n=== JSON解析验证 ===")
        try:
            json.loads(invalid_json)
            print("⚠️ JSON解析竟然成功了！这不应该发生")
        except json.JSONDecodeError as e:
            print(f"✓ JSON解析确实失败: {e}")
        
    except Exception as e:
        print(f"调试过程中发生错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(debug_error_handling())