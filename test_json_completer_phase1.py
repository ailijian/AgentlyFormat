#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试 JSON 补全器 Phase 1 优化功能

测试双阶段补全器、RepairTrace、策略自适应和增强置信度计算
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from agently_format.core.json_completer import (
    JSONCompleter, 
    CompletionStrategy, 
    RepairSeverity,
    RepairPhase
)
import json

def test_basic_completion():
    """测试基础补全功能"""
    print("=== 测试基础补全功能 ===")
    
    completer = JSONCompleter()
    
    # 测试用例
    test_cases = [
        '{"name": "test"',  # 缺少闭合括号
        '{"name": "test", "age": 25',  # 缺少闭合括号
        '{"name": "test", "items": [1, 2, 3',  # 缺少数组闭合
        '{"name": "test", "nested": {"key": "value"',  # 嵌套对象缺少闭合
        '{"valid": true}',  # 已经有效的JSON
    ]
    
    for i, test_json in enumerate(test_cases, 1):
        print(f"\n测试用例 {i}: {test_json}")
        
        result = completer.complete(test_json)
        
        print(f"  补全结果: {result.completed_json}")
        print(f"  是否有效: {result.is_valid}")
        print(f"  置信度: {result.confidence:.3f}")
        print(f"  使用策略: {result.strategy_used.value}")
        print(f"  修复步骤数: {len(result.repair_trace.steps)}")
        
        if result.repair_trace.steps:
            print(f"  修复追踪:")
            for step in result.repair_trace.steps:
                print(f"    - {step.phase.value}: {step.description} (置信度: {step.confidence:.3f})")

def test_repair_trace():
    """测试修复追踪功能"""
    print("\n=== 测试修复追踪功能 ===")
    
    completer = JSONCompleter()
    
    test_json = '{"name": "test", "items": [1, 2, 3'
    result = completer.complete(test_json)
    
    print(f"原始JSON: {test_json}")
    print(f"补全结果: {result.completed_json}")
    print(f"\n修复追踪详情:")
    print(f"  原始文本: {result.repair_trace.original_text}")
    print(f"  目标文本: {result.repair_trace.target_text}")
    print(f"  整体严重程度: {result.repair_trace.overall_severity.value}")
    print(f"  整体置信度: {result.repair_trace.overall_confidence:.3f}")
    print(f"  词法修复比例: {result.repair_trace.get_lexical_repair_ratio():.3f}")
    print(f"  已应用步骤数: {result.repair_trace.get_applied_steps_count()}")
    
    # 转换为字典格式
    trace_dict = result.repair_trace.to_dict()
    print(f"\n修复追踪字典格式:")
    for key, value in trace_dict.items():
        if key != 'steps':
            print(f"  {key}: {value}")

def test_strategy_adaptation():
    """测试策略自适应功能"""
    print("\n=== 测试策略自适应功能 ===")
    
    completer = JSONCompleter()
    
    # 模拟多次补全以触发策略自适应
    test_cases = [
        '{"name": "test1"',
        '{"name": "test2", "age": 25',
        '{"invalid": "json", "missing"',  # 故意的无效JSON
        '{"name": "test3", "items": [1, 2',
        '{"name": "test4"'
    ]
    
    print("执行多次补全以观察策略自适应:")
    
    for i, test_json in enumerate(test_cases, 1):
        result = completer.complete(test_json)
        print(f"\n补全 {i}:")
        print(f"  输入: {test_json}")
        print(f"  策略: {result.strategy_used.value}")
        print(f"  成功: {result.is_valid}")
        print(f"  置信度: {result.confidence:.3f}")
        print(f"  历史成功率: {result.historical_success_rate:.3f}")
    
    # 显示策略历史统计
    print("\n策略历史统计:")
    for strategy, history in completer.strategy_history.items():
        if history.total_attempts > 0:
            print(f"  {strategy.value}:")
            print(f"    总尝试: {history.total_attempts}")
            print(f"    成功率: {history.success_rate:.3f}")
            print(f"    平均置信度: {history.avg_confidence:.3f}")
    
    # 显示整体统计
    print("\n整体统计:")
    stats = completer.completion_stats
    for key, value in stats.items():
        print(f"  {key}: {value}")

def test_enhanced_confidence():
    """测试增强置信度计算"""
    print("\n=== 测试增强置信度计算 ===")
    
    completer = JSONCompleter()
    
    test_cases = [
        ('{"valid": true}', "已有效JSON"),
        ('{"name": "test"}', "简单补全"),
        ('{"name": "test", "age": 25', "中等复杂度补全"),
        ('{"complex": {"nested": {"deep": [1, 2, 3', "复杂嵌套补全"),
    ]
    
    for test_json, description in test_cases:
        result = completer.complete(test_json)
        
        print(f"\n{description}:")
        print(f"  输入: {test_json}")
        print(f"  输出: {result.completed_json}")
        print(f"  置信度: {result.confidence:.3f}")
        print(f"  补全应用: {result.completion_applied}")
        
        if result.repair_trace and result.repair_trace.steps:
            print(f"  修复步骤: {len(result.repair_trace.steps)}")
            print(f"  词法修复比例: {result.repair_trace.get_lexical_repair_ratio():.3f}")
            print(f"  整体严重程度: {result.repair_trace.overall_severity.value}")

def main():
    """主测试函数"""
    print("JSON补全器 Phase 1 优化功能测试")
    print("=" * 50)
    
    try:
        test_basic_completion()
        test_repair_trace()
        test_strategy_adaptation()
        test_enhanced_confidence()
        
        print("\n=== 所有测试完成 ===")
        print("Phase 1 优化功能验证成功！")
        
    except Exception as e:
        print(f"\n测试过程中出现错误: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())