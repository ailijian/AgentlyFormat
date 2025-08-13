#!/usr/bin/env python3
"""调试差分引擎行为"""

import sys
sys.path.insert(0, 'src')

import asyncio
import json
from agently_format.core.streaming_parser import StreamingParser
from agently_format.core.diff_engine import create_diff_engine

async def test_diff_engine():
    """测试差分引擎处理增量数据的行为"""
    print("=== 测试差分引擎行为 ===")
    
    # 创建差分引擎
    diff_engine = create_diff_engine(mode="smart", coalescing_enabled=True)
    
    # 测试数据：从空字典到完整数据
    old_data = {}
    new_data = {
        "users": [
            {"id": 1, "name": "Alice", "email": "alice@example.com"},
            {"id": 2, "name": "Bob", "email": "bob@example.com"}
        ],
        "total": 2
    }
    
    print(f"旧数据: {old_data}")
    print(f"新数据: {json.dumps(new_data, indent=2, ensure_ascii=False)}")
    
    # 计算差分
    diff_results = diff_engine.compute_diff(old_data=old_data, new_data=new_data)
    
    print(f"\n差分结果数量: {len(diff_results)}")
    for i, diff_result in enumerate(diff_results):
        print(f"差分 {i+1}:")
        print(f"  路径: {diff_result.path}")
        print(f"  类型: {diff_result.diff_type}")
        print(f"  旧值: {diff_result.old_value}")
        print(f"  新值: {diff_result.new_value}")
        print()
    
    # 测试事件生成
    print("=== 测试事件生成 ===")
    for diff_result in diff_results:
        event = diff_engine.emit_delta_event(
            diff_result=diff_result,
            session_id="test-session",
            sequence_number=1
        )
        if event:
            print(f"生成事件: {event.event_type} - {event.path} = {event.value}")
        else:
            print(f"事件被抑制: {diff_result.path}")

async def test_streaming_parser_with_debug():
    """测试流式解析器的调试版本"""
    print("\n=== 测试流式解析器 ===")
    
    parser = StreamingParser(enable_diff_engine=True)
    session_id = parser.create_session("debug-session")
    
    chunks = [
        '{"users": [',
        '{"id": 1, "name": "Alice",',
        '"email": "alice@example.com"},',
        '{"id": 2, "name": "Bob",',
        '"email": "bob@example.com"}',
        '], "total": 2}'
    ]
    
    print("处理块:")
    for i, chunk in enumerate(chunks):
        print(f"块 {i+1}: {chunk}")
        is_final = (i == len(chunks) - 1)
        
        # 获取处理前的状态
        state_before = parser.get_parsing_state(session_id)
        print(f"  处理前 current_data: {state_before.current_data}")
        
        # 处理块
        events = await parser.parse_chunk(chunk, session_id, is_final=is_final)
        
        # 获取处理后的状态
        state_after = parser.get_parsing_state(session_id)
        print(f"  处理后 current_data: {state_after.current_data}")
        print(f"  生成事件数量: {len(events)}")
        
        for event in events:
            print(f"    事件: {event.event_type} - {event.data.path} = {getattr(event.data, 'value', 'N/A')}")
        print()
    
    # 最终状态
    final_state = parser.get_parsing_state(session_id)
    print(f"最终状态:")
    print(f"  current_data: {json.dumps(final_state.current_data, indent=2, ensure_ascii=False)}")
    print(f"  is_complete: {getattr(final_state, 'is_complete', 'N/A')}")
    print(f"  completed_fields: {final_state.completed_fields}")

if __name__ == "__main__":
    asyncio.run(test_diff_engine())
    asyncio.run(test_streaming_parser_with_debug())