#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
调试脚本：分析test_cache_clear测试失败的问题

该脚本用于详细分析PerformanceOptimizer的缓存清理功能，
验证clear_caches()方法是否正确清理所有缓存。
"""

import asyncio
import json
from src.agently_format.core.performance_optimizer import PerformanceOptimizer


def print_cache_stats(optimizer: PerformanceOptimizer, stage: str):
    """打印缓存统计信息"""
    print(f"\n=== {stage} 缓存统计 ===")
    stats = optimizer.get_cache_stats()
    
    print(f"字符串增量缓存:")
    print(f"  - 总数: {stats['string_delta_cache']['size']}")
    print(f"  - 命中: {stats['string_delta_cache']['hits']}")
    print(f"  - 总操作: {stats['string_delta_cache']['total']}")
    print(f"  - 命中率: {stats['string_delta_cache']['hit_rate']:.2%}")
    
    print(f"路径匹配缓存:")
    print(f"  - 总数: {stats['path_matching_cache']['size']}")
    print(f"  - 命中: {stats['path_matching_cache']['hits']}")
    print(f"  - 总操作: {stats['path_matching_cache']['total']}")
    print(f"  - 命中率: {stats['path_matching_cache']['hit_rate']:.2%}")
    
    # 检查内部缓存状态
    print(f"\n内部缓存状态:")
    if optimizer.string_optimizer:
        string_stats = optimizer.string_optimizer.get_cache_stats()
        print(f"  - string_optimizer 缓存大小: {string_stats.get('cache_size', 0)}")
    
    if optimizer.path_optimizer:
        path_stats = optimizer.path_optimizer.get_cache_stats()
        print(f"  - path_optimizer 缓存大小: {path_stats.get('cache_size', 0)}")
        print(f"  - path_optimizer 编译模式数: {path_stats.get('compiled_patterns', 0)}")
    
    # 显示性能指标
    print("\n性能指标:")
    print(f"  - 字符串优化操作数: {optimizer.metrics.optimized_string_operations}")
    print(f"  - 路径匹配操作数: {optimizer.metrics.path_match_operations}")
    print(f"  - 缓存路径匹配数: {optimizer.metrics.cached_path_matches}")
    



def main():
    """主函数：执行缓存清理测试"""
    print("开始缓存清理调试测试...")
    
    # 1. 实例化PerformanceOptimizer
    print("\n1. 创建PerformanceOptimizer实例")
    optimizer = PerformanceOptimizer()
    
    # 2. 执行缓存操作 - 字符串增量计算
    print("\n2. 执行字符串增量缓存操作")
    test_strings = [
        ("hello", "hello world"),
        ("test", "test data"),
        ("json", "json parsing"),
        ("cache", "cache test"),
        ("hello", "hello world"),  # 重复，应该命中缓存
    ]
    
    for old_str, new_str in test_strings:
        delta = optimizer.calculate_string_delta(old_str, new_str)
        print(f"  计算增量: '{old_str}' -> '{new_str}' = {delta}")
    
    # 3. 执行路径匹配缓存操作
    print("\n3. 执行路径匹配缓存操作")
    test_patterns = [
        ("users.*.name", "users.0.name"),
        ("data.*", "data.count"),
        ("*.password", "users.password"),
        ("system.*", "system.version"),
        ("users.*.name", "users.1.name"),  # 重复模式，应该命中缓存
    ]
    
    for pattern, path in test_patterns:
        matches = optimizer.match_path_patterns([pattern], path)
        print(f"  路径匹配: '{pattern}' vs '{path}' = {matches}")
    
    # 4. 检查缓存清理前的状态
    print("\n4. 缓存清理前的状态")
    print_cache_stats(optimizer, "清理前")
    
    # 验证缓存中确实有数据
    stats_before = optimizer.get_cache_stats()
    string_cache_total_before = stats_before['string_delta_cache']['total']
    path_cache_total_before = stats_before['path_matching_cache']['total']
    
    print(f"\n验证缓存数据:")
    print(f"  - 字符串缓存操作总数: {string_cache_total_before}")
    print(f"  - 路径匹配缓存操作总数: {path_cache_total_before}")
    if optimizer.string_optimizer:
        string_stats = optimizer.string_optimizer.get_cache_stats()
        print(f"  - 字符串缓存实际大小: {string_stats.get('cache_size', 0)}")
    if optimizer.path_optimizer:
        path_stats = optimizer.path_optimizer.get_cache_stats()
        print(f"  - 路径匹配缓存实际大小: {path_stats.get('cache_size', 0)}")
    
    # 5. 执行clear_caches()
    print("\n5. 执行缓存清理操作")
    optimizer.clear_caches()
    print("  缓存清理完成")
    
    # 6. 检查缓存清理后的状态
    print("\n6. 缓存清理后的状态")
    print_cache_stats(optimizer, "清理后")
    
    # 验证缓存确实被清理
    stats_after = optimizer.get_cache_stats()
    string_cache_total_after = stats_after['string_delta_cache']['total']
    path_cache_total_after = stats_after['path_matching_cache']['total']
    
    print(f"\n验证清理效果:")
    print(f"  - 字符串缓存操作总数: {string_cache_total_after}")
    print(f"  - 路径匹配缓存操作总数: {path_cache_total_after}")
    if optimizer.string_optimizer:
        string_stats_after = optimizer.string_optimizer.get_cache_stats()
        print(f"  - 字符串缓存实际大小: {string_stats_after.get('cache_size', 0)}")
    if optimizer.path_optimizer:
        path_stats_after = optimizer.path_optimizer.get_cache_stats()
        print(f"  - 路径匹配缓存实际大小: {path_stats_after.get('cache_size', 0)}")
    
    # 7. 验证测试期望的断言
    print("\n7. 验证测试断言")
    
    # 获取清理后的缓存大小
    string_cache_size = 0
    path_cache_size = 0
    
    if optimizer.string_optimizer:
        string_stats_final = optimizer.string_optimizer.get_cache_stats()
        string_cache_size = string_stats_final.get('cache_size', 0)
    
    if optimizer.path_optimizer:
        path_stats_final = optimizer.path_optimizer.get_cache_stats()
        path_cache_size = path_stats_final.get('cache_size', 0)
    
    print(f"\n断言验证:")
    print(f"  - 字符串缓存大小 == 0: {string_cache_size == 0} (实际: {string_cache_size})")
    print(f"  - 路径匹配缓存大小 == 0: {path_cache_size == 0} (实际: {path_cache_size})")
    
    # 模拟测试断言
    try:
        assert string_cache_size == 0, f"字符串缓存应该为空，但实际大小为 {string_cache_size}"
        assert path_cache_size == 0, f"路径匹配缓存应该为空，但实际大小为 {path_cache_size}"
        print("\n✅ 所有断言通过！缓存清理功能正常工作")
    except AssertionError as e:
        print(f"\n❌ 断言失败: {e}")
    
    # 检查统计信息是否重置
    print(f"\n统计信息检查:")
    print(f"  - 字符串缓存统计重置: {string_cache_total_after == 0} (实际: {string_cache_total_after})")
    print(f"  - 路径匹配缓存统计重置: {path_cache_total_after == 0} (实际: {path_cache_total_after})")
    
    # 8. 测试清理后的缓存功能
    print("\n8. 测试清理后的缓存功能")
    print("执行新的缓存操作以验证功能正常...")
    
    # 执行新的字符串增量计算
    new_delta = optimizer.calculate_string_delta("new", "new test")
    print(f"  新的字符串增量: 'new' -> 'new test' = {new_delta}")
    
    # 执行新的路径匹配
    new_matches = optimizer.match_path_patterns(["test.*"], "test.field")
    print(f"  新的路径匹配: 'test.*' vs 'test.field' = {new_matches}")
    
    # 检查新操作后的统计
    final_stats = optimizer.get_cache_stats()
    print(f"\n清理后新操作统计:")
    print(f"  - 字符串缓存操作总数: {final_stats['string_delta_cache']['total']}")
    print(f"  - 路径匹配缓存操作总数: {final_stats['path_matching_cache']['total']}")
    
    # 9. 总结
    print("\n=== 调试总结 ===")
    if string_cache_size == 0 and path_cache_size == 0:
        print("✅ 缓存清理功能正常工作")
    else:
        print("❌ 缓存清理功能存在问题")
        print(f"   - 字符串缓存未完全清理: {string_cache_size} 项")
        print(f"   - 路径匹配缓存未完全清理: {path_cache_size} 项")
    
    if string_cache_total_after == 0 and path_cache_total_after == 0:
        print("✅ 缓存统计信息正确重置")
    else:
        print("❌ 缓存统计信息未正确重置")
        print(f"   - 字符串缓存统计: {string_cache_total_after}")
        print(f"   - 路径匹配缓存统计: {path_cache_total_after}")
    
    if final_stats['string_delta_cache']['total'] > 0 and final_stats['path_matching_cache']['total'] > 0:
        print("✅ 清理后缓存功能正常")
    else:
        print("❌ 清理后缓存功能异常")


if __name__ == "__main__":
    main()