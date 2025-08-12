#!/usr/bin/env python3

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from agently_format.core.path_builder import PathBuilder, PathStyle

# 测试复杂嵌套结构
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

print("Generated paths:")
for path in sorted(paths):
    print(f"  {path}")

print("\nExpected paths:")
expected_deep_paths = [
    "api.v1.endpoints[0].path",
    "api.v1.endpoints[0].methods[0]",
    "api.v1.endpoints[0].auth.required",
    "api.v1.endpoints[0].auth.types[0]"
]

for path in expected_deep_paths:
    print(f"  {path} - {'✓' if path in paths else '✗'}")