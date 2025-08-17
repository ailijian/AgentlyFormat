#!/usr/bin/env python3
"""调试字段过滤器的路径匹配逻辑"""

from src.agently_format.core.streaming_parser import FieldFilter

def test_field_filter():
    """测试FieldFilter的路径匹配逻辑"""
    print("=== 测试FieldFilter路径匹配 ===")
    
    # 测试排除字段
    filter_obj = FieldFilter(
        include_paths=None,
        exclude_paths=["year", "creator"],
        exact_match=False
    )
    
    # 测试各种路径
    test_paths = [
        "languages[0].name",
        "languages[0].description", 
        "languages[0].year",
        "languages[0].creator",
        "languages[0].popularity",
        "languages[1].name",
        "languages[1].description",
        "languages[1].year", 
        "languages[1].creator",
        "languages[1].popularity"
    ]
    
    print("\n排除字段 ['year', 'creator'] 的测试结果:")
    for path in test_paths:
        should_include = filter_obj.should_include_path(path)
        print(f"路径: {path:25} -> {'包含' if should_include else '排除'}")
    
    print("\n=== 详细匹配分析 ===")
    # 特别分析year字段为什么没有被排除
    year_path = "languages[0].year"
    print(f"\n分析路径: {year_path}")
    print(f"排除路径列表: {filter_obj.exclude_paths}")
    
    for exclude_pattern in filter_obj.exclude_paths:
        matches = filter_obj._path_matches(year_path, [exclude_pattern])
        print(f"与模式 '{exclude_pattern}' 匹配: {matches}")
        
        # 详细分析匹配过程
        if filter_obj.exact_match:
            exact_match = year_path == exclude_pattern
            print(f"  精确匹配: {exact_match}")
        else:
            prefix_match = year_path.startswith(exclude_pattern)
            endswith_dot = year_path.endswith('.' + exclude_pattern)
            endswith_bracket = year_path.endswith('[' + exclude_pattern + ']')
            wildcard_match = filter_obj._wildcard_match(year_path, exclude_pattern)
            print(f"  前缀匹配: {prefix_match}")
            print(f"  字段名匹配(.{exclude_pattern}): {endswith_dot}")
            print(f"  字段名匹配([{exclude_pattern}]): {endswith_bracket}")
            print(f"  通配符匹配: {wildcard_match}")
            
    # 测试creator字段
    creator_path = "languages[0].creator"
    print(f"\n分析路径: {creator_path}")
    
    for exclude_pattern in filter_obj.exclude_paths:
        matches = filter_obj._path_matches(creator_path, [exclude_pattern])
        print(f"与模式 '{exclude_pattern}' 匹配: {matches}")
        
        if not filter_obj.exact_match:
            prefix_match = creator_path.startswith(exclude_pattern)
            endswith_dot = creator_path.endswith('.' + exclude_pattern)
            endswith_bracket = creator_path.endswith('[' + exclude_pattern + ']')
            wildcard_match = filter_obj._wildcard_match(creator_path, exclude_pattern)
            print(f"  前缀匹配: {prefix_match}")
            print(f"  字段名匹配(.{exclude_pattern}): {endswith_dot}")
            print(f"  字段名匹配([{exclude_pattern}]): {endswith_bracket}")
            print(f"  通配符匹配: {wildcard_match}")

if __name__ == "__main__":
    test_field_filter()