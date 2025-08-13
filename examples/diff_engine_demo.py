#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
差分引擎演示示例

本示例展示了如何使用新的结构化差分引擎来处理流式 JSON 数据，
包括事件去重、合并、幂等性检查等高级功能。
"""

import json
import time
from typing import Dict, Any, List

# 导入差分引擎相关模块
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.agently_format.core.diff_engine import (
    StructuredDiffEngine,
    DiffMode,
    CoalescingConfig,
    create_diff_engine
)
from src.agently_format.core.streaming_parser import StreamingParser
from src.agently_format.core.event_system import StreamingEvent


def demo_basic_diff_engine():
    """演示基础差分引擎功能"""
    print("=== 基础差分引擎演示 ===")
    
    # 创建差分引擎
    engine = create_diff_engine(
        mode="smart",
        coalescing_enabled=False  # 禁用合并以便观察所有事件
    )
    
    # 模拟数据变化序列
    data_stages = [
        {},
        {"user": {"name": "Alice"}},
        {"user": {"name": "Alice", "age": 25}},
        {"user": {"name": "Alice", "age": 25, "profile": {"email": "alice@example.com"}}},
        {"user": {"name": "Bob", "age": 25, "profile": {"email": "alice@example.com"}}},  # 名字变更
    ]
    
    previous_data = {}
    all_events = []
    
    for i, current_data in enumerate(data_stages[1:], 1):
        print(f"\n--- 阶段 {i}: {json.dumps(current_data, ensure_ascii=False)} ---")
        
        # 计算差分
        diffs = engine.compute_diff(previous_data, current_data)
        print(f"发现 {len(diffs)} 个差分:")
        
        # 生成事件
        for diff in diffs:
            print(f"  路径: {diff.path}, 类型: {diff.diff_type}, 新值: {diff.new_value}")
            
            # 发射事件
            event = engine.emit_delta_event(diff, "demo_session", len(all_events) + 1)
            if event:
                all_events.append(event)
                print(f"    -> 事件已发射: {event.event_type}")
            else:
                print(f"    -> 事件被抑制或合并")
        
        previous_data = current_data.copy()
    
    # 显示统计信息
    stats = engine.get_stats()
    print(f"\n=== 统计信息 ===")
    print(f"总差分次数: {stats['total_diffs']}")
    print(f"抑制的重复事件: {stats['suppressed_duplicates']}")
    print(f"合并的事件: {stats['coalesced_events']}")
    print(f"发射的 DONE 事件: {stats['done_events_emitted']}")
    print(f"总事件数: {len(all_events)}")


def demo_event_coalescing():
    """演示事件合并功能"""
    print("\n\n=== 事件合并演示 ===")
    
    # 创建启用合并的差分引擎
    engine = StructuredDiffEngine(
        diff_mode=DiffMode.SMART,
        coalescing_config=CoalescingConfig(
            enabled=True,
            time_window_ms=100,
            max_coalesced_events=3
        )
    )
    
    # 模拟快速连续的数据变化
    base_data = {"counter": 0, "status": "processing"}
    events = []
    
    print("模拟快速连续更新...")
    for i in range(1, 8):
        new_data = {"counter": i, "status": "processing"}
        
        # 计算差分
        diffs = engine.compute_diff(base_data, new_data)
        
        # 生成事件
        for diff in diffs:
            event = engine.emit_delta_event(diff, "coalescing_demo", i)
            if event:
                events.append(event)
                print(f"  立即发射事件: counter = {diff.new_value}")
        
        base_data = new_data.copy()
        time.sleep(0.01)  # 模拟时间间隔
    
    # 刷新合并缓冲区
    print("\n刷新合并缓冲区...")
    final_events = engine.flush_all_coalescing_buffers()
    events.extend(final_events)
    
    print(f"合并后的事件数: {len(final_events)}")
    for event in final_events:
        metadata = event.data.metadata or {}
        if metadata.get("is_coalesced"):
            print(f"  合并事件: 路径={event.data.path}, 合并数量={metadata.get('coalesced_count', 0)}")
    
    # 显示统计信息
    stats = engine.get_stats()
    print(f"\n合并统计: {stats['coalesced_events']} 个事件被合并")


def demo_idempotent_events():
    """演示幂等事件功能"""
    print("\n\n=== 幂等事件演示 ===")
    
    engine = create_diff_engine(coalescing_enabled=False)
    
    # 模拟重复的数据更新
    data = {"message": "Hello World"}
    
    print("第一次更新...")
    diffs1 = engine.compute_diff({}, data)
    for diff in diffs1:
        event = engine.emit_delta_event(diff, "idempotent_demo", 1)
        if event:
            print(f"  事件发射: {diff.path} = {diff.new_value}")
        else:
            print(f"  事件被抑制: {diff.path}")
    
    print("\n相同数据的第二次更新...")
    diffs2 = engine.compute_diff(data, data)  # 相同数据
    print(f"差分数量: {len(diffs2)} (应该为0，因为数据相同)")
    
    print("\n模拟相同值的重复发射...")
    # 手动测试幂等性
    should_emit_1 = engine.should_emit_event("message", "Hello World")
    print(f"第一次检查是否发射: {should_emit_1}")
    
    # 模拟事件已发射
    engine.path_states["message"].update_hash("Hello World")
    
    should_emit_2 = engine.should_emit_event("message", "Hello World")
    print(f"第二次检查是否发射: {should_emit_2} (应该为 False)")
    
    should_emit_3 = engine.should_emit_event("message", "Hello Universe")
    print(f"不同值检查是否发射: {should_emit_3} (应该为 True)")


def demo_streaming_parser_integration():
    """演示与流式解析器的集成"""
    print("\n\n=== 流式解析器集成演示 ===")
    
    # 创建启用差分引擎的流式解析器
    parser = StreamingParser(
        enable_diff_engine=True,
        diff_mode=DiffMode.SMART,
        coalescing_enabled=True,
        coalescing_time_window_ms=50
    )
    
    # 添加事件回调
    received_events = []
    
    def event_handler(event: StreamingEvent):
        received_events.append(event)
        print(f"  收到事件: {event.event_type} - {event.data.path} = {event.data.value}")
    
    # 导入事件类型
    from src.agently_format.core.event_system import EventType
    parser.add_event_callback(EventType.DELTA, event_handler)
    parser.add_event_callback(EventType.DONE, event_handler)
    parser.add_event_callback(EventType.ERROR, event_handler)
    
    # 创建解析会话
    session_id = parser.create_session()
    print(f"创建会话: {session_id}")
    
    # 模拟流式 JSON 数据
    json_chunks = [
        '{"user"',
        ': {"name"',
        ': "Alice"',
        ', "age": 30',
        ', "skills": [',
        '"Python"',
        ', "JavaScript"',
        ']}}'
    ]
    
    print("\n开始流式解析...")
    for i, chunk in enumerate(json_chunks):
        print(f"处理块 {i+1}: '{chunk}'")
        try:
            # 注意：这里简化演示，实际使用时应该用异步版本
            # 由于演示目的，我们跳过实际的流式解析
            print(f"  -> 模拟解析: {chunk}")
        except Exception as e:
            print(f"  解析错误: {e}")
    
    # 完成会话
    print("\n完成解析会话...")
    print("  -> 模拟会话完成")
    
    # 显示结果
    final_data = parser.get_current_data(session_id)
    print(f"\n最终解析结果: {json.dumps(final_data, ensure_ascii=False)}")
    print(f"总共收到 {len(received_events)} 个事件")
    
    # 显示解析器统计信息
    stats = parser.get_stats()
    print(f"\n解析器统计信息:")
    print(f"  解析的块数: {stats.get('chunks_parsed', 0)}")
    print(f"  差分引擎统计: {stats.get('diff_engine_stats', {})}")


def demo_conservative_vs_smart_mode():
    """演示保守模式与智能模式的差异"""
    print("\n\n=== 保守模式 vs 智能模式演示 ===")
    
    # 测试数据：列表修改
    old_data = {"items": ["apple", "banana", "cherry", "date"]}
    new_data = {"items": ["apple", "blueberry", "cherry", "date", "elderberry"]}
    
    print(f"原数据: {json.dumps(old_data, ensure_ascii=False)}")
    print(f"新数据: {json.dumps(new_data, ensure_ascii=False)}")
    
    # 保守模式
    print("\n--- 保守模式 ---")
    conservative_engine = StructuredDiffEngine(diff_mode=DiffMode.CONSERVATIVE)
    conservative_diffs = conservative_engine.compute_diff(old_data, new_data)
    
    for diff in conservative_diffs:
        print(f"  {diff.diff_type}: {diff.path} = {diff.new_value}")
    
    # 智能模式
    print("\n--- 智能模式 ---")
    smart_engine = StructuredDiffEngine(diff_mode=DiffMode.SMART)
    smart_diffs = smart_engine.compute_diff(old_data, new_data)
    
    for diff in smart_diffs:
        print(f"  {diff.diff_type}: {diff.path} = {diff.new_value}")
    
    print(f"\n保守模式差分数: {len(conservative_diffs)}")
    print(f"智能模式差分数: {len(smart_diffs)}")


def main():
    """主演示函数"""
    print("差分引擎功能演示")
    print("=" * 50)
    
    try:
        # 运行各个演示
        demo_basic_diff_engine()
        demo_event_coalescing()
        demo_idempotent_events()
        demo_streaming_parser_integration()
        demo_conservative_vs_smart_mode()
        
        print("\n\n=== 演示完成 ===")
        print("差分引擎的主要特性:")
        print("✓ 结构化差分算法 (dict/list aware)")
        print("✓ 事件去重与幂等性")
        print("✓ 事件合并 (coalescing)")
        print("✓ 智能 vs 保守模式")
        print("✓ 与流式解析器集成")
        print("✓ 完整的统计信息")
        
    except Exception as e:
        print(f"演示过程中发生错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()