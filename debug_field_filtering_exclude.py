#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
调试字段过滤器的排除功能
测试同时使用include_paths和exclude_paths
"""

import asyncio
import json
import sys
sys.path.insert(0, 'src')

from agently_format.core.streaming_parser import StreamingParser, FieldFilter
from agently_format.types.events import EventType

async def debug_exclude_filtering():
    """调试排除字段过滤功能"""
    print("=== 字段排除过滤调试 ===\n")
    
    # 创建字段过滤器 - 包含users和data，但排除敏感字段
    field_filter = FieldFilter(
        enabled=True,
        include_paths=["users", "data"],
        exclude_paths=["password", "secret", "api_key"],  # 排除敏感字段
        mode="include",  # 主要模式是包含
        exact_match=False
    )
    
    # 创建流式解析器
    parser = StreamingParser(
        field_filter=field_filter
    )
    
    # 测试数据
    test_data = {
        "users": [
            {
                "id": 1,
                "name": "Alice",
                "email": "alice@example.com",
                "password": "secret123",  # 应该被排除
                "profile": {
                    "age": 25,
                    "secret": "top_secret"  # 应该被排除
                }
            }
        ],
        "data": {
            "count": 1,
            "api_key": "should_be_excluded",  # 应该被排除
            "public_info": "visible"
        },
        "system": {  # 整个system应该被排除
            "version": "1.0",
            "password": "admin123"
        }
    }
    
    print(f"测试数据: {json.dumps(test_data, indent=2)}\n")
    
    session_id = parser.create_session("exclude_test")
    events = []
    
    async def event_callback(event):
        events.append(event)
        print(f"事件: {event.event_type}, 路径: {getattr(event, 'path', 'N/A')}, 数据: {getattr(event, 'data', 'N/A')}")
    
    parser.add_event_callback(EventType.DELTA, event_callback)
    
    # 检查字段过滤器配置
    print(f"=== 字段过滤器配置 ===")
    print(f"启用状态: {field_filter.enabled}")
    print(f"模式: {field_filter.mode}")
    print(f"包含路径: {field_filter.include_paths}")
    print(f"排除路径: {field_filter.exclude_paths}\n")
    
    # 测试路径匹配逻辑
    print(f"=== 路径匹配测试 ===")
    test_paths = [
        "users[0].id",
        "users[0].name", 
        "users[0].password",  # 应该被排除
        "users[0].profile.age",
        "users[0].profile.secret",  # 应该被排除
        "data.count",
        "data.api_key",  # 应该被排除
        "data.public_info",
        "system.version"  # 应该被排除（不在include_paths中）
    ]
    
    for path in test_paths:
        should_include = field_filter.should_include_path(path)
        print(f"路径 '{path}': {'包含' if should_include else '排除'}")
    
    print(f"\n=== 开始解析数据 ===")
    result = await parser.parse_chunk(
        session_id,
        json.dumps(test_data),
        is_final=True
    )
    
    print(f"\n=== 解析结果 ===")
    print(f"返回事件数量: {len(result)}")
    
    # 分析Delta事件
    delta_events = [e for e in events if e.event_type == EventType.DELTA]
    print(f"\n=== Delta事件分析 ===")
    print(f"Delta事件数量: {len(delta_events)}")
    
    allowed_paths = []
    filtered_content = ""
    for event in delta_events:
        if hasattr(event, 'path'):
            allowed_paths.append(event.path)
            filtered_content += str(event.data)
    
    print(f"\n=== 过滤结果验证 ===")
    print(f"包含的路径: {allowed_paths}")
    print(f"过滤后内容: {filtered_content}")
    
    # 验证敏感信息是否被正确排除
    sensitive_terms = ["secret123", "top_secret", "should_be_excluded", "admin123"]
    print(f"\n=== 敏感信息检查 ===")
    for term in sensitive_terms:
        is_present = term in filtered_content
        print(f"'{term}': {'❌ 泄露' if is_present else '✅ 已过滤'}")
    
    # 验证应该包含的信息
    expected_terms = ["Alice", "alice@example.com", "visible"]
    print(f"\n=== 预期信息检查 ===")
    for term in expected_terms:
        is_present = term in filtered_content
        print(f"'{term}': {'✅ 包含' if is_present else '❌ 缺失'}")

if __name__ == "__main__":
    asyncio.run(debug_exclude_filtering())