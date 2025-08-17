#!/usr/bin/env python3
"""调试字段过滤优化测试失败问题"""

import asyncio
import json
from src.agently_format.core.streaming_parser import StreamingParser, FieldFilter
from src.agently_format.types.events import EventType

async def debug_field_filtering_test():
    """调试字段过滤优化测试"""
    print("=== 调试字段过滤优化测试 ===")
    
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
    
    print(f"解析器创建成功")
    print(f"字段过滤器已启用: {integrated_parser.field_filter.enabled}")
    print(f"包含路径: {integrated_parser.field_filter.include_paths}")
    print(f"排除路径: {integrated_parser.field_filter.exclude_paths}")
    
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
    
    print(f"\n测试数据: {json.dumps(test_data, indent=2)}")
    
    session_id = integrated_parser.create_session("filter_test")
    print(f"\n会话创建成功: {session_id}")
    
    events = []
    
    async def event_callback(event):
        events.append(event)
        print(f"事件回调: {event.event_type} - {event.data}")
    
    integrated_parser.add_event_callback(EventType.DELTA, event_callback)
    print("事件回调已注册")
    
    # 解析数据
    print("\n开始解析数据...")
    try:
        result = await integrated_parser.parse_chunk(
            session_id,
            json.dumps(test_data),
            is_final=True
        )
        print(f"解析完成，结果事件数量: {len(result)}")
        
        for i, event in enumerate(result):
            print(f"结果事件 {i}: {event.event_type} - {event.data}")
            
    except Exception as e:
        print(f"解析失败: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # 验证字段过滤效果
    print("\n=== 验证字段过滤效果 ===")
    delta_events = [e for e in events if e.event_type == EventType.DELTA]
    print(f"Delta事件数量: {len(delta_events)}")
    
    # 检查是否包含了允许的路径
    allowed_paths = []
    for event in delta_events:
        if hasattr(event.data, 'path'):
            allowed_paths.append(event.data.path)
            print(f"路径: {event.data.path}")
        else:
            print(f"事件数据没有path属性: {event.data}")
    
    print(f"\n允许的路径: {allowed_paths}")
    
    # 验证包含的路径
    users_paths = [path for path in allowed_paths if 'users' in path]
    data_paths = [path for path in allowed_paths if 'data' in path]
    
    print(f"包含users的路径: {users_paths}")
    print(f"包含data的路径: {data_paths}")
    
    print(f"\n验证包含路径:")
    print(f"  any('users' in path for path in allowed_paths): {any('users' in path for path in allowed_paths)}")
    print(f"  any('data' in path for path in allowed_paths): {any('data' in path for path in allowed_paths)}")
    
    # 验证排除的路径（密码和秘密信息应该被过滤）
    print(f"\n=== 验证排除路径 ===")
    filtered_content = ''.join([str(event.data) for event in delta_events])
    print(f"过滤后的内容: {filtered_content}")
    
    print(f"\n检查敏感信息:")
    print(f"  'secret123' in filtered_content: {'secret123' in filtered_content}")
    print(f"  'top_secret' in filtered_content: {'top_secret' in filtered_content}")
    print(f"  'admin123' in filtered_content: {'admin123' in filtered_content}")
    
    # 验证路径匹配缓存被使用
    print(f"\n=== 验证缓存使用 ===")
    if integrated_parser.performance_optimizer:
        cache_stats = integrated_parser.performance_optimizer.get_cache_stats()
        print(f"缓存统计: {cache_stats}")
        print(f"路径匹配缓存总数: {cache_stats['path_matching_cache']['total']}")
    else:
        print("性能优化器未启用")
    
    print("\n=== 调试完成 ===")

if __name__ == "__main__":
    asyncio.run(debug_field_filtering_test())