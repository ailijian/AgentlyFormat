#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
调试内存管理集成测试失败问题
分析为什么cleanup_session后活跃会话数没有减少
"""

import sys
import os
import asyncio
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from agently_format import StreamingParser
import json

async def debug_memory_management():
    """调试内存管理集成测试失败问题"""
    print("=== 调试内存管理集成测试 ===")
    
    # 创建解析器实例
    parser = StreamingParser()
    print(f"初始化解析器完成")
    
    # 获取初始内存信息
    initial_memory = parser.memory_manager.get_memory_usage()
    print(f"初始内存信息: {initial_memory}")
    
    # 创建5个会话
    sessions = []
    test_data = '{"name": "test", "value": 123}'
    
    print("\n=== 创建5个会话 ===")
    for i in range(5):
        session_id = f"session_{i}"
        sessions.append(session_id)
        
        # 先创建会话
        created_session_id = parser.create_session(session_id)
        print(f"创建会话 {created_session_id}")
        
        # 为每个会话解析一些数据 - 使用异步的parse_chunk方法
        events = await parser.parse_chunk(session_id, test_data, is_final=True)
        print(f"Generated {len(events)} events for {session_id}")
        for event in events:
             print(f"Event: {event.event_type} - {event.data.path if hasattr(event.data, 'path') else 'no_path'}")
        
        # 检查当前内存状态
        current_memory = parser.memory_manager.get_memory_usage()
        print(f"  当前活跃会话数: {current_memory.get('active_sessions', 0)}")
        print(f"  解析状态数: {len(parser.parsing_states)}")
    
    # 获取创建所有会话后的内存信息
    memory_after_creation = parser.memory_manager.get_memory_usage()
    print(f"\n创建5个会话后的内存信息: {memory_after_creation}")
    print(f"解析状态字典内容: {list(parser.parsing_states.keys())}")
    
    # 清理3个会话
    print("\n=== 清理3个会话 ===")
    sessions_to_cleanup = sessions[:3]  # 清理前3个会话
    
    for session_id in sessions_to_cleanup:
        print(f"\n清理会话 {session_id}")
        print(f"  清理前解析状态: {list(parser.parsing_states.keys())}")
        print(f"  清理前内存信息: {parser.memory_manager.get_memory_usage()}")
        
        # 执行清理
        parser.cleanup_session(session_id)
        
        print(f"  清理后解析状态: {list(parser.parsing_states.keys())}")
        print(f"  清理后内存信息: {parser.memory_manager.get_memory_usage()}")
    
    # 获取清理后的内存信息
    memory_after_cleanup = parser.memory_manager.get_memory_usage()
    print(f"\n清理3个会话后的最终内存信息: {memory_after_cleanup}")
    print(f"最终解析状态字典内容: {list(parser.parsing_states.keys())}")
    
    # 验证测试期望
    print("\n=== 验证测试期望 ===")
    created_sessions = memory_after_creation.get('active_sessions', 0)
    cleanup_sessions = memory_after_cleanup.get('active_sessions', 0)
    print(f"创建后活跃会话数: {created_sessions}")
    print(f"清理后活跃会话数: {cleanup_sessions}")
    print(f"期望: {cleanup_sessions} < {created_sessions}")
    
    if cleanup_sessions < created_sessions:
        print("✅ 测试应该通过")
    else:
        print("❌ 测试失败 - 活跃会话数没有减少")
        
        # 详细分析问题
        print("\n=== 问题分析 ===")
        print(f"解析状态字典大小: {len(parser.parsing_states)}")
        print(f"内存管理器报告的活跃会话数: {memory_after_cleanup.get('active_sessions', 0)}")
        
        # 检查内存管理器的状态
        if hasattr(parser, 'memory_manager'):
            print(f"内存管理器存在: {parser.memory_manager}")
            if hasattr(parser.memory_manager, 'session_registry'):
                print(f"会话注册表: {parser.memory_manager.session_registry}")
            if hasattr(parser.memory_manager, 'stats'):
                print(f"内存管理器统计: {parser.memory_manager.stats}")
        else:
            print("内存管理器不存在")

if __name__ == "__main__":
    asyncio.run(debug_memory_management())