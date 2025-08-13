# AgentlyFormat API 参考文档

AgentlyFormat v2.0.0 提供了完整的 REST API 和 WebSocket 接口，支持 JSON 流式解析、智能补全、Schema 验证等功能。

## 📋 API 概述

### 基础信息

- **基础 URL**: `http://localhost:8000`
- **API 版本**: v2.0.0
- **内容类型**: `application/json`
- **字符编码**: UTF-8
- **认证方式**: API Key（可选）

### 支持的功能

- ✅ JSON 流式解析
- ✅ 智能 JSON 补全
- ✅ Schema 验证
- ✅ 路径构建
- ✅ 模型适配器
- ✅ 会话管理
- ✅ 实时统计
- ✅ WebSocket 支持

## 🔧 快速开始

### 安装和启动

```bash
# 安装依赖
pip install agently-format==2.0.0

# 启动服务
python -m uvicorn agently_format.api.app:app --host 0.0.0.0 --port 8000 --reload
```

### 基础调用示例

```python
import aiohttp
import asyncio

async def test_api():
    async with aiohttp.ClientSession() as session:
        # 健康检查
        async with session.get("http://localhost:8000/health") as resp:
            print(await resp.json())
        
        # JSON 补全
        async with session.post(
            "http://localhost:8000/json/complete",
            json={
                "incomplete_json": '{"name": "John", "age":',
                "target_schema": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "age": {"type": "integer"}
                    }
                }
            }
        ) as resp:
            result = await resp.json()
            print(result)

# 运行示例
asyncio.run(test_api())
```

## 🌐 REST API 端点

### 1. 健康检查

#### `GET /health`

检查服务健康状态。

**请求:**
```http
GET /health HTTP/1.1
Host: localhost:8000
```

**响应:**
```json
{
  "status": "healthy",
  "version": "2.0.0",
  "timestamp": "2024-01-15T10:30:00Z",
  "uptime": 3600,
  "components": {
    "parser": "healthy",
    "completer": "healthy",
    "validator": "healthy",
    "database": "healthy"
  }
}
```

### 2. 系统统计

#### `GET /stats`

获取系统运行统计信息。

**请求:**
```http
GET /stats HTTP/1.1
Host: localhost:8000
```

**响应:**
```json
{
  "requests": {
    "total": 15420,
    "successful": 14890,
    "failed": 530,
    "rate_per_minute": 45.2
  },
  "performance": {
    "avg_response_time": 0.125,
    "p95_response_time": 0.350,
    "p99_response_time": 0.800
  },
  "resources": {
    "memory_usage": "256MB",
    "cpu_usage": "15%",
    "active_connections": 23
  },
  "features": {
    "json_completion": {
      "requests": 8500,
      "avg_time": 0.089
    },
    "streaming_parse": {
      "requests": 4200,
      "avg_time": 0.156
    },
    "schema_validation": {
      "requests": 2720,
      "avg_time": 0.045
    }
  }
}
```

### 3. JSON 补全

#### `POST /json/complete`

智能补全不完整的 JSON 数据。

**请求参数:**

| 参数 | 类型 | 必需 | 描述 |
|------|------|------|------|
| `incomplete_json` | string | ✅ | 不完整的 JSON 字符串 |
| `target_schema` | object | ❌ | 目标 JSON Schema |
| `completion_mode` | string | ❌ | 补全模式：`smart`、`minimal`、`strict` |
| `max_depth` | integer | ❌ | 最大嵌套深度（默认：10） |
| `preserve_order` | boolean | ❌ | 保持键顺序（默认：true） |

**请求示例:**
```json
{
  "incomplete_json": "{\"user\": {\"name\": \"Alice\", \"profile\": {\"age\":",
  "target_schema": {
    "type": "object",
    "properties": {
      "user": {
        "type": "object",
        "properties": {
          "name": {"type": "string"},
          "profile": {
            "type": "object",
            "properties": {
              "age": {"type": "integer"},
              "email": {"type": "string"}
            },
            "required": ["age"]
          }
        },
        "required": ["name", "profile"]
      }
    },
    "required": ["user"]
  },
  "completion_mode": "smart",
  "max_depth": 5
}
```

