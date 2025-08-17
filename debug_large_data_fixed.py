#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
调试大数据处理测试 - 修复版本
测试完整JSON处理而非固定分块
"""

import asyncio
import json
import time
import sys
sys.path.insert(0, 'src')
from agently_format.core.streaming_parser import StreamingParser, FieldFilter
from agently_format.enums import CompletionStrategy

async def debug_large_data_fixed():
    print("=== 大数据处理测试调试 - 修复版本 ===")
    
    # 创建大型测试数据
    large_data = {
        "users": [
            {
                "id": i,
                "name": f"User_{i}",
                "email": f"user{i}@example.com",
                "profile": {
                    "age": 20 + (i % 50),
                    "city": f"City_{i % 100}",
                    "preferences": [f"pref_{j}" for j in range(5)]
                }
            }
            for i in range(1000)  # 1000个用户
        ],
        "data": {
            "total_users": 1000,
            "generated_at": "2024-01-01T00:00:00Z",
            "metadata": {f"key_{i}": f"value_{i}" for i in range(100)}
        }
    }
    
    # 创建解析器 - 使用大缓冲区
    parser = StreamingParser(
        enable_completion=True,
        completion_strategy=CompletionStrategy.SMART,
        enable_diff_engine=True,
        buffer_size=1024*1024  # 1MB缓冲区
    )
    
    session_id = parser.create_session("large_data_test")
    
    # 转换为JSON字符串
    json_str = json.dumps(large_data)
    print(f"JSON大小: {len(json_str)} 字符")
    
    start_time = time.perf_counter()
    
    try:
        # 直接处理完整JSON
        print("开始处理完整JSON...")
        result = await parser.parse_chunk(
            session_id,
            json_str,
            is_final=True
        )
        
        processing_time = time.perf_counter() - start_time
        print(f"处理时间: {processing_time:.2f}秒")
        print(f"生成事件数量: {len(result)}")
        
        # 获取解析状态
        state = parser.get_parsing_state(session_id)
        if state:
            print(f"\n=== 解析状态 ===")
            print(f"is_complete: {state.is_complete}")
            print(f"errors: {len(state.errors)}")
            print(f"parsing_errors: {len(state.parsing_errors)}")
            
            if state.errors:
                print("错误详情:")
                for i, error in enumerate(state.errors[:3], 1):
                    print(f"  {i}. {error}")
            
            if state.parsing_errors:
                print("解析错误详情:")
                for i, error in enumerate(state.parsing_errors[:3], 1):
                    print(f"  {i}. {error}")
            
            if hasattr(state, 'current_data') and state.current_data:
                print(f"current_data keys: {list(state.current_data.keys())}")
                if 'users' in state.current_data:
                    print(f"users数量: {len(state.current_data['users'])}")
            
            # 测试断言条件
            print(f"\n=== 测试断言检查 ===")
            print(f"state.is_complete: {state.is_complete}")
            if hasattr(state, 'current_data') and state.current_data and 'users' in state.current_data:
                users_count = len(state.current_data['users'])
                print(f"len(state.current_data['users']): {users_count}")
                print(f"users_count == 1000: {users_count == 1000}")
            else:
                print("current_data或users字段不存在")
            
            print(f"processing_time < 10.0: {processing_time < 10.0}")
            
            # 内存检查
            memory_info = parser.memory_manager.get_memory_usage()
            print(f"process_memory_mb: {memory_info.get('process_memory_mb', 'N/A')}")
            if 'process_memory_mb' in memory_info:
                print(f"memory < 500MB: {memory_info['process_memory_mb'] < 500}")
        
    except Exception as e:
        print(f"处理异常: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n=== 调试完成 ===")

if __name__ == "__main__":
    asyncio.run(debug_large_data_fixed())
