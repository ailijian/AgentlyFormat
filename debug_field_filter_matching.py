#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
调试FieldFilter的路径匹配逻辑
专门测试users路径为什么没有被正确包含
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from agently_format.core.streaming_parser import FieldFilter
from agently_format.core.performance_optimizer import PerformanceOptimizer

def debug_field_filter_matching():
    """调试FieldFilter的路径匹配逻辑"""
    print("=== 调试FieldFilter路径匹配逻辑 ===")
    
    # 创建性能优化器
    optimizer = PerformanceOptimizer()
    
    # 创建字段过滤器 - 模拟测试中的配置
    field_filter = FieldFilter(
        enabled=True,
        include_paths=["users", "data"],
        exclude_paths=["password", "secret", "admin"],
        mode="include",
        exact_match=False,
        performance_optimizer=optimizer
    )
    
    print(f"字段过滤器配置:")
    print(f"  enabled: {field_filter.enabled}")
    print(f"  include_paths: {field_filter.include_paths}")
    print(f"  exclude_paths: {field_filter.exclude_paths}")
    print(f"  mode: {field_filter.mode}")
    print(f"  exact_match: {field_filter.exact_match}")
    print()
    
    # 测试各种路径
    test_paths = [
        "users",
        "users[0]",
        "users[0].id",
        "users[0].name",
        "users[0].email",
        "users[0].password",
        "users[0].profile",
        "users[0].profile.age",
        "users[0].profile.secret",
        "data",
        "data.count",
        "data.api_key",
        "system",
        "system.version",
        "system.password"
    ]
    
    print("=== 路径匹配测试 ===")
    for path in test_paths:
        try:
            should_include = field_filter.should_include_path(path)
            print(f"路径 '{path}': {should_include} {'✅ 包含' if should_include else '❌ 排除'}")
            
            # 详细分析匹配过程
            if path in ["users", "users[0]", "users[0].id", "data", "data.count"]:
                print(f"  详细分析:")
                
                # 检查include_paths匹配
                include_match = field_filter._path_matches(path, field_filter.include_paths)
                print(f"    include_paths匹配: {include_match}")
                
                # 检查exclude_paths匹配
                exclude_match = field_filter._path_matches(path, field_filter.exclude_paths)
                print(f"    exclude_paths匹配: {exclude_match}")
                
                # 手动测试每个include模式
                for pattern in field_filter.include_paths:
                    pattern_match = field_filter._path_matches(path, [pattern])
                    print(f"    模式 '{pattern}' 匹配: {pattern_match}")
                print()
                
        except Exception as e:
            print(f"路径 '{path}': ❌ 错误 - {e}")
    
    print("\n=== 性能优化器缓存统计 ===")
    cache_stats = optimizer.get_cache_stats()
    print(f"路径匹配缓存: {cache_stats.get('path_matching', {})}")
    
    print("\n=== 手动测试关键路径 ===")
    # 手动测试users路径的各种匹配情况
    test_cases = [
        ("users", ["users"]),
        ("users", ["users", "data"]),
        ("users[0]", ["users"]),
        ("users[0].id", ["users"]),
        ("data", ["data"]),
        ("data.count", ["data"])
    ]
    
    for path, patterns in test_cases:
        try:
            match_result = field_filter._path_matches(path, patterns)
            print(f"路径 '{path}' 匹配模式 {patterns}: {match_result}")
        except Exception as e:
            print(f"路径 '{path}' 匹配模式 {patterns}: ❌ 错误 - {e}")

if __name__ == "__main__":
    debug_field_filter_matching()