**响应:**
```json
{
  "success": true,
  "completed_json": "{\"user\": {\"name\": \"Alice\", \"profile\": {\"age\": 25, \"email\": \"alice@example.com\"}}}",
  "completion_info": {
    "added_fields": ["user.profile.email"],
    "completed_values": ["user.profile.age"],
    "validation_passed": true,
    "completion_time": 0.045
  },
  "metadata": {
    "original_size": 45,
    "completed_size": 89,
    "compression_ratio": 0.98
  }
}
```

### 4. 流式解析

#### `POST /parse/stream`

流式解析 JSON 数据，支持实时处理大型数据。

**请求参数:**

| 参数 | 类型 | 必需 | 描述 |
|------|------|------|------|
| `content` | string | ✅ | 要解析的内容 |
| `format_type` | string | ✅ | 格式类型：`json`、`yaml`、`xml` |
| `streaming` | boolean | ❌ | 是否启用流式解析（默认：true） |
| `schema` | object | ❌ | 验证 Schema |
| `options` | object | ❌ | 解析选项 |

**解析选项 (options):**

| 选项 | 类型 | 默认值 | 描述 |
|------|------|--------|------|
| `validate_schema` | boolean | false | 启用 Schema 验证 |
| `auto_complete` | boolean | false | 自动补全不完整数据 |
| `error_recovery` | boolean | true | 错误恢复模式 |
| `max_depth` | integer | 100 | 最大解析深度 |
| `timeout` | integer | 30 | 解析超时（秒） |

**请求示例:**
```json
{
  "content": "{\"users\": [{\"id\": 1, \"name\": \"Alice\"}, {\"id\": 2, \"name\": \"Bob\"}]}",
  "format_type": "json",
  "streaming": true,
  "schema": {
    "type": "object",
    "properties": {
      "users": {
        "type": "array",
        "items": {
          "type": "object",
          "properties": {
            "id": {"type": "integer"},
            "name": {"type": "string"}
          },
          "required": ["id", "name"]
        }
      }
    }
  },
  "options": {
    "validate_schema": true,
    "auto_complete": false,
    "error_recovery": true
  }
}
```

**响应:**
```json
{
  "success": true,
  "parsed_data": {
    "users": [
      {"id": 1, "name": "Alice"},
      {"id": 2, "name": "Bob"}
    ]
  },
  "parsing_info": {
    "format_detected": "json",
    "schema_valid": true,
    "parsing_time": 0.023,
    "data_size": 156,
    "elements_count": 2
  },
  "metadata": {
    "parser_version": "2.0.0",
    "timestamp": "2024-01-15T10:30:00Z"
  }
}
```

### 5. 路径构建

#### `POST /path/build`

构建和验证 JSON 路径表达式。

**请求参数:**

| 参数 | 类型 | 必需 | 描述 |
|------|------|------|------|
| `data` | object | ✅ | 源数据对象 |
| `path_expression` | string | ✅ | 路径表达式 |
| `operation` | string | ❌ | 操作类型：`get`、`set`、`delete` |
| `value` | any | ❌ | 设置的值（operation=set 时） |

**请求示例:**
```json
{
  "data": {
    "users": [
      {"id": 1, "profile": {"name": "Alice", "age": 25}},
      {"id": 2, "profile": {"name": "Bob", "age": 30}}
    ]
  },
  "path_expression": "users[*].profile.name",
  "operation": "get"
}
```

**响应:**
```json
{
  "success": true,
  "result": ["Alice", "Bob"],
  "path_info": {
    "expression": "users[*].profile.name",
    "resolved_paths": [
      "users[0].profile.name",
      "users[1].profile.name"
    ],
    "operation_type": "get",
    "matches_count": 2
  },
  "performance": {
    "execution_time": 0.012,
    "memory_usage": "2.1KB"
  }
}
```

### 6. 模型配置

#### `GET /model/config`

获取支持的模型配置信息。

