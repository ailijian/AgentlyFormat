#!/usr/bin/env python3
"""调试敏感信息过滤问题

分析为什么敏感信息(secret123, top_secret, admin123)仍然出现在输出中，
尽管字段过滤器配置了exclude_paths=['*.password', '*.secret']。
"""

import json
import asyncio
from src.agently_format.core.streaming_parser import StreamingParser, FieldFilter
from src.agently_format.types.events import EventType


async def debug_sensitive_filtering():
    """调试敏感信息过滤功能"""
    print("=== 敏感信息过滤调试 ===")
    
    # 创建集成解析器
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
            include_paths=['users.*', 'data.*'],
            exclude_paths=['*.password', '*.secret']
        )
    )
    
    # 测试数据 - 包含敏感信息
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
    
    print(f"原始数据: {json.dumps(test_data, indent=2)}")
    print()
    
    # 测试字段过滤器配置
    field_filter = integrated_parser.field_filter
    print(f"字段过滤器配置:")
    print(f"  enabled: {field_filter.enabled}")
    print(f"  include_paths: {field_filter.include_paths}")
    print(f"  exclude_paths: {field_filter.exclude_paths}")
    print()
    
    # 测试路径匹配
    test_paths = [
        'users.0.password',
        'users.0.profile.secret',
        'system.password',
        'users.0.name',
        'users.0.email',
        'data.count',
        'data.api_key'
    ]
    
    print("路径匹配测试:")
    for path in test_paths:
        should_include = field_filter.should_include_path(path)
        print(f"  {path}: {'包含' if should_include else '排除'}")
    print()
    
    # 创建会话并解析
    session_id = integrated_parser.create_session("sensitive_filter_test")
    events = []
    
    async def event_callback(event):
        events.append(event)
        print(f"事件: {event.event_type}, 数据: {event.data}")
    
    integrated_parser.add_event_callback(EventType.DELTA, event_callback)
    integrated_parser.add_event_callback(EventType.ERROR, event_callback)
    
    # 解析数据
    json_str = json.dumps(test_data)
    print(f"开始解析数据...")
    print(f"JSON字符串长度: {len(json_str)}")
    
    # 添加调试信息
    print(f"解析前会话状态: {integrated_parser.get_parsing_state(session_id)}")
    
    result = await integrated_parser.parse_chunk(
        session_id,
        json_str,
        is_final=True
    )
    
    print(f"解析后会话状态: {integrated_parser.get_parsing_state(session_id)}")
    
    # 检查解析状态
    state = integrated_parser.get_parsing_state(session_id)
    if state:
        print(f"当前数据: {state.current_data}")
        print(f"是否完成: {state.is_complete}")
        print(f"错误数量: {len(state.errors)}")
        if state.errors:
            print(f"错误详情: {state.errors}")
    else:
        print("无法获取解析状态")
    
    print(f"\n解析结果: {len(result)} 个事件")
    
    # 分析Delta事件
    delta_events = [e for e in events if e.event_type == EventType.DELTA]
    error_events = [e for e in events if e.event_type == EventType.ERROR]
    
    print(f"Delta事件数量: {len(delta_events)}")
    print(f"Error事件数量: {len(error_events)}")
    
    if error_events:
        print("\n错误事件:")
        for event in error_events:
            print(f"  {event.data}")
    
    # 检查敏感信息是否被过滤
    print("\n敏感信息过滤检查:")
    all_content = ''
    for event in delta_events:
        if hasattr(event.data, 'value'):
            all_content += str(event.data.value)
        else:
            all_content += str(event.data)
    
    sensitive_terms = ['secret123', 'top_secret', 'admin123']
    for term in sensitive_terms:
        found = term in all_content
        print(f"  {term}: {'❌ 未过滤' if found else '✅ 已过滤'}")
    
    # 检查包含的路径
    print("\n包含的路径:")
    for event in delta_events:
        if hasattr(event.data, 'path'):
            print(f"  {event.data.path}")
    
    # 获取缓存统计
    cache_stats = integrated_parser.performance_optimizer.get_cache_stats()
    print(f"\n缓存统计:")
    print(f"  路径匹配缓存: {cache_stats['path_matching_cache']}")
    
    # 清理
    integrated_parser.cleanup_session(session_id)
    print("\n调试完成")


if __name__ == "__main__":
    asyncio.run(debug_sensitive_filtering())