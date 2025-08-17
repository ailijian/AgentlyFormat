#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试FieldFilter的字段过滤功能
"""

from src.agently_format.core.streaming_parser import FieldFilter

def test_field_filter():
    """测试FieldFilter的路径匹配逻辑"""
    
    # 测试exclude模式
    print("=== 测试exclude模式 ===")
    field_filter = FieldFilter(
        enabled=True,
        exclude_paths=["year", "creator"],
        mode="exclude",
        exact_match=False
    )
    
    test_paths = [
        "languages[0].name",
        "languages[0].year", 
        "languages[0].creator",
        "languages[0].description",
        "languages[0].popularity"
    ]
    
    for path in test_paths:
        should_include = field_filter.should_include_path(path)
        print(f"路径: {path:25} -> 应该包含: {should_include}")
    
    print("\n=== 测试include模式 ===")
    field_filter_include = FieldFilter(
        enabled=True,
        include_paths=["name", "description"],
        mode="include",
        exact_match=False
    )
    
    for path in test_paths:
        should_include = field_filter_include.should_include_path(path)
        print(f"路径: {path:25} -> 应该包含: {should_include}")

if __name__ == "__main__":
    test_field_filter()