#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
调试脚本：测试修复后的字段过滤功能
验证exclude_paths配置是否能正确过滤敏感信息
"""

import json
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

import asyncio
import json
from agently_format.core.streaming_parser import StreamingParser
from agently_format.core.performance_optimizer import PerformanceOptimizer
from agently_format.core.memory_manager import MemoryManager
from agently_format.types.events import EventType

def test_field_filter_fix():
    """测试修复后的字段过滤功能"""
    print("=== 测试修复后的字段过滤功能 ===")
    
    # 创建字段过滤器
    from agently_format.core.streaming_parser import FieldFilter
    
    field_filter = FieldFilter(
        enabled=True,
        include_paths=['users', 'users.*', 'data', 'data.*'],
        exclude_paths=['secret123', 'top_secret', 'admin123', 'password', 'token'],
        mode='include'
    )
    
    # 创建解析器，配置字段过滤
    parser = StreamingParser(
        field_filter=field_filter
    )
    
    # 创建会话
    session_id = "test_session"
    parser.create_session(session_id)
    
    # 测试数据 - 包含敏感信息
    test_data = {
        "users": [
            {
                "id": 1,
                "name": "Alice",
                "secret123": "sensitive_value",  # 应该被过滤
                "email": "alice@example.com"
            },
            {
                "id": 2,
                "name": "Bob",
                "top_secret": "classified_info",  # 应该被过滤
                "role": "admin"
            }
        ],
        "data": {
            "public_info": "visible",
            "admin123": "admin_password",  # 应该被过滤
            "description": "test data"
        },
        "metadata": {
            "version": "1.0",
            "password": "hidden_password"  # 应该被过滤
        }
    }
    
    # 收集事件
    events = []
    
    def event_handler(event):
        events.append(event)
        print(f"事件: {event.event_type}, 路径: {event.data.path}, 值: {event.data.value}")
    
    parser.add_event_callback(EventType.DELTA, event_handler)
    
    # 解析数据
    json_str = json.dumps(test_data)
    print(f"\n原始数据: {json_str}")
    print("\n开始解析...")
    
    try:
        async def parse_data():
            await parser.parse_chunk(session_id, json_str, is_final=True)
            await parser.finalize_session(session_id)
        
        # 运行异步解析
        asyncio.run(parse_data())
        
        print(f"\n解析完成，共生成 {len(events)} 个事件")
        
        # 检查敏感信息是否被正确过滤
        sensitive_patterns = ['secret123', 'top_secret', 'admin123', 'password']
        found_sensitive = []
        
        for event in events:
            for pattern in sensitive_patterns:
                if pattern in event.data.path or (event.data.value and pattern in str(event.data.value)):
                    found_sensitive.append({
                        'pattern': pattern,
                        'path': event.data.path,
                        'value': event.data.value,
                        'event_type': event.event_type
                    })
        
        print(f"\n=== 敏感信息过滤检查结果 ===")
        if found_sensitive:
            print(f"❌ 发现 {len(found_sensitive)} 个敏感信息泄露:")
            for item in found_sensitive:
                print(f"  - 模式: {item['pattern']}, 路径: {item['path']}, 值: {item['value']}")
        else:
            print("✅ 所有敏感信息都被正确过滤")
        
        # 检查应该包含的路径是否存在
        expected_paths = ['users', 'users[0].id', 'users[0].name', 'users[0].email', 
                         'users[1].id', 'users[1].name', 'users[1].role',
                         'data.public_info', 'data.description']
        
        found_paths = [event.data.path for event in events if hasattr(event, 'data') and hasattr(event.data, 'path')]
        missing_paths = []
        
        for expected in expected_paths:
            if not any(expected in path for path in found_paths):
                missing_paths.append(expected)
        
        print(f"\n=== 预期路径检查结果 ===")
        if missing_paths:
            print(f"⚠️  缺失 {len(missing_paths)} 个预期路径:")
            for path in missing_paths:
                print(f"  - {path}")
        else:
            print("✅ 所有预期路径都存在")
        
        print(f"\n实际生成的路径:")
        for path in sorted(set(found_paths)):
            print(f"  - {path}")
        
        return len(found_sensitive) == 0 and len(missing_paths) == 0
        
    except Exception as e:
        print(f"❌ 解析过程中发生错误: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_field_filter_fix()
    print(f"\n=== 测试结果 ===")
    if success:
        print("✅ 字段过滤功能修复成功")
    else:
        print("❌ 字段过滤功能仍有问题")
    
    sys.exit(0 if success else 1)