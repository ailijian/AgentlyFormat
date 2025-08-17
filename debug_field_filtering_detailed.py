#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
详细调试字段过滤集成测试失败问题
分析Delta事件生成和路径匹配的具体情况
"""

import asyncio
import json
import sys
sys.path.insert(0, 'src')

from agently_format.core.streaming_parser import StreamingParser, FieldFilter
from agently_format.core.performance_optimizer import PerformanceOptimizer
from agently_format.core.memory_manager import MemoryManager
from agently_format.types.events import EventType

async def debug_field_filtering():
    """调试字段过滤集成测试"""
    print("=== 字段过滤集成测试详细调试 ===")
    
    # 创建字段过滤器
    field_filter = FieldFilter(
        enabled=True,
        include_paths=["users", "data"],
        mode="include",
        exact_match=False
    )
    
    # 创建流式解析器（性能优化器和内存管理器会自动创建）
    parser = StreamingParser(
        field_filter=field_filter
    )
    
    # 创建包含敏感数据的测试数据
    test_data = {
        "users": [
            {
                "id": 1,
                "name": "Alice",
                "email": "alice@example.com",
                "password": "secret123",  # 应该被过滤
                "profile": {
                    "age": 25,
                    "secret": "top_secret"  # 应该被过滤
                }
            }
        ],
        "data": {
            "count": 1,
            "api_key": "should_be_included"
        },
        "system": {
            "version": "1.0",
            "password": "admin123"  # 应该被过滤
        }
    }
    
    print(f"测试数据: {json.dumps(test_data, indent=2)}")
    
    session_id = parser.create_session("filter_test")
    events = []
    
    async def event_callback(event):
        events.append(event)
        print(f"收到事件: {event.event_type}, 路径: {getattr(event, 'path', 'N/A')}, 数据: {getattr(event, 'data', 'N/A')}")
    
    parser.add_event_callback(EventType.DELTA, event_callback)
    
    # 检查字段过滤器配置
    print(f"\n=== 字段过滤器配置 ===")
    if hasattr(parser, 'field_filter') and parser.field_filter:
        print(f"字段过滤器已启用: {parser.field_filter.enabled}")
        print(f"过滤模式: {parser.field_filter.mode}")
        print(f"包含路径: {parser.field_filter.include_paths}")
        print(f"排除路径: {parser.field_filter.exclude_paths}")
    else:
        print("字段过滤器未配置")
    
    # 解析数据
    print(f"\n=== 开始解析数据 ===")
    result = await parser.parse_chunk(
        session_id,
        json.dumps(test_data),
        is_final=True
    )
    
    print(f"\n=== 解析结果 ===")
    print(f"返回事件数量: {len(result)}")
    for i, event in enumerate(result):
        print(f"事件 {i}: {event.event_type}, 路径: {getattr(event, 'path', 'N/A')}, 数据: {getattr(event, 'data', 'N/A')}")
    
    print(f"\n=== 回调事件 ===")
    print(f"回调事件数量: {len(events)}")
    for i, event in enumerate(events):
        print(f"回调事件 {i}: {event.event_type}, 路径: {getattr(event, 'path', 'N/A')}, 数据: {getattr(event, 'data', 'N/A')}")
    
    # 验证字段过滤效果
    delta_events = [e for e in events if e.event_type == EventType.DELTA]
    print(f"\n=== Delta事件分析 ===")
    print(f"Delta事件数量: {len(delta_events)}")
    
    # 检查是否包含了允许的路径
    allowed_paths = []
    for event in delta_events:
        if hasattr(event, 'path'):
            allowed_paths.append(event.path)
            print(f"Delta事件路径: {event.path}")
    
    print(f"\n=== 路径匹配验证 ===")
    print(f"所有Delta事件路径: {allowed_paths}")
    
    # 验证包含的路径
    users_paths = [path for path in allowed_paths if 'users' in path]
    data_paths = [path for path in allowed_paths if 'data' in path]
    
    print(f"包含'users'的路径: {users_paths}")
    print(f"包含'data'的路径: {data_paths}")
    
    print(f"\n=== 断言验证 ===")
    print(f"any('users' in path for path in allowed_paths): {any('users' in path for path in allowed_paths)}")
    print(f"any('data' in path for path in allowed_paths): {any('data' in path for path in allowed_paths)}")
    
    # 验证排除的路径（密码和秘密信息应该被过滤）
    filtered_content = ''.join([str(event.data) for event in delta_events])
    print(f"\n=== 敏感信息过滤验证 ===")
    print(f"过滤后内容: {filtered_content}")
    print(f"包含'secret123': {'secret123' in filtered_content}")
    print(f"包含'top_secret': {'top_secret' in filtered_content}")
    print(f"包含'admin123': {'admin123' in filtered_content}")
    
    # 验证路径匹配缓存被使用
    try:
        cache_stats = parser.performance_optimizer.get_cache_stats()
        print(f"\n=== 缓存统计 ===")
        print(f"路径匹配缓存: {cache_stats['path_matching_cache']}")
    except Exception as e:
        print(f"\n=== 缓存统计错误 ===")
        print(f"获取缓存统计失败: {e}")
    
    # 检查解析状态
    state = parser.get_parsing_state(session_id)
    if state:
        print(f"\n=== 解析状态 ===")
        print(f"解析完成: {state.is_complete}")
        print(f"当前数据: {state.current_data}")
        print(f"错误数量: {len(state.errors)}")
    
if __name__ == "__main__":
    asyncio.run(debug_field_filtering())