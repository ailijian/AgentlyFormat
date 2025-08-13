#!/usr/bin/env python3
"""调试测试客户端"""

import sys
sys.path.insert(0, 'src')

from fastapi.testclient import TestClient
from agently_format.api.app import create_app

# 创建测试应用
app = create_app()
client = TestClient(app)

# 测试流解析端点
request_data = {
    "chunk": '{"name": "Alice", "age": 25}',
    "session_id": "stream-test-session",
    "is_final": True
}

print("发送请求到 /api/v1/parse/stream")
print(f"请求数据: {request_data}")

response = client.post("/api/v1/parse/stream", json=request_data)

print(f"响应状态码: {response.status_code}")
print(f"响应头: {response.headers}")
print(f"响应内容: {response.text}")

if response.status_code == 200:
    data = response.json()
    print(f"解析后的数据: {data}")
else:
    print(f"错误: {response.text}")