**响应:**
```json
{
  "supported_models": {
    "openai": {
      "provider": "OpenAI",
      "models": ["gpt-3.5-turbo", "gpt-4", "gpt-4-turbo"],
      "features": ["chat", "completion", "streaming"],
      "max_tokens": 4096,
      "rate_limits": {
        "requests_per_minute": 3500,
        "tokens_per_minute": 90000
      }
    },
    "baidu": {
      "provider": "百度文心",
      "models": ["ernie-bot", "ernie-bot-turbo", "ernie-bot-4"],
      "features": ["chat", "completion"],
      "max_tokens": 2048,
      "rate_limits": {
        "requests_per_minute": 300,
        "tokens_per_minute": 10000
      }
    },
    "doubao": {
      "provider": "字节豆包",
      "models": ["doubao-pro-4k", "doubao-pro-32k", "doubao-lite-4k"],
      "features": ["chat", "completion", "streaming"],
      "max_tokens": 4096,
      "rate_limits": {
        "requests_per_minute": 1000,
        "tokens_per_minute": 50000
      }
    }
  },
  "default_config": {
    "provider": "openai",
    "model": "gpt-3.5-turbo",
    "temperature": 0.7,
    "max_tokens": 1000
  }
}
```

#### `POST /model/config`

更新模型配置。

**请求示例:**
```json
{
  "provider": "openai",
  "model": "gpt-4",
  "api_key": "sk-...",
  "temperature": 0.5,
  "max_tokens": 2000,
  "stream": true
}
```

### 7. 聊天接口

#### `POST /chat`

与配置的语言模型进行对话。

**请求参数:**

| 参数 | 类型 | 必需 | 描述 |
|------|------|------|------|
| `messages` | array | ✅ | 对话消息列表 |
| `model` | string | ❌ | 使用的模型名称 |
| `stream` | boolean | ❌ | 是否流式响应 |
| `temperature` | number | ❌ | 温度参数（0-1） |
| `max_tokens` | integer | ❌ | 最大生成令牌数 |

**请求示例:**
```json
{
  "messages": [
    {"role": "system", "content": "你是一个 JSON 数据处理专家。"},
    {"role": "user", "content": "请帮我补全这个 JSON: {\"name\": \"Alice\", \"age\":"}
  ],
  "model": "gpt-3.5-turbo",
  "stream": false,
  "temperature": 0.3,
  "max_tokens": 500
}
```

**响应:**
```json
{
  "success": true,
  "response": {
    "id": "chatcmpl-8k2j3h4k5l6m7n8o9p",
    "object": "chat.completion",
    "created": 1705312200,
    "model": "gpt-3.5-turbo",
    "choices": [
      {
        "index": 0,
        "message": {
          "role": "assistant",
          "content": "这个 JSON 可以补全为：\n\n```json\n{\"name\": \"Alice\", \"age\": 25}\n```\n\n我添加了一个合理的年龄值。如果你有特定的年龄要求，请告诉我。"
        },
        "finish_reason": "stop"
      }
    ],
    "usage": {
      "prompt_tokens": 45,
      "completion_tokens": 38,
      "total_tokens": 83
    }
  },
  "metadata": {
    "processing_time": 1.234,
    "model_provider": "openai"
  }
}
```

### 8. 会话管理

#### `POST /sessions`

创建新的解析会话。

**请求示例:**
```json
{
  "session_config": {
    "timeout": 3600,
    "max_requests": 1000,
    "enable_caching": true
  },
  "metadata": {
    "user_id": "user123",
    "project": "data-processing"
  }
}
```

**响应:**
```json
{
  "session_id": "sess_8k2j3h4k5l6m7n8o9p",
  "created_at": "2024-01-15T10:30:00Z",
  "expires_at": "2024-01-15T11:30:00Z",
  "config": {
    "timeout": 3600,
    "max_requests": 1000,
    "enable_caching": true
  }
}
```

#### `GET /sessions/{session_id}`

获取会话信息。

**响应:**
```json
{
  "session_id": "sess_8k2j3h4k5l6m7n8o9p",
  "status": "active",
  "created_at": "2024-01-15T10:30:00Z",
  "last_activity": "2024-01-15T10:45:00Z",
  "requests_count": 45,
  "remaining_requests": 955,
  "statistics": {
    "total_data_processed": "2.5MB",
    "avg_response_time": 0.156,
    "success_rate": 0.978
  }
}
```

#### `DELETE /sessions/{session_id}`

删除会话。

**响应:**
```json
{
  "success": true,
  "message": "会话已成功删除",
  "session_id": "sess_8k2j3h4k5l6m7n8o9p"
}
```

## 🔌 WebSocket API

### 连接端点

**WebSocket URL**: `ws://localhost:8000/ws`

