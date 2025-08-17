#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
调试缓存统计问题的脚本
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from agently_format.core.performance_optimizer import PerformanceOptimizer

def debug_cache_statistics():
    """调试缓存统计功能"""
    print("=== 调试缓存统计功能 ===")
    
    # 创建性能优化器实例
    optimizer = PerformanceOptimizer(
        enable_string_optimization=True,
        enable_path_optimization=True,
        enable_memory_management=True
    )
    
    print(f"初始度量指标:")
    print(f"  optimized_string_operations: {optimizer.metrics.optimized_string_operations}")
    print(f"  path_match_operations: {optimizer.metrics.path_match_operations}")
    print(f"  cached_path_matches: {optimizer.metrics.cached_path_matches}")
    
    # 获取初始缓存统计
    initial_stats = optimizer.get_cache_stats()
    print(f"\n初始缓存统计:")
    for cache_name, stats in initial_stats.items():
        print(f"  {cache_name}: {stats}")
    
    # 执行字符串增量计算操作
    print("\n=== 执行字符串增量计算操作 ===")
    delta1 = optimizer.calculate_string_delta("Hello", "Hello World")
    print(f"Delta 1: {delta1}")
    
    delta2 = optimizer.calculate_string_delta("Hello World", "Hello Beautiful World")
    print(f"Delta 2: {delta2}")
    
    print(f"\n字符串操作后度量指标:")
    print(f"  optimized_string_operations: {optimizer.metrics.optimized_string_operations}")
    
    # 执行路径匹配操作
    print("\n=== 执行路径匹配操作 ===")
    match1 = optimizer.match_path_patterns("config.settings", ["config.*"])
    print(f"Match 1: {match1}")
    
    match2 = optimizer.match_path_patterns("data.user.name", ["data.*"])
    print(f"Match 2: {match2}")
    
    print(f"\n路径匹配后度量指标:")
    print(f"  path_match_operations: {optimizer.metrics.path_match_operations}")
    print(f"  cached_path_matches: {optimizer.metrics.cached_path_matches}")
    
    # 获取最终缓存统计
    final_stats = optimizer.get_cache_stats()
    print(f"\n最终缓存统计:")
    for cache_name, stats in final_stats.items():
        print(f"  {cache_name}: {stats}")
    
    # 检查string_optimizer和path_optimizer的状态
    print(f"\n=== 优化器状态检查 ===")
    print(f"string_optimizer: {optimizer.string_optimizer}")
    print(f"path_optimizer: {optimizer.path_optimizer}")
    
    if optimizer.string_optimizer:
        string_stats = optimizer.string_optimizer.get_cache_stats()
        print(f"string_optimizer stats: {string_stats}")
    
    if optimizer.path_optimizer:
        path_stats = optimizer.path_optimizer.get_cache_stats()
        print(f"path_optimizer stats: {path_stats}")
    
    # 验证测试期望
    print(f"\n=== 验证测试期望 ===")
    string_cache = final_stats.get('string_delta_cache', {})
    path_cache = final_stats.get('path_matching_cache', {})
    
    print(f"string_delta_cache total: {string_cache.get('total', 0)} (期望 >= 2)")
    print(f"string_delta_cache hits: {string_cache.get('hits', 0)} (期望 >= 1)")
    print(f"string_delta_cache size: {string_cache.get('size', 0)} (期望 >= 1)")
    
    print(f"path_matching_cache total: {path_cache.get('total', 0)} (期望 >= 1)")
    print(f"path_matching_cache size: {path_cache.get('size', 0)} (期望 >= 1)")
    
    # 检查断言
    try:
        assert string_cache.get('total', 0) >= 2, f"string_delta_cache total {string_cache.get('total', 0)} < 2"
        assert string_cache.get('hits', 0) >= 1, f"string_delta_cache hits {string_cache.get('hits', 0)} < 1"
        assert string_cache.get('size', 0) >= 1, f"string_delta_cache size {string_cache.get('size', 0)} < 1"
        assert path_cache.get('total', 0) >= 1, f"path_matching_cache total {path_cache.get('total', 0)} < 1"
        assert path_cache.get('size', 0) >= 1, f"path_matching_cache size {path_cache.get('size', 0)} < 1"
        print("\n✅ 所有断言通过！")
    except AssertionError as e:
        print(f"\n❌ 断言失败: {e}")

if __name__ == "__main__":
    debug_cache_statistics()