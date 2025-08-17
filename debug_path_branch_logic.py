#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
调试_should_process_path_branch方法的逻辑
测试为什么users路径分支没有被正确处理
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from agently_format.core.streaming_parser import StreamingParser, FieldFilter
from agently_format.core.performance_optimizer import PerformanceOptimizer

def debug_path_branch_logic():
    """调试路径分支处理逻辑"""
    print("=== 调试路径分支处理逻辑 ===")
    
    # 创建性能优化器
    optimizer = PerformanceOptimizer()
    
    # 创建字段过滤器
    field_filter = FieldFilter(
        enabled=True,
        include_paths=["users", "data"],
        exclude_paths=["password", "secret", "admin"],
        mode="include",
        exact_match=False,
        performance_optimizer=optimizer
    )
    
    # 创建StreamingParser
    parser = StreamingParser(
        field_filter=field_filter
    )
    
    print(f"字段过滤器配置:")
    print(f"  enabled: {field_filter.enabled}")
    print(f"  include_paths: {field_filter.include_paths}")
    print(f"  exclude_paths: {field_filter.exclude_paths}")
    print(f"  mode: {field_filter.mode}")
    print()
    
    # 测试关键路径的分支处理逻辑
    test_paths = [
        "",           # 根路径
        "users",      # 顶级字段
        "users[0]",   # 数组元素
        "users[0].id", # 数组元素字段
        "users[0].name", # 数组元素字段
        "users[0].password", # 应该被排除的字段
        "data",       # 另一个顶级字段
        "data.count", # 嵌套字段
        "system",     # 不在include_paths中的字段
        "system.version" # 不在include_paths中的嵌套字段
    ]
    
    print("=== 路径分支处理测试 ===")
    for path in test_paths:
        try:
            should_process = parser._should_process_path_branch(path)
            should_include = parser._should_include_field(path)
            
            print(f"路径 '{path}':")
            print(f"  should_process_path_branch: {should_process} {'✅' if should_process else '❌'}")
            print(f"  should_include_field: {should_include} {'✅' if should_include else '❌'}")
            
            # 详细分析include模式下的分支处理逻辑
            if path in ["", "users", "users[0]", "data", "system"]:
                print(f"  详细分析 (include模式):")
                
                # 检查每个include_path的匹配情况
                for include_path in field_filter.include_paths:
                    print(f"    检查include_path '{include_path}':")
                    
                    # 条件1: 当前路径是目标路径的前缀
                    cond1 = include_path.startswith(path + ".") or include_path.startswith(path + "[")
                    print(f"      条件1 (目标路径前缀): {cond1}")
                    
                    # 条件2: 当前路径包含目标字段名
                    cond2 = path.endswith("." + include_path) or path.endswith("[" + include_path + "]")
                    print(f"      条件2 (包含目标字段): {cond2}")
                    
                    # 条件3: 目标路径是当前路径的前缀
                    cond3 = path.startswith(include_path + ".") or path.startswith(include_path + "[")
                    print(f"      条件3 (当前路径前缀): {cond3}")
                    
                    # 条件4: 精确匹配
                    cond4 = path == include_path
                    print(f"      条件4 (精确匹配): {cond4}")
                    
                    # 条件5: 简单字段名匹配
                    cond5 = path == include_path or include_path == path.split(".")[-1]
                    print(f"      条件5 (字段名匹配): {cond5}")
                    
                    any_match = cond1 or cond2 or cond3 or cond4 or cond5
                    print(f"      任一条件匹配: {any_match}")
                    
                print()
                
        except Exception as e:
            print(f"路径 '{path}': ❌ 错误 - {e}")
            import traceback
            print(f"错误堆栈: {traceback.format_exc()}")
    
    print("\n=== 模拟实际解析过程 ===")
    # 模拟实际的解析过程，看看哪些路径会被处理
    test_data = {
        "users": [{
            "id": 1,
            "name": "Alice",
            "password": "secret123"
        }],
        "data": {
            "count": 1
        },
        "system": {
            "version": "1.0"
        }
    }
    
    def simulate_traverse(data, path="", level=0):
        """模拟遍历过程"""
        indent = "  " * level
        print(f"{indent}处理路径 '{path}':")
        
        should_process = parser._should_process_path_branch(path)
        should_include = parser._should_include_field(path)
        
        print(f"{indent}  should_process_path_branch: {should_process}")
        print(f"{indent}  should_include_field: {should_include}")
        
        if not should_process:
            print(f"{indent}  ❌ 分支被剪枝，停止处理")
            return
        
        if isinstance(data, dict):
            for key, value in data.items():
                new_path = f"{path}.{key}" if path else key
                simulate_traverse(value, new_path, level + 1)
        elif isinstance(data, list):
            for i, item in enumerate(data):
                new_path = f"{path}[{i}]"
                simulate_traverse(item, new_path, level + 1)
        else:
            if should_include:
                print(f"{indent}  ✅ 生成Delta事件")
            else:
                print(f"{indent}  ❌ 字段被过滤")
    
    simulate_traverse(test_data)

if __name__ == "__main__":
    debug_path_branch_logic()