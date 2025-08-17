#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
调试路径匹配功能
"""

import asyncio
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from agently_format.core.streaming_parser import FieldFilter
from agently_format.core.performance_optimizer import PerformanceOptimizer

def debug_path_matching():
    """调试路径匹配功能"""
    print("=== 路径匹配调试 ===")
    
    # 创建性能优化器
    optimizer = PerformanceOptimizer()
    
    # 创建字段过滤器
    field_filter = FieldFilter(
        enabled=True,
        include_paths=["users", "data"],
        exclude_paths=[],
        mode="include",
        exact_match=False,
        performance_optimizer=optimizer
    )
    
    # 测试路径列表
    test_paths = [
        "",  # 根路径
        "users",  # 顶级字段
        "data",   # 顶级字段
        "system", # 不包含的字段
        "users[0]",  # 数组元素
        "users[0].id",  # 数组元素的字段
        "users[0].name",  # 数组元素的字段
        "users[0].password",  # 敏感字段
        "data.count",  # 嵌套字段
        "data.api_key",  # 嵌套字段
        "system.version",  # 不包含的嵌套字段
    ]
    
    print(f"字段过滤器配置:")
    print(f"  启用: {field_filter.enabled}")
    print(f"  模式: {field_filter.mode}")
    print(f"  包含路径: {field_filter.include_paths}")
    print(f"  排除路径: {field_filter.exclude_paths}")
    print(f"  精确匹配: {field_filter.exact_match}")
    print()
    
    print("路径匹配测试:")
    for path in test_paths:
        try:
            # 测试should_include_path方法
            should_include = field_filter.should_include_path(path)
            print(f"  路径 '{path}': {should_include}")
            
            # 测试_path_matches方法
            path_matches = field_filter._path_matches(path, field_filter.include_paths)
            print(f"    _path_matches结果: {path_matches}")
            
            # 测试性能优化器的match_path_patterns方法
            if field_filter.performance_optimizer:
                optimizer_result = field_filter.performance_optimizer.match_path_patterns(path, field_filter.include_paths)
                print(f"    优化器结果: {optimizer_result}")
            
        except Exception as e:
            print(f"  路径 '{path}': 错误 - {e}")
        print()
    
    # 检查缓存统计
    print("缓存统计:")
    stats = optimizer.get_stats()
    print(f"  路径匹配缓存: {stats.get('path_matching_cache', {})}")
    
if __name__ == "__main__":
    debug_path_matching()