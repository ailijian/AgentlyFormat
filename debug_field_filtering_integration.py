#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
调试字段过滤集成测试失败的原因
分析test_field_filtering_with_optimization测试失败的具体问题：
1) 解析成功但没有生成Delta事件
2) users路径应该被包含但字段过滤返回False
"""

import sys
import os
import json
import asyncio
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from agently_format.core.streaming_parser import StreamingParser, FieldFilter
from agently_format.core.performance_optimizer import PerformanceOptimizer
from agently_format.types.events import EventType

def debug_field_filtering_integration():
    """调试字段过滤集成测试失败的原因"""
    print("=== 调试字段过滤集成测试失败原因 ===")
    
    # 使用与测试相同的配置
    test_data = {
        "users": [
            {
                "id": 1,
                "name": "Alice",
                "email": "alice@example.com",
                "password": "secret123",
                "profile": {
                    "age": 25,
                    "secret": "top_secret"
                }
            }
        ],
        "data": {
            "count": 1,
            "api_key": "admin123"
        },
        "system": {
            "version": "1.0",
            "password": "system_secret"
        }
    }
    
    # 创建性能优化器
    optimizer = PerformanceOptimizer()
    
    # 创建字段过滤器 - 与测试相同的配置
    field_filter = FieldFilter(
        enabled=True,
        include_paths=["users", "data"],
        exclude_paths=["password", "secret", "admin"],
        mode="include",
        exact_match=False,
        performance_optimizer=optimizer
    )
    
    print(f"字段过滤器配置:")
    print(f"  enabled: {field_filter.enabled}")
    print(f"  include_paths: {field_filter.include_paths}")
    print(f"  exclude_paths: {field_filter.exclude_paths}")
    print(f"  mode: {field_filter.mode}")
    print(f"  exact_match: {field_filter.exact_match}")
    print()
    
    # 创建StreamingParser
    parser = StreamingParser(field_filter=field_filter)
    
    # 事件收集器
    events = []
    
    def collect_event(event):
        events.append(event)
        # 安全地访问事件数据
        path = getattr(event.data, 'path', 'N/A') if hasattr(event.data, 'path') else 'N/A'
        value = getattr(event.data, 'value', 'N/A') if hasattr(event.data, 'value') else 'N/A'
        print(f"收到事件: {event.event_type} - 路径: {path} - 值: {value}")
    
    # 注册事件回调
    parser.add_event_callback(EventType.DELTA, collect_event)
    parser.add_event_callback(EventType.DONE, collect_event)
    parser.add_event_callback(EventType.ERROR, collect_event)
    
    print("=== 开始解析过程 ===")
    
    # 创建会话
    session_id = parser.create_session()
    print(f"创建会话: {session_id}")
    
    # 将测试数据转换为JSON字符串
    json_str = json.dumps(test_data, ensure_ascii=False)
    print(f"JSON字符串长度: {len(json_str)}")
    print(f"JSON内容: {json_str[:200]}..." if len(json_str) > 200 else f"JSON内容: {json_str}")
    print()
    
    # 模拟分块解析
    chunk_size = 50  # 小块大小，模拟流式输入
    chunks = [json_str[i:i+chunk_size] for i in range(0, len(json_str), chunk_size)]
    
    print(f"分成 {len(chunks)} 个块进行解析:")
    for i, chunk in enumerate(chunks):
        print(f"  块 {i+1}: '{chunk}'")
    print()
    
    # 逐块解析
    async def parse_chunks():
        try:
            for i, chunk in enumerate(chunks):
                print(f"\n--- 处理块 {i+1}/{len(chunks)} ---")
                print(f"块内容: '{chunk}'")
                
                # 获取解析前的状态
                state = parser.parsing_states.get(session_id)
                if state:
                    print(f"解析前状态:")
                    print(f"  当前数据: {state.current_data}")
                    print(f"  已完成字段: {state.completed_fields}")
                    print(f"  序列号: {state.sequence_number}")
                
                # 解析块
                result = await parser.parse_chunk(session_id, chunk)
                
                print(f"解析结果: {result}")
                
                # 获取解析后的状态
                if state:
                    print(f"解析后状态:")
                    print(f"  当前数据: {state.current_data}")
                    print(f"  已完成字段: {state.completed_fields}")
                    print(f"  序列号: {state.sequence_number}")
                    print(f"  错误信息: {getattr(state, 'error', None)}")
                
                # 检查是否有新事件
                print(f"当前事件总数: {len(events)}")
                
                # 检查是否有错误
                if state and hasattr(state, 'error') and state.error:
                    print(f"解析出现错误: {state.error}")
                    break
            
            # 最终化会话
            print("\n--- 最终化会话 ---")
            final_result = await parser.finalize_session(session_id)
            print(f"最终化结果: {final_result}")
            
        except Exception as e:
            print(f"解析过程中发生错误: {e}")
            import traceback
            print(f"错误堆栈: {traceback.format_exc()}")
    
    # 运行异步解析
    asyncio.run(parse_chunks())
    
    print("\n=== 解析结果分析 ===")
    print(f"总共生成事件数: {len(events)}")
    
    if events:
        print("\n事件详情:")
        for i, event in enumerate(events):
            print(f"  事件 {i+1}:")
            print(f"    类型: {event.event_type}")
            # 安全地访问事件数据属性
            path = getattr(event.data, 'path', 'N/A') if hasattr(event.data, 'path') else 'N/A'
            value = getattr(event.data, 'value', 'N/A') if hasattr(event.data, 'value') else 'N/A'
            delta_value = getattr(event.data, 'delta_value', 'N/A') if hasattr(event.data, 'delta_value') else 'N/A'
            print(f"    路径: {path}")
            print(f"    值: {value}")
            print(f"    Delta值: {delta_value}")
            # 安全地访问时间戳
            timestamp = getattr(event, 'timestamp', None) or getattr(event.data, 'timestamp', 'N/A')
            print(f"    时间戳: {timestamp}")
    else:
        print("❌ 没有生成任何事件！")
    
    # 检查敏感信息过滤
    print("\n=== 敏感信息过滤检查 ===")
    sensitive_terms = ["secret123", "top_secret", "admin123"]
    
    for event in events:
        event_str = str(event.data)
        for term in sensitive_terms:
            if term in event_str:
                print(f"❌ 发现敏感信息 '{term}' 在事件中: {event.data}")
            else:
                print(f"✅ 敏感信息 '{term}' 已被过滤")
    
    # 检查路径匹配缓存统计
    print("\n=== 路径匹配缓存统计 ===")
    cache_stats = optimizer.get_cache_stats()
    print(f"路径匹配缓存命中率: {cache_stats.get('hit_rate', 0):.2%}")
    print(f"缓存大小: {cache_stats.get('cache_size', 0)}")
    print(f"总查询次数: {cache_stats.get('total_queries', 0)}")
    
    # 检查内存使用情况
    print("\n=== 内存使用情况 ===")
    memory_usage = parser.memory_manager.get_memory_usage()
    print(f"解析器内存统计: {memory_usage}")
    
    # 检查解析器统计
    print("\n=== 解析器统计 ===")
    print(f"解析器统计: {parser.stats}")
    
    print("\n=== 调试完成 ===")

if __name__ == "__main__":
    debug_field_filtering_integration()