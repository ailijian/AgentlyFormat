#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
调试Delta事件生成问题
分析为什么字段过滤器路径匹配正常但没有生成Delta事件
"""

import asyncio
import json
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.agently_format.core.streaming_parser import StreamingParser, FieldFilter
from src.agently_format.types.events import EventType

async def debug_delta_event_generation():
    """调试Delta事件生成问题"""
    print("=== 调试Delta事件生成问题 ===")
    
    # 测试数据
    test_data = {
        "users": [
            {
                "id": 1,
                "name": "Alice",
                "password": "secret123"
            }
        ],
        "data": {
            "count": 42,
            "secret": "top_secret"
        },
        "system": {
            "admin": "admin123"
        }
    }
    
    # 问题分析：测试中使用的include_paths是['users.*', 'data.*']
    # 但实际路径是'users', 'data', 'users[0]', 'users[0].id'等
    # 'users.*'不会匹配'users'本身，只匹配'users.xxx'格式
    
    print("\n=== 问题分析 ===")
    print("测试配置: include_paths=['users.*', 'data.*']")
    print("实际路径: users, data, users[0], users[0].id, data.count等")
    print("问题: 'users.*'不匹配'users'本身，导致路径被过滤掉")
    
    # 测试1: 使用原始配置（有问题的配置）
    print("\n=== 测试1: 原始配置（有问题） ===")
    field_filter1 = FieldFilter(
        enabled=True,
        include_paths=["users.*", "data.*"],
        exclude_paths=["*.password", "*.secret"],
        mode="include"
    )
    
    parser1 = StreamingParser(field_filter=field_filter1)
    session_id1 = parser1.create_session()
    
    # 测试路径匹配
    test_paths = ["users", "data", "users[0]", "users[0].id", "data.count"]
    print("路径匹配测试:")
    for path in test_paths:
        should_include = field_filter1.should_include_path(path)
        print(f"  {path}: {should_include} {'✅' if should_include else '❌'}")
    
    # 解析测试
    json_chunks = [
        '{"users": [',
        '{"id": 1, "name": "Alice"}',
        '], "data": {"count": 42}}'
    ]
    
    events1 = []
    for chunk in json_chunks:
        chunk_events = await parser1.parse_chunk(session_id1, chunk)
        events1.extend(chunk_events)
    
    final_events1 = await parser1.parse_chunk(session_id1, "", is_final=True)
    events1.extend(final_events1)
    
    delta_events1 = [e for e in events1 if e.event_type == EventType.DELTA]
    print(f"\n生成的Delta事件数量: {len(delta_events1)}")
    
    # 测试2: 修正配置
    print("\n=== 测试2: 修正配置 ===")
    field_filter2 = FieldFilter(
        enabled=True,
        include_paths=["users", "users.*", "data", "data.*"],  # 包含根路径
        exclude_paths=["*.password", "*.secret"],
        mode="include"
    )
    
    parser2 = StreamingParser(field_filter=field_filter2)
    session_id2 = parser2.create_session()
    
    # 测试路径匹配
    print("路径匹配测试:")
    for path in test_paths:
        should_include = field_filter2.should_include_path(path)
        print(f"  {path}: {should_include} {'✅' if should_include else '❌'}")
    
    # 解析测试
    events2 = []
    for chunk in json_chunks:
        chunk_events = await parser2.parse_chunk(session_id2, chunk)
        events2.extend(chunk_events)
    
    final_events2 = await parser2.parse_chunk(session_id2, "", is_final=True)
    events2.extend(final_events2)
    
    delta_events2 = [e for e in events2 if e.event_type == EventType.DELTA]
    print(f"\n生成的Delta事件数量: {len(delta_events2)}")
    
    if delta_events2:
        print("\n生成的Delta事件:")
        for event in delta_events2:
            print(f"  路径: {event.data.path}, 值: {event.data.value}")
    
    # 测试3: 更简单的配置
    print("\n=== 测试3: 更简单的配置 ===")
    field_filter3 = FieldFilter(
        enabled=True,
        include_paths=["users", "data"],  # 只包含根路径，让子路径自动包含
        exclude_paths=["password", "secret"],  # 简化排除模式
        mode="include"
    )
    
    parser3 = StreamingParser(field_filter=field_filter3)
    session_id3 = parser3.create_session()
    
    # 测试路径匹配
    print("路径匹配测试:")
    for path in test_paths:
        should_include = field_filter3.should_include_path(path)
        print(f"  {path}: {should_include} {'✅' if should_include else '❌'}")
    
    # 解析测试
    events3 = []
    for chunk in json_chunks:
        chunk_events = await parser3.parse_chunk(session_id3, chunk)
        events3.extend(chunk_events)
    
    final_events3 = await parser3.parse_chunk(session_id3, "", is_final=True)
    events3.extend(final_events3)
    
    delta_events3 = [e for e in events3 if e.event_type == EventType.DELTA]
    print(f"\n生成的Delta事件数量: {len(delta_events3)}")
    
    if delta_events3:
        print("\n生成的Delta事件:")
        for event in delta_events3:
            print(f"  路径: {event.data.path}, 值: {event.data.value}")
    
    print("\n=== 结论 ===")
    print("问题根源: include_paths=['users.*', 'data.*']不匹配根路径'users'和'data'")
    print("解决方案: 修改include_paths为['users', 'users.*', 'data', 'data.*']")
    print("或者修改为['users', 'data']并调整路径匹配逻辑")

if __name__ == "__main__":
    asyncio.run(debug_delta_event_generation())