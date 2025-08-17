#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
字段过滤调试脚本
分析为什么没有生成delta事件
"""

import asyncio
import json
from src.agently_format.core.streaming_parser import StreamingParser, FieldFilter
from src.agently_format.core.performance_optimizer import PerformanceOptimizer
from src.agently_format.core.memory_manager import MemoryManager
from src.agently_format.types.events import EventType

async def debug_field_filtering():
    print("=== 字段过滤调试 ===")
    
    # 创建组件
    performance_optimizer = PerformanceOptimizer()
    field_filter = FieldFilter(
        enabled=True,
        include_paths=['users', 'data'],
        exclude_paths=['password', 'secret', 'admin'],
        mode="include",
        performance_optimizer=performance_optimizer
    )
    
    # 创建解析器
    parser = StreamingParser(
        field_filter=field_filter
    )
    
    print("解析器创建成功")
    
    # 创建会话
    session_id = parser.create_session("debug_field_filtering")
    print(f"会话创建成功: {session_id}")
    
    # 设置字段过滤
    include_patterns = ['users', 'data']
    exclude_patterns = ['password', 'secret', 'admin']
    print(f"字段过滤设置: include={field_filter.include_paths}, exclude={field_filter.exclude_paths}")
    
    # 测试数据
    test_data = {
        "users": [
            {
                "id": 1,
                "name": "Alice",
                "password": "secret123"
            },
            {
                "id": 2,
                "name": "Bob",
                "admin": "admin123"
            }
        ],
        "data": {
            "count": 2,
            "secret": "top_secret"
        },
        "metadata": {
            "version": "1.0"
        }
    }
    
    json_str = json.dumps(test_data)
    print(f"开始解析: {json_str}")
    
    # 收集事件
    events = []
    
    async def event_callback(event):
        events.append(event)
        print(f"事件: {event.event_type} - {event.data.path} = {event.data.value}")
    
    # 注册事件回调
    parser.add_event_callback(EventType.DELTA, event_callback)
    parser.add_event_callback(EventType.DONE, event_callback)
    parser.add_event_callback(EventType.START, event_callback)
    parser.add_event_callback(EventType.FINISH, event_callback)
    
    try:
        # 解析数据
        result = await parser.parse_chunk(
            json_str,
            session_id,
            is_final=True
        )
        
        print(f"解析成功，事件数量: {len(events)}")
        print(f"结果事件数量: {len(result)}")
        
        # 分析事件
        delta_events = [e for e in events if e.event_type == EventType.DELTA]
        print(f"Delta事件数量: {len(delta_events)}")
        
        if delta_events:
            print("Delta事件路径:")
            for event in delta_events:
                if hasattr(event.data, 'path'):
                    print(f"  - {event.data.path}")
        else:
            print("没有生成Delta事件")
            
        # 检查字段过滤器状态
        print("\n=== 字段过滤器状态 ===")
        print(f"字段过滤器启用: {field_filter.enabled}")
        try:
            print(f"包含路径: {field_filter.include_paths}")
            print(f"排除路径: {field_filter.exclude_paths}")
            print(f"模式: {field_filter.mode}")
            print(f"精确匹配: {field_filter.exact_match}")
        except Exception as e:
            print(f"解析失败: {e}")
        
        # 测试路径匹配
        print("\n=== 路径匹配测试 ===")
        test_paths = ['users', 'users[0]', 'users[0].id', 'users[0].name', 'users[0].password', 'data', 'data.count', 'data.secret', 'metadata']
        
        for path in test_paths:
            should_include = field_filter.should_include_path(path)
            print(f"路径 '{path}': {'包含' if should_include else '排除'}")
        
        # 获取解析状态
        print("\n=== 解析状态信息 ===")
        state = parser.get_parsing_state(session_id)
        if state:
            print(f"总块数: {state.total_chunks}")
            print(f"处理块数: {state.processed_chunks}")
            print(f"当前数据: {state.current_data}")
            print(f"错误数量: {len(state.errors)}")
            if state.errors:
                for error in state.errors:
                    print(f"  错误: {error}")
        
    except Exception as e:
        print(f"解析失败: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # 清理会话
        parser.cleanup_session(session_id)
        print("会话已清理")

if __name__ == "__main__":
    asyncio.run(debug_field_filtering())