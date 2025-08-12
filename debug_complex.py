#!/usr/bin/env python3

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from agently_format.core.path_builder import PathBuilder, PathStyle

# 复杂嵌套数据
complex_data = {
    "api": {
        "v1": {
            "endpoints": [
                {
                    "path": "/users",
                    "methods": ["GET", "POST"],
                    "auth": {
                        "required": True,
                        "types": ["bearer", "api_key"]
                    }
                }
            ]
        }
    }
}

path_builder = PathBuilder()
paths = path_builder.build_paths(complex_data)

print("=== 生成的所有路径 ===")
for path in sorted(paths):
    print(f"  {path}")

print("\n=== 检查期望的路径 ===")
expected_deep_paths = [
    "api.v1.endpoints[0].path",
    "api.v1.endpoints[0].methods[0]",
    "api.v1.endpoints[0].auth.required",
    "api.v1.endpoints[0].auth.types[0]"
]

for path in expected_deep_paths:
    exists = path in paths
    print(f"  {path} - {'✓' if exists else '✗'}")
    if not exists:
        # 查找相似的路径
        similar = [p for p in paths if 'methods' in p and '[0]' in p]
        if similar:
            print(f"    相似路径: {similar}")