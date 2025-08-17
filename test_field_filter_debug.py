#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
字段过滤器调试测试
测试FieldFilter的路径匹配逻辑
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from agently_format.core.streaming_parser import FieldFilter

def test_field_filter_matching():
    """测试字段过滤器的路径匹配逻辑"""
    print("=== 测试字段过滤器路径匹配逻辑 ===")
    
    # 创建排除year和creator的过滤器
    field_filter = FieldFilter(
        enabled=True,
        exclude_paths=['year', 'creator'],
        mode='exclude'
    )
    
    # 测试各种路径
    test_paths = [
        'languages[0].name',
        'languages[0].year',
        'languages[0].creator', 
        'languages[0].description',
        'languages[0].popularity',
        'languages[1].name',
        'languages[1].year',
        'languages[1].creator',
        'languages[1].description', 
        'languages[1].popularity',
        'name',
        'year',
        'creator',
        'description',
        'popularity'
    ]
    
    print("\n排除字段: ['year', 'creator']")
    print("模式: exclude")
    print("精确匹配: False")
    print()
    
    for path in test_paths:
        should_include = field_filter.should_include_path(path)
        status = "包含" if should_include else "排除"
        print(f"路径: {path:<25} -> {status}")
        
        # 详细分析匹配过程
        matches = field_filter._path_matches(path, field_filter.exclude_paths)
        if matches:
            print(f"  匹配原因: 路径 '{path}' 匹配排除模式")
            # 检查具体匹配的模式
            for pattern in field_filter.exclude_paths:
                if path.startswith(pattern):
                    print(f"    - 前缀匹配: '{pattern}'")
                elif path.endswith('.' + pattern):
                    print(f"    - 字段名匹配(点): '.{pattern}'")
                elif path.endswith('[' + pattern + ']'):
                    print(f"    - 字段名匹配(括号): '[{pattern}]'")
                elif field_filter._wildcard_match(path, pattern):
                    print(f"    - 通配符匹配: '{pattern}'")
        print()

if __name__ == "__main__":
    test_field_filter_matching()