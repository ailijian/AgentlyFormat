#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
调试字段过滤优化测试失败问题
"""

import asyncio
import json
import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.agently_format.core.streaming_parser import StreamingParser, FieldFilter
from src.agently_format.types.events import EventType

async def debug_field_filtering_optimization():
    """调试字段过滤优化测试"""
    print("=== 调试字段过滤优化测试 ===")
    
    # 创建与测试相同的解析器配置
    parser = StreamingParser(
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
    
    print(f"字段过滤器配置:")
    print(f"  enabled: {parser.field_filter.enabled}")
    print(f"  include_paths: {parser.field_filter.include_paths}")
    print(f"  exclude_paths: {parser.field_filter.exclude_paths}")
    
    # 测试数据
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
    
    print(f"\n测试数据: {json.dumps(test_data, indent=2)}")
    
    # 测试路径匹配逻辑
    print("\n=== 路径匹配测试 ===")
    test_paths = [
        'users',
        'users[0]',
        'users[0].id',
        'users[0].name',
        'users[0].password',
        'users[0].profile',
        'users[0].profile.age',
        'users[0].profile.secret',
        'data',
        'data.count',
        'data.api_key',
        'system',
        'system.version',
        'system.password'
    ]
    
    for path in test_paths:
        should_include = parser.field_filter.should_include_path(path)
        print(f"  {path}: {'包含' if should_include else '排除'}")
    
    # 创建会话并解析数据
    session_id = parser.create_session("filter_test")
    events = []
    
    async def event_callback(event):
        events.append(event)
        print(f"事件: {event.event_type}, 数据: {getattr(event.data, 'path', 'N/A')} = {getattr(event.data, 'value', str(event.data))}")
    
    parser.add_event_callback(EventType.DELTA, event_callback)
    
    print(f"\n=== 解析数据 ===")
    result = await parser.parse_chunk(
        json.dumps(test_data),
        session_id,
        is_final=True
    )
    
    print(f"\n解析结果: {len(result)} 个事件")
    
    # 分析Delta事件
    delta_events = [e for e in events if e.event_type == EventType.DELTA]
    print(f"Delta事件数量: {len(delta_events)}")
    
    # 检查允许的路径
    allowed_paths = []
    for event in delta_events:
        if hasattr(event.data, 'path'):
            allowed_paths.append(event.data.path)
    
    print(f"\n允许的路径: {allowed_paths}")
    
    # 验证包含的路径
    users_included = any('users' in path for path in allowed_paths)
    data_included = any('data' in path for path in allowed_paths)
    
    print(f"\n=== 验证结果 ===")
    print(f"users路径包含: {users_included}")
    print(f"data路径包含: {data_included}")
    
    # 验证排除的路径
    filtered_content = ''.join([str(event.data) for event in delta_events])
    secret123_filtered = 'secret123' not in filtered_content
    top_secret_filtered = 'top_secret' not in filtered_content
    admin123_filtered = 'admin123' not in filtered_content
    
    print(f"secret123已过滤: {secret123_filtered}")
    print(f"top_secret已过滤: {top_secret_filtered}")
    print(f"admin123已过滤: {admin123_filtered}")
    
    # 检查性能优化器缓存
    try:
        cache_stats = parser.performance_optimizer.get_cache_stats()
        print(f"\n=== 缓存统计 ===")
        print(f"路径匹配缓存: {cache_stats.get('path_matching_cache', {})}")
        cache_used = cache_stats.get('path_matching_cache', {}).get('total', 0) > 0
        print(f"缓存已使用: {cache_used}")
    except Exception as e:
        print(f"\n缓存统计获取失败: {e}")
        cache_used = False
    
    # 分析失败原因
    print(f"\n=== 失败分析 ===")
    
    if not users_included:
        print("❌ users路径未包含")
    if not data_included:
        print("❌ data路径未包含")
    if not secret123_filtered:
        print("❌ secret123未被过滤")
    if not top_secret_filtered:
        print("❌ top_secret未被过滤")
    if not admin123_filtered:
        print("❌ admin123未被过滤")
    if not cache_used:
        print("❌ 路径匹配缓存未使用")
    
    # 检查具体的断言失败点
    print(f"\n=== 断言检查 ===")
    print(f"assert any('users' in path for path in allowed_paths): {users_included}")
    print(f"assert any('data' in path for path in allowed_paths): {data_included}")
    print(f"assert 'secret123' not in filtered_content: {secret123_filtered}")
    print(f"assert 'top_secret' not in filtered_content: {top_secret_filtered}")
    print(f"assert 'admin123' not in filtered_content: {admin123_filtered}")
    print(f"assert cache_stats['path_matching_cache']['total'] > 0: {cache_used}")
    
    # 清理
    parser.cleanup_session(session_id)
    
    return {
        'users_included': users_included,
        'data_included': data_included,
        'secret123_filtered': secret123_filtered,
        'top_secret_filtered': top_secret_filtered,
        'admin123_filtered': admin123_filtered,
        'cache_used': cache_used,
        'delta_events_count': len(delta_events),
        'allowed_paths': allowed_paths
    }

if __name__ == "__main__":
    result = asyncio.run(debug_field_filtering_optimization())
    print(f"\n=== 最终结果 ===")
    print(json.dumps(result, indent=2, ensure_ascii=False))