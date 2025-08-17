#!/usr/bin/env python3
"""调试错误处理集成测试的详细脚本

分析test_error_handling_integration测试失败的原因，
特别是assert 0 > 0问题的具体位置和原因。
"""

import asyncio
import json
import sys
import traceback
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.agently_format.core.streaming_parser import StreamingParser, FieldFilter
from src.agently_format.core.performance_optimizer import PerformanceOptimizer
from src.agently_format.core.memory_manager import MemoryManager
from src.agently_format.core.event_system import EventType

async def debug_error_handling_integration():
    """调试错误处理集成测试"""
    print("=== 开始调试错误处理集成测试 ===")
    
    try:
        # 创建字段过滤器
        field_filter = FieldFilter(
            enabled=True,
            include_paths=["users"],
            exclude_paths=[],
            mode="include",
            exact_match=False
        )
        
        # 创建集成解析器（StreamingParser会自动创建性能优化器和内存管理器）
        integrated_parser = StreamingParser(
            field_filter=field_filter
        )
        
        print("集成解析器创建成功")
        
        # 开始测试错误处理集成
        session_id = integrated_parser.create_session("error_test")
        print(f"创建会话: {session_id}")
        
        events = []
        
        async def event_callback(event):
            events.append(event)
            print(f"收到事件: {event.event_type} - {event.data}")
        
        integrated_parser.add_event_callback(EventType.ERROR, event_callback)
        print("添加错误事件回调")
        
        # 解析无效JSON
        print("\n=== 开始解析无效JSON ===")
        invalid_json = '{"invalid": json syntax here}'
        print(f"无效JSON: {invalid_json}")
        
        try:
            result = await integrated_parser.parse_chunk(
                invalid_json,
                session_id,
                is_final=True
            )
            print(f"解析结果: {len(result)} 个事件")
            for i, event in enumerate(result):
                print(f"  事件 {i+1}: {event.event_type} - {event.data}")
        except Exception as e:
            print(f"解析过程中发生异常: {e}")
            traceback.print_exc()
        
        # 验证错误处理
        print("\n=== 验证错误处理 ===")
        error_events = [e for e in events if e.event_type == EventType.ERROR]
        result_error_events = [e for e in result if e.event_type == EventType.ERROR]
        
        print(f"回调收到的错误事件数量: {len(error_events)}")
        print(f"结果中的错误事件数量: {len(result_error_events)}")
        
        # 这里是可能的问题点
        total_error_events = len(error_events) + len(result_error_events)
        print(f"总错误事件数量: {total_error_events}")
        
        # 检查是否这里有问题的断言
        if total_error_events == 0:
            print("警告: 没有生成任何错误事件！")
            print("这可能是assert 0 > 0失败的原因")
        
        # 验证会话状态
        print("\n=== 验证会话状态 ===")
        state = integrated_parser.get_parsing_state(session_id)
        if state is not None:
            print(f"会话状态存在: {state}")
            print(f"会话错误数量: {len(state.errors)}")
            if len(state.errors) == 0:
                print("警告: 会话状态中没有错误记录！")
                print("这可能是另一个assert失败的原因")
        else:
            print("警告: 会话状态为None！")
        
        # 模拟测试断言
        print("\n=== 模拟测试断言 ===")
        try:
            # 应该有错误事件
            assert len(error_events) > 0 or len(result_error_events) > 0, "应该有错误事件"
            print("✓ 错误事件断言通过")
        except AssertionError as e:
            print(f"✗ 错误事件断言失败: {e}")
            print("这可能对应 assert 0 > 0 失败")
        
        try:
            # 验证会话状态
            assert state is not None, "会话状态不应为None"
            print("✓ 会话状态存在断言通过")
        except AssertionError as e:
            print(f"✗ 会话状态存在断言失败: {e}")
        
        try:
            assert len(state.errors) > 0, "会话应该有错误记录"
            print("✓ 会话错误记录断言通过")
        except AssertionError as e:
            print(f"✗ 会话错误记录断言失败: {e}")
            print("这可能对应另一个断言失败")
        
        # 检查解析器的错误处理配置
        print("\n=== 检查解析器配置 ===")
        print(f"启用补全: {integrated_parser.enable_completion}")
        print(f"启用差异引擎: {integrated_parser.enable_diff_engine}")
        print(f"性能优化器: {integrated_parser.performance_optimizer is not None}")
        print(f"内存管理器: {integrated_parser.memory_manager is not None}")
        print(f"字段过滤器: {integrated_parser.field_filter is not None}")
        
    except Exception as e:
        print(f"调试过程中发生异常: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(debug_error_handling_integration())