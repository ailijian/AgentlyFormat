#!/usr/bin/env python3
"""调试字段过滤集成测试的详细脚本

分析test_field_filtering_with_optimization测试失败的原因
"""

import asyncio
import json
from src.agently_format.core.streaming_parser import StreamingParser, FieldFilter
from src.agently_format.types.events import EventType


async def debug_integration_test():
    """调试集成测试中的字段过滤问题"""
    print("=== 调试字段过滤集成测试 ===")
    
    # 创建与测试相同的解析器配置
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
    print(f"字段过滤器状态: enabled={integrated_parser.field_filter.enabled}")
    print(f"包含路径: {integrated_parser.field_filter.include_paths}")
    print(f"排除路径: {integrated_parser.field_filter.exclude_paths}")
    print(f"过滤模式: {integrated_parser.field_filter.mode}")
    
    # 创建与测试相同的测试数据
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
    
    # 创建会话
    session_id = integrated_parser.create_session("filter_test")
    print(f"\n会话创建: {session_id}")
    
    # 收集事件
    events = []
    
    async def event_callback(event):
        events.append(event)
        print(f"事件: {event.event_type} - {event.data}")
    
    integrated_parser.add_event_callback(EventType.DELTA, event_callback)
    integrated_parser.add_event_callback(EventType.START, event_callback)
    integrated_parser.add_event_callback(EventType.FINISH, event_callback)
    integrated_parser.add_event_callback(EventType.ERROR, event_callback)
    
    print(f"\n开始解析...")
    
    # 解析数据
    try:
        result = await integrated_parser.parse_chunk(
            session_id,
            json.dumps(test_data),
            is_final=True
        )
    except Exception as e:
        print(f"❌ 解析过程中发生异常: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        result = []
    
    print(f"\n解析完成")
    print(f"返回结果数量: {len(result)}")
    print(f"收集到的事件数量: {len(events)}")
    
    # 分析事件
    delta_events = [e for e in events if e.event_type == EventType.DELTA]
    print(f"\nDelta事件数量: {len(delta_events)}")
    
    if delta_events:
        print("\nDelta事件详情:")
        for i, event in enumerate(delta_events):
            print(f"  {i+1}. {event.data}")
            if hasattr(event.data, 'path'):
                print(f"     路径: {event.data.path}")
    else:
        print("\n❌ 没有生成Delta事件！")
    
    # 分析结果事件
    print(f"\n结果事件分析:")
    for event in result:
        print(f"  类型: {event.event_type}, 数据: {event.data}")
    
    # 检查解析状态
    state = integrated_parser.get_parsing_state(session_id)
    if state:
        print(f"\n解析状态:")
        print(f"  完成状态: {state.is_complete}")
        print(f"  总块数: {state.total_chunks}")
        print(f"  处理块数: {state.processed_chunks}")
        print(f"  错误数: {len(state.errors)}")
        print(f"  当前数据: {state.current_data}")
    
    # 测试字段过滤逻辑
    print(f"\n字段过滤测试:")
    test_paths = [
        "users",
        "users[0]",
        "users[0].name",
        "users[0].password",
        "users[0].profile.secret",
        "data",
        "data.count",
        "system",
        "system.password"
    ]
    
    for path in test_paths:
        should_include = integrated_parser.field_filter.should_include_path(path)
        should_process = integrated_parser._should_process_path_branch(path)
        print(f"  路径 '{path}': 包含={should_include}, 处理分支={should_process}")
    
    # 详细测试通配符匹配
    print(f"\n通配符匹配详细测试:")
    patterns = ['users.*', 'data.*']
    for pattern in patterns:
        print(f"  模式 '{pattern}':")
        for path in test_paths:
            matches = integrated_parser.field_filter._wildcard_match(path, pattern)
            print(f"    路径 '{path}' -> {matches}")
    
    # 检查性能优化器缓存
    cache_stats = integrated_parser.performance_optimizer.get_cache_stats()
    print(f"\n缓存统计:")
    print(f"  路径匹配缓存: {cache_stats['path_matching_cache']}")
    print(f"  字符串增量缓存: {cache_stats['string_delta_cache']}")
    
    print(f"\n=== 调试完成 ===")


if __name__ == "__main__":
    asyncio.run(debug_integration_test())