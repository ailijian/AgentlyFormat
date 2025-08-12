#!/usr/bin/env python3

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from agently_format.core.path_builder import PathBuilder, PathStyle

# API测试使用的示例数据
sample_data = {
    "users": [
        {
            "id": 1,
            "name": "Alice",
            "email": "alice@example.com",
            "profile": {
                "age": 25,
                "city": "New York"
            }
        },
        {
            "id": 2,
            "name": "Bob",
            "email": "bob@example.com",
            "profile": {
                "age": 30,
                "city": "San Francisco"
            }
        }
    ],
    "metadata": {
        "total": 2,
        "page": 1
    }
}

path_builder = PathBuilder()

print("=== API测试期望的路径格式 ===")
print("期望: users.0.name (DOT风格应该使用点号连接数组索引)")
print("期望: metadata.total")

print("\n=== 当前生成的路径 (DOT风格) ===")
dot_paths = path_builder.build_paths(sample_data, style=PathStyle.DOT)
for path in sorted(dot_paths):
    if 'users' in path and ('name' in path or 'id' in path):
        print(f"  {path}")

print("\n=== 检查期望路径是否存在 ===")
expected_paths = ['users.0.name', 'users.0.id', 'metadata.total']
for expected in expected_paths:
    exists = expected in dot_paths
    print(f"  {expected} - {'✓' if exists else '✗'}")