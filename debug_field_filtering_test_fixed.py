#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
调试字段过滤优化测试失败问题
重点分析字段过滤器的路径匹配逻辑
"""

import asyncio
import json
import sys
import os

# 添加src目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from agently_format.core.streaming_parser import (
    StreamingParser, FieldFilter, EventType
)
from agently_format.core.performance_optimizer import PerformanceOptimizer
from agently_format.core.memory_manager import MemoryManager

async def debug_field_filtering():
    """调试字段过滤功能"""
    print("=== 调试字段过滤功能 ===")
    
    # 创建性能优化器和内存管理器
    performance_optimizer = PerformanceOptimizer()
    memory_manager = MemoryManager()
    
    # 创建字段过滤器 - 模拟测试中的配置
    field_filter = FieldFilter(
        enabled=True,
        include_paths=["users.*", "data.*"],  # 包含users和data下的所有字段
        exclude_paths=["*.password", "*.secret"],  # 排除所有password和secret字段
        mode="include",
        exact_match=False
    )
    
    print(f"字段过滤器配置:")
    print(f"  enabled: {field_filter.enabled}")
    print(f"  include_paths: {field_filter.include_paths}")
    print(f"  exclude_paths: {field_filter.exclude_paths}")
    print(f"  mode: {field_filter.mode}")
    print()
    
    # 测试路径匹配逻辑
    test_paths = [
        "users",
        "users[0]", 
        "users[0].id",
        "users[0].name",
        "users[0].password",  # 应该被排除
        "data",
        "data.count",
        "data.secret",  # 应该被排除
        "system",  # 应该被排除（不在include_paths中）
        "system.version"  # 应该被排除
    ]
    
    print("=== 测试路径匹配逻辑 ===")
    for path in test_paths:
        should_include = field_filter.should_include_path(path)
        status = "✅ 包含" if should_include else "❌ 排除"
        print(f"路径 '{path}': {status}")
        
        # 详细分析关键路径
        if path in ["users", "users[0].id", "users[0].password", "data.count", "system"]:
            print(f"  详细分析:")
            
            # 检查include_paths匹配
            if field_filter.include_paths:
                include_match = field_filter._path_matches(path, field_filter.include_paths)
                print(f"    include_paths匹配: {include_match}")
            
            # 检查exclude_paths匹配
            if field_filter.exclude_paths:
                exclude_match = field_filter._path_matches(path, field_filter.exclude_paths)
                print(f"    exclude_paths匹配: {exclude_match}")
            print()
    
    # 创建解析器
    parser = StreamingParser(
        field_filter=field_filter
    )
    
    print("=== 测试解析过程 ===")
    
    # 测试数据 - 包含敏感信息
    test_data = {
        "users": [
            {
                "id": 1,
                "name": "Alice",
                "password": "secret123"  # 应该被过滤
            }
        ],
        "data": {
            "count": 42,
            "secret": "top_secret"  # 应该被过滤
        },
        "system": {  # 整个system应该被过滤
            "version": "1.0"
        }
    }
    
    # 收集事件
    events = []
    
    async def event_callback(event):
        events.append(event)
        event_data = getattr(event, 'data', None)
        if event_data:
            path = getattr(event_data, 'path', 'N/A')
            value = getattr(event_data, 'value', 'N/A')
            print(f"事件: {event.event_type}, 路径: {path}, 值: {value}")
        else:
            print(f"事件: {event.event_type}, 数据: {event}")
    
    # 注册事件回调
    parser.add_event_callback(EventType.DELTA, event_callback)
    parser.add_event_callback(EventType.DONE, event_callback)
    parser.add_event_callback(EventType.ERROR, event_callback)
    
    # 开始解析
    session_id = parser.create_session()
    
    print(f"开始解析数据: {json.dumps(test_data, ensure_ascii=False)}")
    print()
    
    # 解析数据
    try:
        await parser.parse_chunk(session_id, json.dumps(test_data), is_final=True)
        print("解析完成")
    except Exception as e:
        print(f"解析错误: {e}")
        import traceback
        traceback.print_exc()
    
    print()
    print(f"总事件数量: {len(events)}")
    
    # 分析事件类型
    delta_events = [e for e in events if e.event_type == EventType.DELTA]
    done_events = [e for e in events if e.event_type == EventType.DONE]
    error_events = [e for e in events if e.event_type == EventType.ERROR]
    
    print(f"Delta事件数量: {len(delta_events)}")
    print(f"Done事件数量: {len(done_events)}")
    print(f"Error事件数量: {len(error_events)}")
    
    if error_events:
        print("\n=== 错误事件详情 ===")
        for event in error_events:
            print(f"错误类型: {getattr(event.data, 'error_type', 'N/A')}")
            print(f"错误消息: {getattr(event.data, 'error_message', 'N/A')}")
    
    # 检查敏感信息是否被过滤
    print("\n=== 敏感信息过滤检查 ===")
    all_event_content = str(events)
    sensitive_terms = ["secret123", "top_secret", "password", "secret"]
    
    for term in sensitive_terms:
        if term in all_event_content:
            print(f"⚠️  敏感信息 '{term}' 仍然出现在事件中")
        else:
            print(f"✅ 敏感信息 '{term}' 已被正确过滤")
    
    # 打印解析器统计
    print("\n=== 解析器统计 ===")
    print(f"解析器统计: {parser.stats}")

if __name__ == "__main__":
    asyncio.run(debug_field_filtering())