### 消息格式

所有 WebSocket 消息都使用 JSON 格式：

```json
{
  "type": "request|response|event|error",
  "id": "unique_message_id",
  "data": {},
  "timestamp": "2024-01-15T10:30:00Z"
}
```

### 流式解析

**发送请求:**
```json
{
  "type": "request",
  "id": "req_001",
  "action": "parse_stream",
  "data": {
    "content": "{\"large_data\": [...]",
    "format_type": "json",
    "chunk_size": 1024
  }
}
```

**接收响应:**
```json
{
  "type": "event",
  "id": "req_001",
  "event_type": "parse_progress",
  "data": {
    "progress": 0.25,
    "parsed_elements": 150,
    "current_chunk": "chunk_data..."
  },
  "timestamp": "2024-01-15T10:30:01Z"
}
```

**完成通知:**
```json
{
  "type": "response",
  "id": "req_001",
  "data": {
    "success": true,
    "result": {...},
    "total_time": 2.345,
    "elements_processed": 600
  },
  "timestamp": "2024-01-15T10:30:03Z"
}
```

### 实时监控

**订阅统计信息:**
```json
{
  "type": "request",
  "id": "monitor_001",
  "action": "subscribe_stats",
  "data": {
    "interval": 5,
    "metrics": ["requests", "performance", "resources"]
  }
}
```

**接收统计更新:**
```json
{
  "type": "event",
  "id": "monitor_001",
  "event_type": "stats_update",
  "data": {
    "requests_per_second": 12.5,
    "avg_response_time": 0.145,
    "memory_usage": "278MB",
    "active_connections": 34
  },
  "timestamp": "2024-01-15T10:30:05Z"
}
```

## 📊 错误处理

### HTTP 状态码

| 状态码 | 含义 | 描述 |
|--------|------|------|
| 200 | OK | 请求成功 |
| 201 | Created | 资源创建成功 |
| 400 | Bad Request | 请求参数错误 |
| 401 | Unauthorized | 认证失败 |
| 403 | Forbidden | 权限不足 |
| 404 | Not Found | 资源不存在 |
| 422 | Unprocessable Entity | 数据验证失败 |
| 429 | Too Many Requests | 请求频率超限 |
| 500 | Internal Server Error | 服务器内部错误 |
| 503 | Service Unavailable | 服务不可用 |

### 错误响应格式

```json
{
  "success": false,
  "error": {
    "code": "PARSE_ERROR",
    "message": "JSON 解析失败：意外的字符 '}' 在位置 45",
    "details": {
      "position": 45,
      "line": 3,
      "column": 12,
      "context": "...\"name\": \"Alice\"}..."
    },
    "suggestions": [
      "检查 JSON 语法是否正确",
      "确保所有括号和引号匹配",
      "使用 JSON 验证工具检查格式"
    ]
  },
  "request_id": "req_8k2j3h4k5l6m7n8o9p",
  "timestamp": "2024-01-15T10:30:00Z"
}
```

### 常见错误代码

