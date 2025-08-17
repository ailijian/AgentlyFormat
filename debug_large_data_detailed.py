#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
详细调试大数据处理测试失败问题
"""

import json
import time
import asyncio
import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from agently_format.core.streaming_parser import StreamingParser, FieldFilter
from agently_format.core.performance_optimizer import PerformanceOptimizer
from agently_format.core.memory_manager import MemoryManager
from agently_format.core.json_completer import CompletionStrategy
from agently_format.core.path_builder import PathStyle

async def debug_large_data_processing():
    """调试大数据处理问题"""
    print("=== 开始调试大数据处理测试 ===")
    
    # 创建字段过滤器
    field_filter = FieldFilter(exclude_paths=["secret", "password", "token"])
    
    # 创建流式解析器 - 增大缓冲区大小以避免分块
    parser = StreamingParser(
        enable_completion=True,
        completion_strategy=CompletionStrategy.SMART,
        path_style=PathStyle.DOT,
        max_depth=10,
        chunk_timeout=5.0,
        enable_diff_engine=True,
        diff_mode="smart",
        coalescing_enabled=True,
        coalescing_time_window_ms=100,
        buffer_size=1024*1024,  # 1MB缓冲区，足够容纳大JSON
        enable_schema_validation=False,
        adaptive_timeout_enabled=True,
        max_timeout=30.0,
        backoff_factor=1.5,
        field_filter=field_filter
    )
    
    # 创建大型测试数据（与测试相同）
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
    
    session_id = parser.create_session("large_data_test")
    
    # 分块处理大数据（与测试相同）
    json_str = json.dumps(large_data)
    chunk_size = 1024  # 1KB chunks
    chunks = [json_str[i:i+chunk_size] for i in range(0, len(json_str), chunk_size)]
    
    print(f"JSON数据大小: {len(json_str)} 字符")
    print(f"分块数量: {len(chunks)}")
    print(f"分块大小: {chunk_size} 字符")
    
    start_time = time.perf_counter()
    
    # 逐块处理并记录详细信息
    for i, chunk in enumerate(chunks):
        is_final = (i == len(chunks) - 1)
        print(f"\n--- 处理分块 {i+1}/{len(chunks)} (大小: {len(chunk)}, 最终: {is_final}) ---")
        
        try:
            result = await parser.parse_chunk(
                session_id,
                chunk,
                is_final=is_final
            )
            print(f"解析结果事件数量: {len(result)}")
            
            # 获取当前状态
            state = parser.get_parsing_state(session_id)
            if state:
                print(f"当前状态:")
                print(f"  - is_complete: {state.is_complete}")
                print(f"  - errors: {len(state.errors)}")
                print(f"  - parsing_errors: {len(state.parsing_errors)}")
                # print(f"  - validation_errors: {len(state.validation_errors)}")  # 属性不存在，跳过
                # print(f"  - buffer_size: {len(state.buffer.buffer)}")  # 属性不存在，跳过
                # print(f"  - total_size: {state.buffer.total_size}")  # 属性不存在，跳过
                
                # 显示错误详情
                if state.errors:
                    print(f"  错误详情:")
                    for j, error in enumerate(state.errors[:3]):  # 只显示前3个错误
                        print(f"    {j+1}. {error}")
                
                if state.parsing_errors:
                    print(f"  解析错误详情:")
                    for j, error in enumerate(state.parsing_errors[:3]):  # 只显示前3个错误
                        print(f"    {j+1}. {error}")
                
                # 检查缓冲区内容
                # buffer_content = state.buffer.get_soft_trimmed_content()  # 属性不存在，跳过
                # if buffer_content != chunk:
                #     print(f"  缓冲区内容与分块不同 (缓冲区大小: {len(buffer_content)})")
                #     if len(buffer_content) > 100:
                #         print(f"  缓冲区开头: {buffer_content[:50]}...")
                #         print(f"  缓冲区结尾: ...{buffer_content[-50:]}")
                #     else:
                #         print(f"  缓冲区内容: {buffer_content}")
            
        except Exception as e:
            print(f"处理分块时出错: {e}")
            import traceback
            traceback.print_exc()
    
    processing_time = time.perf_counter() - start_time
    
    # 最终状态检查
    print(f"\n=== 最终状态检查 ===")
    state = parser.get_parsing_state(session_id)
    if state:
        print(f"is_complete: {state.is_complete}")
        print(f"errors: {len(state.errors)}")
        print(f"parsing_errors: {len(state.parsing_errors)}")
        # print(f"validation_errors: {len(state.validation_errors)}")  # 属性不存在，跳过
        print(f"current_data keys: {list(state.current_data.keys()) if state.current_data else 'None'}")
        
        if 'users' in state.current_data:
            print(f"users数量: {len(state.current_data['users'])}")
        
        # 分析is_complete为False的原因
        print(f"\n=== is_complete分析 ===")
        print(f"len(state.errors) == 0: {len(state.errors) == 0}")
        print(f"len(state.parsing_errors) == 0: {len(state.parsing_errors) == 0}")
        # print(f"len(state.validation_errors) == 0: {len(state.validation_errors) == 0}")  # 属性不存在，跳过
        # print(f"state.buffer.is_balanced(): {state.buffer.is_balanced()}")  # 属性不存在，跳过
        
        # 检查缓冲区状态
        print(f"\n=== 缓冲区状态 ===")
        # print(f"buffer size: {len(state.buffer.buffer)}")  # 属性不存在，跳过
        # print(f"total_size: {state.buffer.total_size}")  # 属性不存在，跳过
        # print(f"bracket_balance: {state.buffer.bracket_balance}")  # 属性不存在，跳过
        # print(f"in_string: {state.buffer.in_string}")  # 属性不存在，跳过
        
        # if state.buffer.buffer:  # 属性不存在，跳过
        #     buffer_content = ''.join(state.buffer.buffer)
        #     print(f"缓冲区内容长度: {len(buffer_content)}")
        #     if len(buffer_content) > 200:
        #         print(f"缓冲区开头: {buffer_content[:100]}")
        #         print(f"缓冲区结尾: {buffer_content[-100:]}")
        #     else:
        #         print(f"缓冲区内容: {buffer_content}")
    
    print(f"\n处理时间: {processing_time:.2f}秒")
    print("=== 调试完成 ===")

if __name__ == "__main__":
    asyncio.run(debug_large_data_processing())