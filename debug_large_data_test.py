#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
import asyncio
import json
import time

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'src'))

from agently_format.core.streaming_parser import StreamingParser, FieldFilter
from agently_format.core.performance_optimizer import PerformanceOptimizer
from agently_format.core.memory_manager import MemoryManager
from agently_format.exceptions import ErrorHandler

async def debug_large_data_test():
    """调试大数据处理测试失败问题"""
    print("=== 大数据处理调试 ===")
    
    # 创建集成解析器（与测试相同的配置）
    integrated_parser = StreamingParser(
        enable_completion=True,
        enable_diff_engine=True,
        max_depth=10,
        chunk_timeout=30.0,
        buffer_size=8192,
        enable_schema_validation=True,
        adaptive_timeout_enabled=True,
        field_filter=FieldFilter(
            enabled=True,
            include_paths=['users', 'users.*', 'data', 'data.*'],
            exclude_paths=['*.password', '*.secret']
        )
    )
    
    # 创建大型测试数据（简化版本）
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
            for i in range(100)  # 减少到100个用户便于调试
        ],
        "data": {
            "total_users": 100,
            "generated_at": "2024-01-01T00:00:00Z",
            "metadata": {f"key_{i}": f"value_{i}" for i in range(10)}
        }
    }
    
    session_id = integrated_parser.create_session("large_data_test")
    print(f"创建会话: {session_id}")
    
    # 分块处理大数据
    json_str = json.dumps(large_data)
    chunk_size = 1024  # 1KB chunks
    chunks = [json_str[i:i+chunk_size] for i in range(0, len(json_str), chunk_size)]
    
    print(f"JSON字符串长度: {len(json_str)}")
    print(f"分块数量: {len(chunks)}")
    
    start_time = time.perf_counter()
    
    for i, chunk in enumerate(chunks):
        is_final = (i == len(chunks) - 1)
        print(f"\n--- 处理块 {i+1}/{len(chunks)} (final={is_final}) ---")
        print(f"块大小: {len(chunk)}")
        
        result = await integrated_parser.parse_chunk(
            session_id,
            chunk,
            is_final=is_final
        )
        
        print(f"解析结果事件数: {len(result)}")
        
        # 检查解析状态
        state = integrated_parser.get_parsing_state(session_id)
        if state:
            print(f"解析状态:")
            print(f"  processed_chunks: {state.processed_chunks}")
            print(f"  total_chunks: {state.total_chunks}")
            print(f"  errors: {len(state.errors)}")
            print(f"  parsing_errors: {len(state.parsing_errors)}")
            print(f"  current_data keys: {list(state.current_data.keys()) if state.current_data else 'None'}")
            print(f"  current_data empty: {not bool(state.current_data)}")
            print(f"  is_complete: {state.is_complete}")
            
            if state.errors:
                print(f"  错误详情: {state.errors}")
            if state.parsing_errors:
                print(f"  解析错误详情: {state.parsing_errors}")
    
    processing_time = time.perf_counter() - start_time
    print(f"\n=== 最终结果 ===")
    print(f"处理时间: {processing_time:.3f}秒")
    
    # 最终状态检查
    final_state = integrated_parser.get_parsing_state(session_id)
    if final_state:
        print(f"\n最终解析状态:")
        print(f"  is_complete: {final_state.is_complete}")
        print(f"  processed_chunks: {final_state.processed_chunks}")
        print(f"  errors: {len(final_state.errors)}")
        print(f"  parsing_errors: {len(final_state.parsing_errors)}")
        print(f"  current_data: {bool(final_state.current_data)}")
        
        if final_state.current_data:
            print(f"  users数量: {len(final_state.current_data.get('users', []))}")
            print(f"  data字段: {'data' in final_state.current_data}")
        
        # 详细分析is_complete的每个条件
        print(f"\nis_complete条件分析:")
        print(f"  len(state.errors) == 0: {len(final_state.errors) == 0}")
        print(f"  state.processed_chunks > 0: {final_state.processed_chunks > 0}")
        print(f"  bool(state.current_data): {bool(final_state.current_data)}")
        print(f"  len(state.parsing_errors) == 0: {len(final_state.parsing_errors) == 0}")

if __name__ == "__main__":
    asyncio.run(debug_large_data_test())