| 错误代码 | 描述 | 解决方案 |
|----------|------|----------|
| `PARSE_ERROR` | 解析失败 | 检查数据格式 |
| `VALIDATION_ERROR` | Schema 验证失败 | 修正数据结构 |
| `COMPLETION_ERROR` | 补全失败 | 提供更多上下文 |
| `TIMEOUT_ERROR` | 请求超时 | 减少数据量或增加超时时间 |
| `RATE_LIMIT_ERROR` | 频率限制 | 降低请求频率 |
| `INVALID_SCHEMA` | Schema 无效 | 检查 Schema 格式 |
| `UNSUPPORTED_FORMAT` | 不支持的格式 | 使用支持的格式 |
| `MEMORY_LIMIT_ERROR` | 内存不足 | 减少数据量或分批处理 |

## 🔐 认证和安全

### API Key 认证

```http
POST /json/complete HTTP/1.1
Host: localhost:8000
Content-Type: application/json
Authorization: Bearer your_api_key_here

{
  "incomplete_json": "..."
}
```

### 请求签名（高级）

```python
import hmac
import hashlib
import time

def generate_signature(api_secret, method, path, body, timestamp):
    message = f"{method}\n{path}\n{body}\n{timestamp}"
    signature = hmac.new(
        api_secret.encode(),
        message.encode(),
        hashlib.sha256
    ).hexdigest()
    return signature

# 使用示例
timestamp = str(int(time.time()))
signature = generate_signature(
    api_secret="your_secret",
    method="POST",
    path="/json/complete",
    body=json.dumps(request_data),
    timestamp=timestamp
)

headers = {
    "X-API-Key": "your_api_key",
    "X-Timestamp": timestamp,
    "X-Signature": signature
}
```

## 📈 性能和限制

### 请求限制

| 限制类型 | 免费版 | 专业版 | 企业版 |
|----------|--------|--------|---------|
| 每分钟请求数 | 100 | 1000 | 10000 |
| 每日请求数 | 10000 | 100000 | 无限制 |
| 最大数据大小 | 1MB | 10MB | 100MB |
| 并发连接数 | 10 | 100 | 1000 |
| WebSocket 连接 | 5 | 50 | 500 |

### 性能基准

| 操作 | 平均响应时间 | P95 响应时间 | 吞吐量 |
|------|-------------|-------------|--------|
| JSON 补全 | 89ms | 250ms | 500 req/s |
| 流式解析 | 156ms | 400ms | 300 req/s |
| Schema 验证 | 45ms | 120ms | 800 req/s |
| 路径构建 | 12ms | 35ms | 1200 req/s |

### 优化建议

1. **批量处理**: 合并多个小请求
2. **缓存结果**: 启用响应缓存
3. **压缩传输**: 使用 gzip 压缩
4. **连接复用**: 使用 HTTP/2 或连接池
5. **异步处理**: 使用 WebSocket 进行长时间操作

## 🧪 测试和调试

### 使用 curl 测试

```bash
# 健康检查
curl -X GET http://localhost:8000/health

# JSON 补全
curl -X POST http://localhost:8000/json/complete \
  -H "Content-Type: application/json" \
  -d '{
    "incomplete_json": "{\"name\": \"Alice\", \"age\":",
    "completion_mode": "smart"
  }'

# 流式解析
curl -X POST http://localhost:8000/parse/stream \
  -H "Content-Type: application/json" \
  -d '{
    "content": "{\"users\": [{\"id\": 1}]}",
    "format_type": "json",
    "options": {"validate_schema": true}
  }'
```

### Python 客户端示例

