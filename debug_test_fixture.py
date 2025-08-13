#!/usr/bin/env python3
"""调试测试fixture行为"""

import sys
sys.path.insert(0, 'src')

import asyncio
import json
from agently_format.core.streaming_parser import StreamingParser

async def test_fixture_behavior():
    """测试fixture行为"""
    print("=== 测试fixture行为 ===")
    
    # 创建与fixture相同的解析器
    parser = StreamingParser()  # 默认配置
    
    print(f"enable_diff_engine: {parser.enable_diff_engine}")
    print(f"diff_engine: {parser.diff_engine}")
    
    # 使用与测试相同的数据
    chunks = [
        '{"users": [',
        '{"id": 1, "name": "Alice",',
        '"email": "alice@example.com"},',
        '{"id": 2, "name": "Bob",',
        '"email": "bob@example.com"}',
        '], "total": 2}'
    ]
    
    session_id = "test-incomplete"
    parser.create_session(session_id)
    
    print("\n处理块:")
    for i, chunk in enumerate(chunks):
        is_final = (i == len(chunks) - 1)
        print(f"块 {i+1}: {chunk}")
        
        # 获取处理前的状态
        state_before = parser.get_parsing_state(session_id)
        print(f"  处理前 current_data: {state_before.current_data}")
        
        # 处理块
        result = await parser.parse_chunk(
            chunk,
            session_id,
            is_final=is_final
        )
        
        # 获取处理后的状态
        state_after = parser.get_parsing_state(session_id)
        print(f"  处理后 current_data: {state_after.current_data}")
        print(f"  生成事件数量: {len(result)}")
        print()
    
    # 检查最终状态
    state = parser.get_parsing_state(session_id)
    print(f"最终状态:")
    print(f"  current_data: {json.dumps(state.current_data, indent=2, ensure_ascii=False)}")
    print(f"  is_complete: {getattr(state, 'is_complete', 'N/A')}")
    print(f"  'users' in current_data: {'users' in state.current_data}")
    print(f"  'total' in current_data: {'total' in state.current_data}")
    
    # 模拟测试断言
    try:
        assert state is not None
        assert state.is_complete
        assert "users" in state.current_data
        assert "total" in state.current_data
        print("\n✅ 所有断言通过！")
    except AssertionError as e:
        print(f"\n❌ 断言失败: {e}")
        print(f"实际的 current_data 键: {list(state.current_data.keys())}")

if __name__ == "__main__":
    asyncio.run(test_fixture_behavior())