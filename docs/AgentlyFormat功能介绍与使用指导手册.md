# AgentlyFormat 功能介绍与使用指导手册

## 📋 目录

1. [项目概述](#项目概述)
2. [核心功能](#核心功能)
3. [快速开始](#快速开始)
4. [详细功能介绍](#详细功能介绍)
5. [API文档](#api文档)
6. [配置指南](#配置指南)
7. [使用示例](#使用示例)
8. [性能优化](#性能优化)
9. [故障排除](#故障排除)
10. [最佳实践](#最佳实践)

---

## 📖 项目概述

### 什么是 AgentlyFormat？

AgentlyFormat 是一个专注于大模型格式化输出结果的Python库，主要解决大语言模型在生成JSON格式数据时遇到的各种问题。该项目基于Agently强大的格式化输出能力构建，主打轻量化和高性能。

### 核心问题解决

- **JSON输出不完整**: 大模型经常生成不完整的JSON数据
- **流式输出处理**: 实时处理流式JSON数据流
- **格式不一致**: 不同模型输出格式差异较大
- **结构复杂**: 复杂嵌套JSON结构难以处理
- **性能瓶颈**: 大文件处理性能问题

### 版本信息

- **当前版本**: v2.0.0
- **Python要求**: ≥ 3.8
- **许可证**: Apache-2.0
- **维护状态**: 积极维护

---

## 🚀 核心功能

### 1. 智能JSON补全
- 自动补全不完整的JSON字符串
- 支持多种补全策略（智能、保守、激进）
- 双阶段补全：词法分析 → 语法修复
- 智能类型推断和错误修复

### 2. 流式JSON解析
- 实时处理流式JSON数据
- 跨块缓冲机制，支持大文件处理
- 智能边界检测，避免数据截断
- 事件驱动的解析进度通知

### 3. 数据路径构建
- 自动提取JSON数据的所有路径
- 支持多种路径格式（点号、斜杠、括号）
- 路径格式转换和验证
- 通过路径快速访问数据

### 4. Schema验证
- 增量Schema验证机制
- 自定义验证规则支持
- 类型兼容性检查
- 修复建议和错误定位

### 5. 差分引擎
- 结构化数据差分算法
- 增量更新和版本追踪
- 事件去重和合并优化
- 冲突检测和解决

### 6. 多模型适配器
- 支持主流大模型API（OpenAI、豆包、文心、千问、DeepSeek、Kimi）
- 统一的接口抽象
- 自动重试和错误处理
- 流式和非流式响应支持

---

## ⚡ 快速开始

### 安装

```bash
# 基础安装
pip install AgentlyFormat

# 开发环境安装
pip install -e ".[dev]"

# 完整功能安装
pip install -e ".[dev,docs]"
```

### 基础使用

```python
from agently_format.core.json_completer import JSONCompleter
from agently_format.core.streaming_parser import StreamingParser
from agently_format.core.path_builder import PathBuilder

# JSON补全
completer = JSONCompleter()
result = completer.complete('{"name": "Alice", "age": 25')
print(result.completed_json)

# 流式解析
parser = StreamingParser()
session_id = parser.create_session()
result = await parser.parse_chunk(session_id, '{"users": [')

# 路径构建
builder = PathBuilder()
data = {"user": {"name": "Alice", "profile": {"age": 25}}}
paths = builder.extract_parsing_key_orders(data)
print(paths)  # ['user.name', 'user.profile.age']
```

### 启动API服务

```bash
# 启动开发服务器
python -m agently_format.api.app

# 或使用uvicorn
uvicorn agently_format.api.app:app --host 0.0.0.0 --port 8000 --reload
```

---

## 📚 详细功能介绍

### JSON智能补全器 (JSONCompleter)

#### 功能特性
- **多策略补全**: 支持智能、保守、激进三种补全策略
- **双阶段处理**: 词法分析和语法修复的两阶段处理
- **RepairTrace机制**: 完整的修复路径追踪和回滚
- **类型推断**: 基于上下文的智能类型推断
- **增量修复**: 支持部分内容的增量补全

#### 使用方法

```python
from agently_format.core.json_completer import JSONCompleter, CompletionStrategy

completer = JSONCompleter()

# 基础补全
incomplete_json = '{"name": "Alice", "age": 25'
result = completer.complete(incomplete_json)

# 指定策略补全
result = completer.complete(
    incomplete_json, 
    strategy=CompletionStrategy.CONSERVATIVE
)

# 检查结果
if result.is_valid:
    print(f"补全成功: {result.completed_json}")
    print(f"置信度: {result.confidence}")
else:
    print(f"补全失败: {result.error_message}")
```

#### 补全策略说明

| 策略 | 描述 | 适用场景 |
|------|------|----------|
| SMART | 智能补全，平衡准确性和完整性 | 大多数场景 |
| CONSERVATIVE | 保守补全，优先保证准确性 | 关键数据处理 |
| AGGRESSIVE | 激进补全，尽可能补全更多内容 | 数据探索阶段 |

### 流式JSON解析器 (StreamingParser)

#### 功能特性
- **跨块缓冲**: 环形缓冲区支持大文件流式处理
- **智能边界检测**: 括号/引号平衡统计，避免数据截断
- **软裁剪逻辑**: 智能识别安全切分点
- **事件驱动**: 实时解析进度和状态通知
- **会话管理**: 支持多会话并发处理

#### 使用方法

```python
import asyncio
from agently_format.core.streaming_parser import StreamingParser

async def streaming_parse_example():
    parser = StreamingParser()
    session_id = parser.create_session()
    
    # 模拟分块数据
    chunks = [
        '{"users": [',
        '{"id": 1, "name": "Alice"},',
        '{"id": 2, "name": "Bob"}',
        '], "total": 2}'
    ]
    
    # 逐块解析
    for i, chunk in enumerate(chunks):
        is_final = (i == len(chunks) - 1)
        result = await parser.parse_chunk(
            session_id=session_id,
            chunk=chunk
        )
        
        # 获取当前解析状态
        state = parser.parsing_states[session_id]
        print(f"处理进度: {state.processed_chunks}/{state.total_chunks}")
    
    # 获取最终结果
    final_data = parser.get_current_data(session_id)
    print(f"解析结果: {final_data}")
    
    # 清理会话
    parser.cleanup_session(session_id)

# 运行示例
asyncio.run(streaming_parse_example())
```

#### 事件监听

```python
from agently_format.core.event_system import get_global_emitter, EventType

# 获取全局事件发射器
emitter = get_global_emitter()

# 事件处理器
async def on_parse_progress(event):
    print(f"解析进度: {event.data}")

async def on_parse_error(event):
    print(f"解析错误: {event.data}")

# 注册事件监听器
emitter.on(EventType.DELTA, on_parse_progress)
emitter.on(EventType.ERROR, on_parse_error)
```

### 数据路径构建器 (PathBuilder)

#### 功能特性
- **多格式支持**: 点号、斜杠、括号等多种路径格式
- **路径提取**: 自动提取JSON数据的所有路径
- **格式转换**: 不同路径格式之间的转换
- **值访问**: 通过路径快速访问数据值
- **路径验证**: 路径有效性检查

#### 使用方法

```python
from agently_format.core.path_builder import PathBuilder, PathStyle

builder = PathBuilder()

# 示例数据
data = {
    "api": {
        "version": "v1",
        "endpoints": [
            {
                "path": "/users",
                "methods": ["GET", "POST"]
            }
        ]
    }
}

# 提取所有路径
paths = builder.extract_parsing_key_orders(data)
print("所有路径:")
for path in paths:
    print(f"  {path}")

# 通过路径获取值
success, value = builder.get_value_at_path(data, "api.version")
if success:
    print(f"api.version = {value}")

# 路径格式转换
dot_path = "api.endpoints[0].methods"
slash_path = builder.convert_path(dot_path, PathStyle.SLASH)
bracket_path = builder.convert_path(dot_path, PathStyle.BRACKET)

print(f"点号格式: {dot_path}")
print(f"斜杠格式: {slash_path}")
print(f"括号格式: {bracket_path}")
```

#### 路径格式说明

| 格式 | 示例 | 描述 |
|------|------|------|
| DOT | `user.profile.age` | 点号分隔，最常用 |
| SLASH | `user/profile/age` | 斜杠分隔，类似文件路径 |
| BRACKET | `user[profile][age]` | 括号格式，支持特殊字符 |

### Schema验证器 (SchemaValidator)

#### 功能特性
- **增量验证**: 逐路径验证机制，支持实时验证
- **自定义规则**: 支持用户自定义验证逻辑
- **类型检查**: 严格的类型匹配和转换
- **错误定位**: 精确的错误位置和修复建议
- **缓存优化**: 智能缓存常见修复方案

#### 使用方法

```python
from agently_format.core.schemas import SchemaValidator
from pydantic import BaseModel
from typing import List, Optional

# 定义Schema
class UserProfile(BaseModel):
    name: str
    age: int
    email: Optional[str] = None
    tags: List[str] = []

class UserData(BaseModel):
    users: List[UserProfile]
    total: int

# 创建验证器
validator = SchemaValidator(UserData)

# 验证数据
data = {
    "users": [
        {"name": "Alice", "age": 25, "email": "alice@example.com"},
        {"name": "Bob", "age": "30"}  # age类型错误
    ],
    "total": 2
}

result = validator.validate(data)
if result.is_valid:
    print("验证通过")
else:
    print("验证失败:")
    for error in result.errors:
        print(f"  {error.path}: {error.message}")
        if error.suggestion:
            print(f"    建议: {error.suggestion}")
```

### 差分引擎 (DiffEngine)

#### 功能特性
- **结构化差分**: dict/list aware的智能差分算法
- **增量更新**: 最小化数据传输的增量更新
- **版本追踪**: 完整的数据变更历史记录
- **事件优化**: 事件去重和合并优化
- **冲突解决**: 智能的数据冲突检测和解决

#### 使用方法

```python
from agently_format.core.diff_engine import DiffEngine

engine = DiffEngine()

# 原始数据
old_data = {
    "users": [
        {"id": 1, "name": "Alice", "age": 25},
        {"id": 2, "name": "Bob", "age": 30}
    ],
    "total": 2
}

# 更新后数据
new_data = {
    "users": [
        {"id": 1, "name": "Alice", "age": 26},  # 年龄变更
        {"id": 2, "name": "Bob", "age": 30},
        {"id": 3, "name": "Charlie", "age": 28}  # 新增用户
    ],
    "total": 3
}

# 计算差分
diff_result = engine.compute_diff(old_data, new_data)

print("数据变更:")
for change in diff_result.changes:
    print(f"  {change.operation}: {change.path} = {change.new_value}")

# 应用差分
patched_data = engine.apply_diff(old_data, diff_result)
print(f"应用差分后: {patched_data == new_data}")  # True
```

---

## 🌐 API文档

### REST API接口

#### 基础信息
- **基础URL**: `http://localhost:8000`
- **API版本**: v1
- **内容类型**: `application/json`
- **认证方式**: Bearer Token（可选）

#### 核心接口

##### 1. JSON补全接口

```http
POST /api/v1/json/complete
Content-Type: application/json

{
  "content": "{\"name\": \"Alice\", \"age\": 25",
  "strategy": "smart"
}
```

**响应示例**:
```json
{
  "success": true,
  "data": {
    "completed_json": "{\"name\": \"Alice\", \"age\": 25}",
    "is_valid": true,
    "confidence": 0.95,
    "completion_applied": true
  }
}
```

##### 2. 流式解析接口

```http
POST /api/v1/parse/stream
Content-Type: application/json

{
  "session_id": "session_123",
  "chunk": "{\"users\": [",
  "is_final": false
}
```

**响应示例**:
```json
{
  "success": true,
  "data": {
    "session_id": "session_123",
    "parsed_data": {"users": []},
    "is_complete": false,
    "progress": 0.25
  }
}
```

##### 3. 路径构建接口

```http
POST /api/v1/path/build
Content-Type: application/json

{
  "data": {"user": {"name": "Alice"}},
  "style": "dot"
}
```

**响应示例**:
```json
{
  "success": true,
  "data": {
    "paths": ["user.name"],
    "total_count": 1,
    "style": "dot"
  }
}
```

##### 4. 模型聊天接口

```http
POST /api/v1/chat
Content-Type: application/json

{
  "model": "openai",
  "messages": [
    {"role": "user", "content": "请生成一个用户信息的JSON"}
  ],
  "stream": false
}
```

##### 5. 系统统计接口

```http
GET /api/v1/stats
```

**响应示例**:
```json
{
  "success": true,
  "data": {
    "total_sessions": 156,
    "active_sessions": 12,
    "total_events": 2847,
    "uptime": 86400,
    "memory_usage": "45.2MB"
  }
}
```

##### 6. 健康检查接口

```http
GET /health
```

**响应示例**:
```json
{
  "status": "healthy",
  "version": "2.0.0",
  "timestamp": "2024-12-01T10:30:00Z",
  "checks": {
    "database": "ok",
    "memory": "ok",
    "disk": "ok"
  }
}
```

### WebSocket接口

#### 连接地址
```
ws://localhost:8000/ws
```

#### 消息格式

**发送消息**:
```json
{
  "type": "parse",
  "session_id": "session_123",
  "data": "{\"partial\": \"json\"}"
}
```

**接收消息**:
```json
{
  "type": "parse_result",
  "session_id": "session_123",
  "data": {
    "parsed_data": {"partial": "json"},
    "is_complete": false,
    "progress": 0.5
  }
}
```

#### 使用示例

```python
import asyncio
import websockets
import json

async def websocket_client():
    uri = "ws://localhost:8000/ws"
    async with websockets.connect(uri) as websocket:
        # 发送解析请求
        message = {
            "type": "parse",
            "session_id": "demo_session",
            "data": '{"users": ['
        }
        await websocket.send(json.dumps(message))
        
        # 接收响应
        response = await websocket.recv()
        result = json.loads(response)
        print(f"实时响应: {result}")

asyncio.run(websocket_client())
```

---

## ⚙️ 配置指南

### 环境变量配置

```bash
# API服务配置
AGENTLY_FORMAT_HOST=0.0.0.0
AGENTLY_FORMAT_PORT=8000
AGENTLY_FORMAT_DEBUG=false

# 模型API密钥
OPENAI_API_KEY=your-openai-key
DOUBAO_API_KEY=your-doubao-key
WENXIN_API_KEY=your-wenxin-key
WENXIN_SECRET_KEY=your-wenxin-secret
QIANWEN_API_KEY=your-qianwen-key
DEEPSEEK_API_KEY=your-deepseek-key
KIMI_API_KEY=your-kimi-key

# 性能配置
MAX_CHUNK_SIZE=1048576  # 1MB
SESSION_TTL=3600       # 1小时
MAX_SESSIONS=1000

# 安全配置
RATE_LIMIT_ENABLED=true
ACCESS_TOKEN=your-access-token
CORS_ORIGINS=*
```

### 配置文件 (config.yaml)

```yaml
# 服务器配置
server:
  host: "0.0.0.0"
  port: 8000
  debug: false
  workers: 4

# 处理配置
processing:
  max_chunk_size: 1048576  # 1MB
  session_ttl: 3600       # 1小时
  max_sessions: 1000
  buffer_size: 8192
  enable_compression: true

# 模型配置
models:
  openai:
    api_key: "${OPENAI_API_KEY}"
    base_url: "https://api.openai.com/v1"
    timeout: 30
    max_retries: 3
  
  doubao:
    api_key: "${DOUBAO_API_KEY}"
    base_url: "https://ark.cn-beijing.volces.com/api/v3"
    timeout: 30
    max_retries: 3
  
  wenxin:
    api_key: "${WENXIN_API_KEY}"
    api_secret: "${WENXIN_SECRET_KEY}"
    timeout: 30
    max_retries: 3

# 安全配置
security:
  rate_limit_enabled: true
  rate_limit_requests: 100
  rate_limit_window: 60  # 秒
  access_token: "${ACCESS_TOKEN}"
  cors_origins:
    - "*"
  cors_methods:
    - "GET"
    - "POST"
    - "PUT"
    - "DELETE"

# 监控配置
monitoring:
  metrics_enabled: true
  health_check_enabled: true
  log_level: "INFO"
  log_format: "json"
  
# 缓存配置
cache:
  enabled: true
  ttl: 300  # 5分钟
  max_size: 1000
```

### 程序化配置

```python
from agently_format.api.config import Settings
from agently_format.core.streaming_parser import StreamingParser
from agently_format.core.json_completer import JSONCompleter

# 创建自定义配置
settings = Settings(
    host="0.0.0.0",
    port=8000,
    debug=False,
    max_chunk_size=1024*1024,  # 1MB
    session_ttl=3600,  # 1小时
    rate_limit_enabled=True
)

# 使用配置创建组件
parser = StreamingParser(
    max_chunk_size=settings.max_chunk_size,
    session_ttl=settings.session_ttl
)

completer = JSONCompleter(
    default_strategy="smart",
    enable_cache=True
)
```

---

## 💡 使用示例

### 示例1: 处理大模型流式输出

```python
import asyncio
from agently_format.adapters.openai_adapter import OpenAIAdapter
from agently_format.core.streaming_parser import StreamingParser
from agently_format.core.json_completer import JSONCompleter

async def process_llm_stream():
    # 创建模型适配器
    adapter = OpenAIAdapter(api_key="your-api-key")
    
    # 创建流式解析器
    parser = StreamingParser()
    session_id = parser.create_session()
    
    # 创建JSON补全器
    completer = JSONCompleter()
    
    # 构建聊天消息
    messages = [
        {
            "role": "user", 
            "content": "请生成5个用户的信息，包含姓名、年龄、邮箱，以JSON格式返回"
        }
    ]
    
    print("开始处理大模型流式输出...")
    
    # 流式调用模型
    async for chunk in adapter.chat_completion_stream(
        messages=messages,
        temperature=0.7
    ):
        if chunk.content:
            # 实时解析JSON块
            result = await parser.parse_chunk(
                session_id=session_id,
                chunk=chunk.content
            )
            
            # 获取当前解析状态
            state = parser.parsing_states[session_id]
            if state.current_data:
                print(f"当前解析数据: {state.current_data}")
    
    # 获取最终数据
    final_data = parser.get_current_data(session_id)
    
    # 如果数据不完整，进行补全
    if not final_data:
        raw_content = parser.get_raw_content(session_id)
        completion_result = completer.complete(raw_content)
        
        if completion_result.is_valid:
            print(f"补全后的JSON: {completion_result.completed_json}")
        else:
            print(f"补全失败: {completion_result.error_message}")
    else:
        print(f"解析成功: {final_data}")
    
    # 清理资源
    parser.cleanup_session(session_id)
    await adapter.close()

# 运行示例
asyncio.run(process_llm_stream())
```

### 示例2: 批量数据处理

```python
import asyncio
import json
from typing import List, Dict, Any
from agently_format.core.json_completer import JSONCompleter
from agently_format.core.path_builder import PathBuilder
from agently_format.core.schemas import SchemaValidator
from pydantic import BaseModel

class UserInfo(BaseModel):
    name: str
    age: int
    email: str
    department: str

class BatchProcessor:
    def __init__(self):
        self.completer = JSONCompleter()
        self.path_builder = PathBuilder()
        self.validator = SchemaValidator(UserInfo)
    
    async def process_batch(self, incomplete_jsons: List[str]) -> List[Dict[str, Any]]:
        """批量处理不完整的JSON数据"""
        results = []
        
        for i, incomplete_json in enumerate(incomplete_jsons):
            print(f"处理第 {i+1}/{len(incomplete_jsons)} 条数据...")
            
            # 1. JSON补全
            completion_result = self.completer.complete(incomplete_json)
            
            if not completion_result.is_valid:
                results.append({
                    "index": i,
                    "status": "completion_failed",
                    "error": completion_result.error_message,
                    "original": incomplete_json
                })
                continue
            
            # 2. 解析JSON
            try:
                data = json.loads(completion_result.completed_json)
            except json.JSONDecodeError as e:
                results.append({
                    "index": i,
                    "status": "parse_failed",
                    "error": str(e),
                    "completed_json": completion_result.completed_json
                })
                continue
            
            # 3. 提取数据路径
            paths = self.path_builder.extract_parsing_key_orders(data)
            
            # 4. Schema验证
            validation_result = self.validator.validate(data)
            
            # 5. 构建结果
            result = {
                "index": i,
                "status": "success" if validation_result.is_valid else "validation_failed",
                "original": incomplete_json,
                "completed": completion_result.completed_json,
                "parsed_data": data,
                "paths": paths,
                "confidence": completion_result.confidence
            }
            
            if not validation_result.is_valid:
                result["validation_errors"] = [
                    {"path": err.path, "message": err.message}
                    for err in validation_result.errors
                ]
            
            results.append(result)
        
        return results
    
    def generate_report(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """生成处理报告"""
        total = len(results)
        success = sum(1 for r in results if r["status"] == "success")
        completion_failed = sum(1 for r in results if r["status"] == "completion_failed")
        parse_failed = sum(1 for r in results if r["status"] == "parse_failed")
        validation_failed = sum(1 for r in results if r["status"] == "validation_failed")
        
        avg_confidence = sum(
            r.get("confidence", 0) for r in results 
            if r["status"] in ["success", "validation_failed"]
        ) / max(1, success + validation_failed)
        
        return {
            "total_processed": total,
            "success_count": success,
            "completion_failed_count": completion_failed,
            "parse_failed_count": parse_failed,
            "validation_failed_count": validation_failed,
            "success_rate": success / total if total > 0 else 0,
            "average_confidence": avg_confidence,
            "failed_items": [
                {"index": r["index"], "status": r["status"], "error": r.get("error")}
                for r in results if r["status"] != "success"
            ]
        }

# 使用示例
async def batch_processing_example():
    processor = BatchProcessor()
    
    # 模拟不完整的JSON数据
    incomplete_jsons = [
        '{"name": "Alice", "age": 25, "email": "alice@example.com"',
        '{"name": "Bob", "age": 30, "email": "bob@example.com", "department": "IT"',
        '{"name": "Charlie", "age": "invalid", "email": "charlie@example.com"',
        '{"name": "David", "age": 28',
        '{"name": "Eve", "age": 32, "email": "eve@example.com", "department": "HR"}'
    ]
    
    # 批量处理
    results = await processor.process_batch(incomplete_jsons)
    
    # 生成报告
    report = processor.generate_report(results)
    
    print("\n=== 处理报告 ===")
    print(f"总处理数量: {report['total_processed']}")
    print(f"成功数量: {report['success_count']}")
    print(f"成功率: {report['success_rate']:.2%}")
    print(f"平均置信度: {report['average_confidence']:.2f}")
    
    if report['failed_items']:
        print("\n失败项目:")
        for item in report['failed_items']:
            print(f"  索引 {item['index']}: {item['status']} - {item['error']}")
    
    print("\n=== 详细结果 ===")
    for result in results:
        print(f"索引 {result['index']}: {result['status']}")
        if result['status'] == 'success':
            print(f"  数据: {result['parsed_data']}")
            print(f"  路径数量: {len(result['paths'])}")

# 运行示例
asyncio.run(batch_processing_example())
```

### 示例3: 实时数据监控

```python
import asyncio
import json
import time
from typing import Dict, Any, List
from dataclasses import dataclass, field
from agently_format.core.streaming_parser import StreamingParser
from agently_format.core.event_system import get_global_emitter, EventType
from agently_format.core.diff_engine import DiffEngine

@dataclass
class MonitoringMetrics:
    """监控指标"""
    total_events: int = 0
    parse_events: int = 0
    error_events: int = 0
    active_sessions: int = 0
    avg_parse_time: float = 0.0
    parse_times: List[float] = field(default_factory=list)
    last_update: float = field(default_factory=time.time)

class RealTimeMonitor:
    """实时数据监控器"""
    
    def __init__(self):
        self.parser = StreamingParser()
        self.diff_engine = DiffEngine()
        self.emitter = get_global_emitter()
        self.metrics = MonitoringMetrics()
        self.data_snapshots: Dict[str, Any] = {}
        
        # 注册事件监听器
        self._setup_event_listeners()
    
    def _setup_event_listeners(self):
        """设置事件监听器"""
        self.emitter.on(EventType.DELTA, self._on_parse_event)
        self.emitter.on(EventType.ERROR, self._on_error_event)
        self.emitter.on(EventType.COMPLETE, self._on_complete_event)
    
    async def _on_parse_event(self, event):
        """解析事件处理"""
        self.metrics.total_events += 1
        self.metrics.parse_events += 1
        
        # 记录解析时间
        if hasattr(event, 'processing_time'):
            self.metrics.parse_times.append(event.processing_time)
            if len(self.metrics.parse_times) > 100:  # 保持最近100次记录
                self.metrics.parse_times.pop(0)
            
            self.metrics.avg_parse_time = sum(self.metrics.parse_times) / len(self.metrics.parse_times)
    
    async def _on_error_event(self, event):
        """错误事件处理"""
        self.metrics.total_events += 1
        self.metrics.error_events += 1
        print(f"⚠️ 解析错误: {event.data.get('error', 'Unknown error')}")
    
    async def _on_complete_event(self, event):
        """完成事件处理"""
        session_id = event.session_id
        current_data = self.parser.get_current_data(session_id)
        
        if current_data:
            # 检查数据变化
            if session_id in self.data_snapshots:
                old_data = self.data_snapshots[session_id]
                diff_result = self.diff_engine.compute_diff(old_data, current_data)
                
                if diff_result.changes:
                    print(f"📊 数据变化检测 (会话: {session_id}):")
                    for change in diff_result.changes[:5]:  # 只显示前5个变化
                        print(f"  {change.operation}: {change.path} = {change.new_value}")
            
            # 更新快照
            self.data_snapshots[session_id] = current_data.copy()
    
    async def start_monitoring(self, data_sources: List[str]):
        """开始监控数据源"""
        print("🚀 开始实时数据监控...")
        
        # 为每个数据源创建会话
        sessions = {}
        for source in data_sources:
            session_id = self.parser.create_session()
            sessions[source] = session_id
            print(f"📡 创建监控会话: {source} -> {session_id}")
        
        self.metrics.active_sessions = len(sessions)
        
        # 模拟数据流
        await self._simulate_data_streams(sessions)
    
    async def _simulate_data_streams(self, sessions: Dict[str, str]):
        """模拟数据流"""
        # 模拟不同数据源的JSON数据流
        data_streams = {
            "user_service": [
                '{"users": [',
                '{"id": 1, "name": "Alice", "status": "online"},',
                '{"id": 2, "name": "Bob", "status": "offline"}',
                '], "timestamp": "2024-12-01T10:30:00Z"}'
            ],
            "order_service": [
                '{"orders": [',
                '{"id": "ord_001", "amount": 99.99, "status": "pending"},',
                '{"id": "ord_002", "amount": 149.99, "status": "completed"}',
                '], "total_amount": 249.98}'
            ],
            "metrics_service": [
                '{"metrics": {',
                '"cpu_usage": 45.2,',
                '"memory_usage": 67.8,',
                '"disk_usage": 23.1',
                '}, "timestamp": "2024-12-01T10:30:00Z"}'
            ]
        }
        
        # 并发处理所有数据流
        tasks = []
        for source, session_id in sessions.items():
            if source in data_streams:
                task = self._process_data_stream(
                    source, session_id, data_streams[source]
                )
                tasks.append(task)
        
        await asyncio.gather(*tasks)
        
        # 输出最终统计
        await self._print_final_stats(sessions)
    
    async def _process_data_stream(self, source: str, session_id: str, chunks: List[str]):
        """处理单个数据流"""
        print(f"\n📈 开始处理 {source} 数据流...")
        
        for i, chunk in enumerate(chunks):
            start_time = time.time()
            
            # 模拟网络延迟
            await asyncio.sleep(0.1)
            
            # 解析数据块
            result = await self.parser.parse_chunk(
                session_id=session_id,
                chunk=chunk
            )
            
            processing_time = time.time() - start_time
            
            # 获取当前状态
            state = self.parser.parsing_states[session_id]
            progress = (i + 1) / len(chunks)
            
            print(f"  {source}: 块 {i+1}/{len(chunks)} 处理完成 ({progress:.1%}) - {processing_time:.3f}s")
            
            # 如果有部分数据，显示预览
            if state.current_data:
                preview = str(state.current_data)[:100]
                print(f"    预览: {preview}...")
    
    async def _print_final_stats(self, sessions: Dict[str, str]):
        """输出最终统计信息"""
        print("\n📊 监控统计报告")
        print("=" * 50)
        print(f"总事件数: {self.metrics.total_events}")
        print(f"解析事件: {self.metrics.parse_events}")
        print(f"错误事件: {self.metrics.error_events}")
        print(f"活跃会话: {self.metrics.active_sessions}")
        print(f"平均解析时间: {self.metrics.avg_parse_time:.3f}s")
        
        print("\n📋 会话详情:")
        for source, session_id in sessions.items():
            final_data = self.parser.get_current_data(session_id)
            if final_data:
                print(f"  {source}: 解析成功 - {len(str(final_data))} 字符")
            else:
                print(f"  {source}: 解析失败")
            
            # 清理会话
            self.parser.cleanup_session(session_id)
        
        print("\n✅ 监控完成")

# 使用示例
async def monitoring_example():
    monitor = RealTimeMonitor()
    
    # 定义要监控的数据源
    data_sources = [
        "user_service",
        "order_service", 
        "metrics_service"
    ]
    
    # 开始监控
    await monitor.start_monitoring(data_sources)

# 运行示例
asyncio.run(monitoring_example())
```

---

## ⚡ 性能优化

### 性能指标

AgentlyFormat v2.0.0 在性能方面有显著提升：

| 指标 | v1.0.0 | v2.0.0 | 改进幅度 |
|------|--------|--------|----------|
| 适配器创建时间 | 19.5s | 3.75s | **81% ⬇️** |
| 测试执行时间 | ~15s | 3.75s | **75% ⬇️** |
| 内存使用 | 基准 | -50% | **50% ⬇️** |
| API响应时间 | ~500ms | ~100ms | **80% ⬇️** |
| 并发处理能力 | 10 req/s | 100 req/s | **900% ⬆️** |
| 错误率 | ~5% | <0.1% | **98% ⬇️** |

### 性能优化建议

#### 1. 内存优化

```python
# 使用环形缓冲区减少内存占用
from agently_format.core.streaming_parser import StreamingParser

parser = StreamingParser(
    buffer_size=8192,  # 8KB缓冲区
    max_chunk_size=1024*1024,  # 1MB最大块大小
    enable_compression=True  # 启用压缩
)

# 及时清理会话
session_id = parser.create_session()
# ... 处理数据 ...
parser.cleanup_session(session_id)  # 重要：及时清理
```

#### 2. 并发处理

```python
import asyncio
from agently_format.core.json_completer import JSONCompleter

async def concurrent_completion(json_list: list):
    completer = JSONCompleter()
    
    # 并发处理多个JSON补全任务
    tasks = [
        completer.complete(json_str) 
        for json_str in json_list
    ]
    
    results = await asyncio.gather(*tasks, return_exceptions=True)
    return results

# 使用信号量限制并发数
semaphore = asyncio.Semaphore(10)  # 最多10个并发任务

async def limited_concurrent_processing(json_list: list):
    async def process_with_limit(json_str):
        async with semaphore:
            return await completer.complete(json_str)
    
    tasks = [process_with_limit(json_str) for json_str in json_list]
    return await asyncio.gather(*tasks)
```

#### 3. 缓存优化

```python
from agently_format.core.json_completer import JSONCompleter
from agently_format.core.path_builder import PathBuilder

# 启用缓存
completer = JSONCompleter(enable_cache=True, cache_size=1000)
builder = PathBuilder(enable_cache=True, cache_ttl=300)  # 5分钟TTL

# 预热缓存
common_patterns = [
    '{"name": "',
    '{"id": ',
    '{"data": ['
]

for pattern in common_patterns:
    completer.complete(pattern)  # 预热缓存
```

#### 4. 批量处理优化

```python
from agently_format.api.batch import BatchProcessor

# 使用批量处理器
batch_processor = BatchProcessor(
    batch_size=100,  # 批量大小
    max_workers=4,   # 工作线程数
    timeout=30       # 超时时间
)

# 批量处理JSON补全
results = await batch_processor.process_completions(json_list)

# 批量路径构建
path_results = await batch_processor.process_path_building(data_list)
```

### 监控和调优

#### 1. 性能监控

```python
import time
import psutil
from agently_format.core.streaming_parser import StreamingParser

class PerformanceMonitor:
    def __init__(self):
        self.start_time = time.time()
        self.process = psutil.Process()
    
    def get_metrics(self):
        return {
            "uptime": time.time() - self.start_time,
            "cpu_percent": self.process.cpu_percent(),
            "memory_mb": self.process.memory_info().rss / 1024 / 1024,
            "threads": self.process.num_threads()
        }
    
    def log_metrics(self):
        metrics = self.get_metrics()
        print(f"性能指标: CPU={metrics['cpu_percent']:.1f}% "
              f"内存={metrics['memory_mb']:.1f}MB "
              f"线程={metrics['threads']}")

# 使用监控器
monitor = PerformanceMonitor()

# 定期输出性能指标
import asyncio

async def periodic_monitoring():
    while True:
        monitor.log_metrics()
        await asyncio.sleep(10)  # 每10秒输出一次

# 在后台运行监控
asyncio.create_task(periodic_monitoring())
```

#### 2. 性能基准测试

```python
import time
import statistics
from agently_format.core.json_completer import JSONCompleter

def benchmark_completion(test_cases: list, iterations: int = 100):
    """JSON补全性能基准测试"""
    completer = JSONCompleter()
    results = []
    
    for test_case in test_cases:
        times = []
        
        for _ in range(iterations):
            start_time = time.perf_counter()
            result = completer.complete(test_case)
            end_time = time.perf_counter()
            
            if result.is_valid:
                times.append(end_time - start_time)
        
        if times:
            results.append({
                "test_case": test_case[:50] + "...",
                "avg_time": statistics.mean(times),
                "min_time": min(times),
                "max_time": max(times),
                "std_dev": statistics.stdev(times) if len(times) > 1 else 0,
                "success_rate": len(times) / iterations
            })
    
    return results

# 运行基准测试
test_cases = [
    '{"simple": "test"',
    '{"nested": {"data": [1, 2, 3',
    '{"complex": {"users": [{"name": "Alice", "profile": {"age": 25'
]

benchmark_results = benchmark_completion(test_cases)

for result in benchmark_results:
    print(f"测试用例: {result['test_case']}")
    print(f"  平均时间: {result['avg_time']*1000:.2f}ms")
    print(f"  成功率: {result['success_rate']:.1%}")
    print()
```

---

## 🔧 故障排除

### 常见问题

#### 1. JSON补全失败

**问题**: JSON补全返回无效结果

**可能原因**:
- 输入JSON格式严重损坏
- 补全策略不适合当前数据
- 内存不足导致处理失败

**解决方案**:
```python
from agently_format.core.json_completer import JSONCompleter, CompletionStrategy

completer = JSONCompleter()

# 尝试不同的补全策略
strategies = [CompletionStrategy.SMART, CompletionStrategy.CONSERVATIVE, CompletionStrategy.AGGRESSIVE]

for strategy in strategies:
    result = completer.complete(incomplete_json, strategy=strategy)
    if result.is_valid:
        print(f"使用 {strategy} 策略补全成功")
        break
else:
    print("所有策略都失败，检查输入数据")
    
    # 诊断输入数据
    diagnostic = completer.diagnose(incomplete_json)
    print(f"诊断结果: {diagnostic}")
```

#### 2. 流式解析卡住

**问题**: 流式解析器停止响应

**可能原因**:
- 数据块过大导致内存溢出
- 会话超时
- 事件循环阻塞

**解决方案**:
```python
import asyncio
from agently_format.core.streaming_parser import StreamingParser

# 设置合理的参数
parser = StreamingParser(
    max_chunk_size=1024*512,  # 512KB
    session_ttl=1800,         # 30分钟
    max_sessions=100          # 限制会话数
)

# 添加超时处理
async def parse_with_timeout(session_id, chunk, timeout=10):
    try:
        result = await asyncio.wait_for(
            parser.parse_chunk(session_id, chunk),
            timeout=timeout
        )
        return result
    except asyncio.TimeoutError:
        print(f"解析超时，会话: {session_id}")
        parser.cleanup_session(session_id)
        return None

# 监控会话状态
def check_session_health():
    stats = parser.get_stats()
    if stats.get('active_sessions', 0) > 50:
        print("警告: 活跃会话过多，考虑清理")
        # 清理超时会话
        parser.cleanup_expired_sessions()
```

#### 3. API响应慢

**问题**: API接口响应时间过长

**可能原因**:
- 并发请求过多
- 数据处理量大
- 资源竞争

**解决方案**:
```python
# 1. 启用请求限流
from agently_format.api.middleware import RateLimitMiddleware

app.add_middleware(
    RateLimitMiddleware,
    calls=100,
    period=60  # 每分钟100次请求
)

# 2. 使用连接池
import httpx

client = httpx.AsyncClient(
    limits=httpx.Limits(
        max_keepalive_connections=20,
        max_connections=100
    ),
    timeout=30.0
)

# 3. 启用响应缓存
from agently_format.api.middleware import CacheMiddleware

app.add_middleware(
    CacheMiddleware,
    ttl=300,  # 5分钟缓存
    max_size=1000
)
```

#### 4. 内存泄漏

**问题**: 长时间运行后内存持续增长

**可能原因**:
- 会话未及时清理
- 事件监听器未正确移除
- 缓存无限增长

**解决方案**:
```python
import gc
import weakref
from agently_format.core.streaming_parser import StreamingParser

class MemoryManagedParser:
    def __init__(self):
        self.parser = StreamingParser()
        self.session_refs = weakref.WeakSet()
    
    def create_session(self):
        session_id = self.parser.create_session()
        self.session_refs.add(session_id)
        return session_id
    
    def cleanup_all_sessions(self):
        """清理所有会话"""
        for session_id in list(self.session_refs):
            self.parser.cleanup_session(session_id)
        gc.collect()  # 强制垃圾回收
    
    def get_memory_usage(self):
        """获取内存使用情况"""
        import psutil
        process = psutil.Process()
        return {
            "rss_mb": process.memory_info().rss / 1024 / 1024,
            "active_sessions": len(self.session_refs)
        }

# 定期清理内存
async def memory_cleanup_task(parser):
    while True:
        await asyncio.sleep(300)  # 每5分钟
        memory_info = parser.get_memory_usage()
        
        if memory_info["rss_mb"] > 500:  # 超过500MB
            print("内存使用过高，执行清理")
            parser.cleanup_all_sessions()
```

### 调试工具

#### 1. 日志配置

```python
import logging
from agently_format.core.logging import setup_logging

# 配置详细日志
setup_logging(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("agently_format.log")
    ]
)

# 获取特定模块的日志器
parser_logger = logging.getLogger("agently_format.core.streaming_parser")
completer_logger = logging.getLogger("agently_format.core.json_completer")

# 设置不同级别
parser_logger.setLevel(logging.INFO)
completer_logger.setLevel(logging.DEBUG)
```

#### 2. 性能分析

```python
import cProfile
import pstats
from agently_format.core.json_completer import JSONCompleter

def profile_completion(json_str: str):
    """性能分析JSON补全"""
    completer = JSONCompleter()
    
    # 创建性能分析器
    profiler = cProfile.Profile()
    
    # 开始分析
    profiler.enable()
    result = completer.complete(json_str)
    profiler.disable()
    
    # 输出分析结果
    stats = pstats.Stats(profiler)
    stats.sort_stats('cumulative')
    stats.print_stats(10)  # 显示前10个最耗时的函数
    
    return result

# 使用示例
result = profile_completion('{"large": "json", "data": [')
```

#### 3. 内存分析

```python
import tracemalloc
from agently_format.core.streaming_parser import StreamingParser

async def memory_trace_parsing():
    """内存追踪解析过程"""
    # 开始内存追踪
    tracemalloc.start()
    
    parser = StreamingParser()
    session_id = parser.create_session()
    
    # 记录初始内存
    snapshot1 = tracemalloc.take_snapshot()
    
    # 执行解析操作
    chunks = ['{"data": [' + str(i) + ',' for i in range(1000)]
    for chunk in chunks:
        await parser.parse_chunk(session_id, chunk)
    
    # 记录结束内存
    snapshot2 = tracemalloc.take_snapshot()
    
    # 分析内存差异
    top_stats = snapshot2.compare_to(snapshot1, 'lineno')
    
    print("内存使用Top 10:")
    for stat in top_stats[:10]:
        print(stat)
    
    # 清理
    parser.cleanup_session(session_id)
    tracemalloc.stop()
```

---

## 💡 最佳实践

### 1. 架构设计原则

#### 单一职责原则
```python
# ✅ 好的设计 - 每个类职责单一
class JSONCompleter:
    """专门负责JSON补全"""
    def complete(self, json_str: str) -> CompletionResult:
        pass

class StreamingParser:
    """专门负责流式解析"""
    async def parse_chunk(self, session_id: str, chunk: str) -> ParseResult:
        pass

class PathBuilder:
    """专门负责路径构建"""
    def extract_parsing_key_orders(self, data: dict) -> List[str]:
        pass

# ❌ 不好的设计 - 职责混乱
class JSONProcessor:
    """什么都做的类"""
    def complete_and_parse_and_build_paths(self, json_str: str):
        pass  # 职责过多
```

#### 依赖注入
```python
from typing import Protocol

class EventEmitterProtocol(Protocol):
    async def emit(self, event) -> None:
        pass

class StreamingParser:
    def __init__(self, event_emitter: EventEmitterProtocol):
        self.event_emitter = event_emitter  # 依赖注入
    
    async def parse_chunk(self, session_id: str, chunk: str):
        # 使用注入的依赖
        await self.event_emitter.emit(parse_event)
```

### 2. 错误处理策略

#### 分层错误处理
```python
from typing import Union, Optional
from dataclasses import dataclass

@dataclass
class ProcessingError:
    code: str
    message: str
    details: Optional[dict] = None
    recoverable: bool = True

class JSONCompleter:
    def complete(self, json_str: str) -> Union[CompletionResult, ProcessingError]:
        try:
            # 核心处理逻辑
            return self._do_complete(json_str)
        except ValueError as e:
            return ProcessingError(
                code="INVALID_INPUT",
                message=f"输入JSON格式无效: {e}",
                recoverable=False
            )
        except MemoryError as e:
            return ProcessingError(
                code="MEMORY_EXHAUSTED",
                message="内存不足，请减少数据量",
                recoverable=True
            )
        except Exception as e:
            return ProcessingError(
                code="UNKNOWN_ERROR",
                message=f"未知错误: {e}",
                details={"exception_type": type(e).__name__},
                recoverable=False
            )
```

#### 重试机制
```python
import asyncio
from functools import wraps

def retry_on_failure(max_retries: int = 3, delay: float = 1.0):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < max_retries:
                        await asyncio.sleep(delay * (2 ** attempt))  # 指数退避
                        continue
                    break
            
            raise last_exception
        return wrapper
    return decorator

class ModelAdapter:
    @retry_on_failure(max_retries=3, delay=1.0)
    async def chat_completion(self, messages: list) -> ChatResponse:
        # 可能失败的网络请求
        pass
```

### 3. 资源管理

#### 上下文管理器
```python
from contextlib import asynccontextmanager
from typing import AsyncGenerator

class StreamingParser:
    @asynccontextmanager
    async def session_context(self) -> AsyncGenerator[str, None]:
        """会话上下文管理器"""
        session_id = self.create_session()
        try:
            yield session_id
        finally:
            self.cleanup_session(session_id)

# 使用示例
async def process_with_session():
    parser = StreamingParser()
    
    async with parser.session_context() as session_id:
        # 自动管理会话生命周期
        result = await parser.parse_chunk(session_id, chunk)
        return result
    # 会话自动清理
```

#### 连接池管理
```python
import asyncio
from typing import Dict, Optional

class ConnectionPool:
    def __init__(self, max_connections: int = 10):
        self.max_connections = max_connections
        self.connections: Dict[str, object] = {}
        self.semaphore = asyncio.Semaphore(max_connections)
    
    async def get_connection(self, key: str) -> object:
        async with self.semaphore:
            if key not in self.connections:
                self.connections[key] = await self._create_connection(key)
            return self.connections[key]
    
    async def _create_connection(self, key: str) -> object:
        # 创建实际连接
        pass
    
    async def close_all(self):
        for conn in self.connections.values():
            await self._close_connection(conn)
        self.connections.clear()
```

### 4. 测试策略

#### 单元测试
```python
import pytest
from unittest.mock import Mock, AsyncMock
from agently_format.core.json_completer import JSONCompleter

class TestJSONCompleter:
    def setup_method(self):
        self.completer = JSONCompleter()
    
    def test_simple_completion(self):
        """测试简单JSON补全"""
        incomplete = '{"name": "Alice"'
        result = self.completer.complete(incomplete)
        
        assert result.is_valid
        assert result.completed_json == '{"name": "Alice"}'
    
    def test_complex_nested_completion(self):
        """测试复杂嵌套JSON补全"""
        incomplete = '{"user": {"profile": {"age": 25'
        result = self.completer.complete(incomplete)
        
        assert result.is_valid
        assert '}}' in result.completed_json
    
    def test_invalid_input_handling(self):
        """测试无效输入处理"""
        invalid_input = "not json at all"
        result = self.completer.complete(invalid_input)
        
        assert not result.is_valid
        assert result.error_message is not None
    
    @pytest.mark.parametrize("strategy", [
        "smart", "conservative", "aggressive"
    ])
    def test_different_strategies(self, strategy):
        """测试不同补全策略"""
        incomplete = '{"data": [1, 2'
        result = self.completer.complete(incomplete, strategy=strategy)
        
        # 所有策略都应该能处理这个简单案例
        assert result.is_valid
```

#### 集成测试
```python
import pytest
import asyncio
from agently_format.core.streaming_parser import StreamingParser
from agently_format.core.event_system import EventEmitter

@pytest.mark.asyncio
class TestStreamingIntegration:
    async def test_end_to_end_parsing(self):
        """端到端流式解析测试"""
        emitter = EventEmitter()
        parser = StreamingParser(emitter)
        
        # 收集事件
        events = []
        async def event_collector(event):
            events.append(event)
        
        emitter.on('parse_progress', event_collector)
        
        # 执行解析
        session_id = parser.create_session()
        chunks = ['{"users": [', '{"id": 1}', ']}']
        
        for chunk in chunks:
            await parser.parse_chunk(session_id, chunk)
        
        # 验证结果
        final_data = parser.get_current_data(session_id)
        assert final_data == {"users": [{"id": 1}]}
        assert len(events) > 0  # 确保事件被触发
        
        parser.cleanup_session(session_id)
```

#### 性能测试
```python
import time
import pytest
from agently_format.core.json_completer import JSONCompleter

class TestPerformance:
    def test_completion_performance(self):
        """测试补全性能"""
        completer = JSONCompleter()
        large_json = '{"data": [' + ','.join([f'{{"id": {i}}}' for i in range(1000)])
        
        start_time = time.perf_counter()
        result = completer.complete(large_json)
        end_time = time.perf_counter()
        
        processing_time = end_time - start_time
        
        assert result.is_valid
        assert processing_time < 1.0  # 应该在1秒内完成
    
    @pytest.mark.benchmark
    def test_memory_usage(self):
        """测试内存使用"""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss
        
        completer = JSONCompleter()
        
        # 处理大量数据
        for i in range(100):
            large_json = '{"batch": ' + str(i) + ', "data": ['
            completer.complete(large_json)
        
        final_memory = process.memory_info().rss
        memory_increase = final_memory - initial_memory
        
        # 内存增长应该在合理范围内（比如50MB）
        assert memory_increase < 50 * 1024 * 1024
```

### 5. 部署建议

#### Docker部署
```dockerfile
# Dockerfile
FROM python:3.11-slim

WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用代码
COPY . .

# 安装应用
RUN pip install -e .

# 创建非root用户
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# 暴露端口
EXPOSE 8000

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# 启动命令
CMD ["uvicorn", "agently_format.api.app:app", "--host", "0.0.0.0", "--port", "8000"]
```

#### Docker Compose
```yaml
# docker-compose.yml
version: '3.8'

services:
  agently-format:
    build: .
    ports:
      - "8000:8000"
    environment:
      - AGENTLY_FORMAT_DEBUG=false
      - OPENAI_API_KEY=${OPENAI_API_KEY}
    volumes:
      - ./logs:/app/logs
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
  
  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
    depends_on:
      - agently-format
    restart: unless-stopped
```

#### 生产环境配置
```python
# production_config.py
from agently_format.api.config import Settings

class ProductionSettings(Settings):
    debug: bool = False
    log_level: str = "INFO"
    
    # 性能优化
    max_workers: int = 4
    max_chunk_size: int = 1024 * 1024  # 1MB
    session_ttl: int = 1800  # 30分钟
    
    # 安全配置
    rate_limit_enabled: bool = True
    rate_limit_requests: int = 1000
    rate_limit_window: int = 60
    
    # 监控配置
    metrics_enabled: bool = True
    health_check_enabled: bool = True
    
    class Config:
        env_file = ".env.production"
```

---

## 📞 技术支持

### 获取帮助

- **GitHub Issues**: [https://github.com/AgentEra/AgentlyFormat/issues](https://github.com/AgentEra/AgentlyFormat/issues)
- **文档**: [https://AgentlyFormat.readthedocs.io](https://AgentlyFormat.readthedocs.io)
- **邮箱支持**: support@agently.tech

### 贡献指南

1. Fork 项目仓库
2. 创建功能分支 (`git checkout -b feature/amazing-feature`)
3. 提交更改 (`git commit -m 'Add amazing feature'`)
4. 推送到分支 (`git push origin feature/amazing-feature`)
5. 创建 Pull Request

### 版本规划

- **v2.1.0**: 更多模型支持、插件系统
- **v2.2.0**: Web管理界面、集群支持
- **v3.0.0**: 机器学习集成、多语言支持

---

## 📄 许可证

本项目采用 [Apache-2.0](https://opensource.org/licenses/Apache-2.0) 许可证。

---

**AgentlyFormat** - 让大模型JSON输出更稳定、更可靠！ 🚀

*最后更新: 2024年12月*