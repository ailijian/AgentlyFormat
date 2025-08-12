#!/usr/bin/env python3

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from agently_format.core.path_builder import PathBuilder, PathStyle

# 测试数据
data = {
    "user": {
        "profile": {
            "settings": ["option1", "option2"]
        }
    }
}

path_builder = PathBuilder()

print("=== 测试不同路径风格 ===")

# 点号风格
print("\n点号风格 (DOT):")
dot_paths = path_builder.build_paths(data, style=PathStyle.DOT)
for path in sorted(dot_paths):
    print(f"  {path}")
print(f"期望: user.profile.settings[0] - {'✓' if 'user.profile.settings[0]' in dot_paths else '✗'}")

# 斜杠风格
print("\n斜杠风格 (SLASH):")
slash_paths = path_builder.build_paths(data, style=PathStyle.SLASH)
for path in sorted(slash_paths):
    print(f"  {path}")
print(f"期望: user/profile/settings[0] - {'✓' if 'user/profile/settings[0]' in slash_paths else '✗'}")

# 括号风格
print("\n括号风格 (BRACKET):")
bracket_paths = path_builder.build_paths(data, style=PathStyle.BRACKET)
for path in sorted(bracket_paths):
    print(f"  {path}")
expected_bracket = "user['profile']['settings'][0]"
print(f"期望: {expected_bracket} - {'✓' if expected_bracket in bracket_paths else '✗'}")

# 混合风格
print("\n混合风格 (MIXED):")
mixed_paths = path_builder.build_paths(data, style=PathStyle.MIXED)
for path in sorted(mixed_paths):
    print(f"  {path}")
print(f"期望: user.profile.settings[0] - {'✓' if 'user.profile.settings[0]' in mixed_paths else '✗'}")

# 默认风格
print("\n默认风格:")
default_paths = path_builder.build_paths(data)
for path in sorted(default_paths):
    print(f"  {path}")
print(f"期望: user.profile.settings[0] - {'✓' if 'user.profile.settings[0]' in default_paths else '✗'}")