```python
import aiohttp
import asyncio
import json

class AgentlyFormatClient:
    def __init__(self, base_url="http://localhost:8000", api_key=None):
        self.base_url = base_url
        self.api_key = api_key
        self.session = None
    
    async def __aenter__(self):
        headers = {}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        
        self.session = aiohttp.ClientSession(
            headers=headers,
            timeout=aiohttp.ClientTimeout(total=30)
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def complete_json(self, incomplete_json, schema=None, mode="smart"):
        """JSON 智能补全"""
        data = {
            "incomplete_json": incomplete_json,
            "completion_mode": mode
        }
        if schema:
            data["target_schema"] = schema
        
        async with self.session.post(
            f"{self.base_url}/json/complete",
            json=data
        ) as resp:
            return await resp.json()
    
    async def parse_stream(self, content, format_type="json", **options):
        """流式解析"""
        data = {
            "content": content,
            "format_type": format_type,
            "streaming": True,
            "options": options
        }
        
        async with self.session.post(
            f"{self.base_url}/parse/stream",
            json=data
        ) as resp:
            return await resp.json()
    
    async def get_stats(self):
        """获取系统统计"""
        async with self.session.get(f"{self.base_url}/stats") as resp:
            return await resp.json()

# 使用示例
async def main():
    async with AgentlyFormatClient() as client:
        # JSON 补全
        result = await client.complete_json(
            '{"name": "Alice", "age":',
            schema={
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "age": {"type": "integer"}
                }
            }
        )
        print("补全结果:", result)
        
        # 流式解析
        parse_result = await client.parse_stream(
            '{"users": [{"id": 1, "name": "Alice"}]}',
            validate_schema=True
        )
        print("解析结果:", parse_result)
        
        # 系统统计
        stats = await client.get_stats()
        print("系统统计:", stats)

if __name__ == "__main__":
    asyncio.run(main())
```

### WebSocket 客户端示例

```python
import websockets
import json
import asyncio

async def websocket_client():
    uri = "ws://localhost:8000/ws"
    
    async with websockets.connect(uri) as websocket:
        # 发送解析请求
        request = {
            "type": "request",
            "id": "parse_001",
            "action": "parse_stream",
            "data": {
                "content": '{"large_array": [' + ','.join([f'{{"id": {i}}}' for i in range(1000)]) + ']}',
                "format_type": "json",
                "chunk_size": 1024
            }
        }
        
        await websocket.send(json.dumps(request))
        print("已发送解析请求")
        
        # 接收响应
        async for message in websocket:
            data = json.loads(message)
            
            if data["type"] == "event":
                if data["event_type"] == "parse_progress":
                    progress = data["data"]["progress"]
                    print(f"解析进度: {progress:.1%}")
            
            elif data["type"] == "response":
                if data["data"]["success"]:
                    print("解析完成!")
                    print(f"处理时间: {data['data']['total_time']:.2f}s")
                    print(f"元素数量: {data['data']['elements_processed']}")
                else:
                    print(f"解析失败: {data['data']['error']}")
                break
            
            elif data["type"] == "error":
                print(f"错误: {data['data']['message']}")
                break

# 运行 WebSocket 客户端
asyncio.run(websocket_client())
```

## 📚 SDK 和工具

### 官方 Python SDK

```bash
pip install agently-format-sdk
```

```python
from agently_format_sdk import AgentlyFormatClient

# 初始化客户端
client = AgentlyFormatClient(
    base_url="http://localhost:8000",
    api_key="your_api_key"
)

# 同步调用
result = client.complete_json('{"name": "Alice", "age":')
print(result.completed_json)

# 异步调用
result = await client.complete_json_async('{"name": "Alice", "age":')
print(result.completed_json)
```

### CLI 工具

```bash
# 安装 CLI
pip install agently-format-cli

# JSON 补全
agently-format complete --input '{"name": "Alice", "age":' --output result.json

# 流式解析
agently-format parse --file large_data.json --format json --validate

# 批量处理
agently-format batch --input-dir ./data --output-dir ./results --format json
```

## 🔗 相关资源

- **项目主页**: [GitHub Repository](https://github.com/AgentlyFormat/AgentlyFormat)
- **完整文档**: [Documentation Site](https://docs.agentlyformat.com)
- **示例代码**: [Examples Repository](https://github.com/AgentlyFormat/examples)
- **社区讨论**: [GitHub Discussions](https://github.com/AgentlyFormat/AgentlyFormat/discussions)
- **问题反馈**: [GitHub Issues](https://github.com/AgentlyFormat/AgentlyFormat/issues)
- **更新日志**: [CHANGELOG.md](../CHANGELOG/v2.0.0.md)
- **迁移指南**: [MIGRATION.md](MIGRATION.md)

---

**AgentlyFormat v2.0.0 - 让 JSON 处理更智能、更高效！**