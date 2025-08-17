#!/usr/bin/env python3
"""调试统计收集功能"""

import sys
import os
import asyncio
sys.path.insert(0, 'src')

from agently_format.core.streaming_parser import StreamingParser

async def test_statistics():
    """测试统计信息收集"""
    print("=== 调试统计收集功能 ===")
    
    try:
        # 创建解析器
        parser = StreamingParser(enable_diff_engine=True)
        print("✓ 解析器创建成功")
        
        # 创建会话
        session_id = parser.create_session("stats-test")
        print(f"✓ 会话创建成功: {session_id}")
        
        # 解析数据
        print("开始解析数据...")
        await parser.parse_chunk(session_id, '{"test": "data"}', is_final=True)
        print("✓ 数据解析完成")
        
        # 获取统计信息
        print("获取统计信息...")
        stats = parser.get_stats()
        print(f"统计信息: {stats}")
        
        # 验证统计信息
        if "active_sessions" in stats:
            print(f"✓ active_sessions: {stats['active_sessions']}")
        else:
            print("✗ 缺少 active_sessions")
            
        if "total_events_emitted" in stats:
            print(f"✓ total_events_emitted: {stats['total_events_emitted']}")
        else:
            print("✗ 缺少 total_events_emitted")
            
        print("=== 测试完成 ===")
        
    except Exception as e:
        print(f"✗ 错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_statistics())