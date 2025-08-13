# AgentlyFormat 迁移指南

本文档提供从 AgentlyFormat v1.0.0 到 v2.0.0 的详细迁移指南。

## 📋 迁移概述

AgentlyFormat v2.0.0 是一个重大版本更新，包含了核心架构重构、API 接口升级和配置系统重构。本次升级带来了显著的性能提升和功能增强，但也包含了一些破坏性变更。

### 版本对比

| 特性 | v1.0.0 | v2.0.0 |
|------|--------|--------|
| 解析性能 | 基础 | 提升 300% |
| 内存使用 | 标准 | 优化 40% |
| API 接口 | 基础 REST | 增强 REST + WebSocket |
| 配置系统 | 简单 | 分层配置 |
| 监控统计 | 有限 | 完整指标 |
| 测试覆盖 | 基础 | 95%+ |

## 🚨 破坏性变更

### 1. 核心模块重构

#### StreamingParser 变更

**v1.0.0:**
```python
from agently_format import StreamingParser

parser = StreamingParser()
result = parser.parse(data)
```

**v2.0.0:**
```python
from agently_format.core import StreamingParser
from agently_format.types import ParseRequest

parser = StreamingParser()
request = ParseRequest(
    content=data,
    format_type="json",
    streaming=True
)
result = await parser.parse_async(request)
```

#### JSONCompleter 变更

**v1.0.0:**
```python
from agently_format import JSONCompleter

completer = JSONCompleter()
result = completer.complete(incomplete_json)
```

**v2.0.0:**
```python
from agently_format.core import JSONCompleter
from agently_format.types import CompletionRequest

completer = JSONCompleter()
request = CompletionRequest(
    incomplete_json=incomplete_json,
    target_schema=schema,  # 新增 Schema 支持
    completion_mode="smart"  # 新增智能补全模式
)
result = await completer.complete_async(request)
```

### 2. API 接口变更

#### 端点路径变更

| v1.0.0 | v2.0.0 | 说明 |
|--------|--------|---------|
| `/parse` | `/parse/stream` | 流式解析端点 |
| `/complete` | `/json/complete` | JSON 补全端点 |
| `/health` | `/health` | 健康检查（无变更） |
| - | `/stats` | 新增统计端点 |
| - | `/path/build` | 新增路径构建端点 |
| - | `/model/config` | 新增模型配置端点 |
| - | `/chat` | 新增聊天接口 |

#### 请求/响应格式变更

**v1.0.0 解析请求:**
```json
{
  "content": "string",
  "format": "json"
}
```

**v2.0.0 解析请求:**
```json
{
  "content": "string",
  "format_type": "json",
  "streaming": true,
  "schema": {},
  "options": {
    "validate_schema": true,
    "auto_complete": true,
    "error_recovery": true
  }
}
```

### 3. 配置系统变更

#### 配置文件结构

**v1.0.0 配置:**
```python
# config.py
API_HOST = "localhost"
API_PORT = 8000
DEBUG = False
```

**v2.0.0 配置:**
```python
# config/settings.py
from agently_format.config import BaseConfig

class AppConfig(BaseConfig):
    # 服务器配置
    server: ServerConfig = ServerConfig()
    
    # 解析器配置
    parser: ParserConfig = ParserConfig()
    
    # 模型配置
    models: Dict[str, ModelConfig] = {}
    
    # 监控配置
    monitoring: MonitoringConfig = MonitoringConfig()
```

## 🔄 迁移步骤

### 步骤 1: 环境准备

1. **Python 版本要求**
   ```bash
   # v1.0.0 要求 Python 3.8+
   # v2.0.0 要求 Python 3.9+
   python --version  # 确保 >= 3.9
   ```

2. **依赖更新**
   ```bash
   pip uninstall agently-format
   pip install agently-format==2.0.0
   ```

### 步骤 2: 代码迁移

#### 2.1 导入语句更新

**查找并替换:**
```python
# 旧导入
from agently_format import StreamingParser, JSONCompleter
from agently_format import ModelAdapter

# 新导入
from agently_format.core import StreamingParser, JSONCompleter
from agently_format.adapters import ModelAdapter
from agently_format.types import ParseRequest, CompletionRequest
```

#### 2.2 异步方法迁移

**同步到异步:**
```python
# v1.0.0 同步调用
def process_data(data):
    parser = StreamingParser()
    result = parser.parse(data)
    return result

# v2.0.0 异步调用
async def process_data(data):
    parser = StreamingParser()
    request = ParseRequest(content=data, format_type="json")
    result = await parser.parse_async(request)
    return result
```

#### 2.3 错误处理更新

**v1.0.0:**
```python
try:
    result = parser.parse(data)
except Exception as e:
    print(f"解析错误: {e}")
```

**v2.0.0:**
```python
from agently_format.exceptions import (
    ParseError, ValidationError, CompletionError
)

try:
    result = await parser.parse_async(request)
except ParseError as e:
    print(f"解析错误: {e.message}")
except ValidationError as e:
    print(f"验证错误: {e.details}")
except CompletionError as e:
    print(f"补全错误: {e.context}")
```

### 步骤 3: 配置迁移

#### 3.1 创建新配置文件

```python
# config/app_config.py
from agently_format.config import (
    BaseConfig, ServerConfig, ParserConfig, 
    ModelConfig, MonitoringConfig
)

class ProductionConfig(BaseConfig):
    """生产环境配置"""
    
    server = ServerConfig(
        host="0.0.0.0",
        port=8000,
        workers=4,
        reload=False
    )
    
    parser = ParserConfig(
        max_content_size=10 * 1024 * 1024,  # 10MB
        timeout=30,
        enable_caching=True,
        cache_ttl=3600
    )
    
    models = {
        "openai": ModelConfig(
            provider="openai",
            model="gpt-3.5-turbo",
            api_key="${OPENAI_API_KEY}",
            max_tokens=4096
        )
    }
    
    monitoring = MonitoringConfig(
        enable_metrics=True,
        metrics_port=9090,
        log_level="INFO"
    )
```

#### 3.2 环境变量迁移

**创建 .env 文件:**
```env
# v2.0.0 环境变量
AGENTLY_ENV=production
AGENTLY_CONFIG_PATH=config/app_config.py

# API 密钥
OPENAI_API_KEY=your_openai_key
BAIDU_API_KEY=your_baidu_key
BAIDU_SECRET_KEY=your_baidu_secret

# 数据库配置（如果使用）
DATABASE_URL=sqlite:///agently_format.db

# Redis 配置（如果使用缓存）
REDIS_URL=redis://localhost:6379/0
```

### 步骤 4: API 客户端迁移

#### 4.1 HTTP 客户端更新

**v1.0.0:**
```python
import requests

def parse_content(content):
    response = requests.post(
        "http://localhost:8000/parse",
        json={"content": content, "format": "json"}
    )
    return response.json()
```

**v2.0.0:**
```python
import aiohttp
import asyncio

async def parse_content(content):
    async with aiohttp.ClientSession() as session:
        async with session.post(
            "http://localhost:8000/parse/stream",
            json={
                "content": content,
                "format_type": "json",
                "streaming": False,
                "options": {
                    "validate_schema": True,
                    "auto_complete": True
                }
            }
        ) as response:
            return await response.json()
```

#### 4.2 WebSocket 客户端（新功能）

```python
import websockets
import json

async def stream_parse(content):
    uri = "ws://localhost:8000/ws/parse"
    async with websockets.connect(uri) as websocket:
        # 发送解析请求
        request = {
            "content": content,
            "format_type": "json",
            "streaming": True
        }
        await websocket.send(json.dumps(request))
        
        # 接收流式结果
        async for message in websocket:
            data = json.loads(message)
            if data["type"] == "delta":
                print(f"增量数据: {data['content']}")
            elif data["type"] == "done":
                print(f"解析完成: {data['result']}")
                break
            elif data["type"] == "error":
                print(f"解析错误: {data['error']}")
                break
```

## 🧪 测试迁移

### 测试框架更新

**v1.0.0:**
```python
import unittest
from agently_format import StreamingParser

class TestParser(unittest.TestCase):
    def test_parse(self):
        parser = StreamingParser()
        result = parser.parse('{"key": "value"}')
        self.assertIsNotNone(result)
```

**v2.0.0:**
```python
import pytest
from agently_format.core import StreamingParser
from agently_format.types import ParseRequest

class TestParser:
    @pytest.mark.asyncio
    async def test_parse_async(self):
        parser = StreamingParser()
        request = ParseRequest(
            content='{"key": "value"}',
            format_type="json"
        )
        result = await parser.parse_async(request)
        assert result is not None
        assert result.success is True
```

## 🚀 性能优化建议

### 1. 启用缓存

```python
# 配置 Redis 缓存
parser_config = ParserConfig(
    enable_caching=True,
    cache_backend="redis",
    cache_url="redis://localhost:6379/0",
    cache_ttl=3600
)
```

### 2. 批量处理

```python
# 使用批量解析 API
async def batch_parse(contents):
    async with aiohttp.ClientSession() as session:
        tasks = []
        for content in contents:
            task = session.post(
                "http://localhost:8000/parse/batch",
                json={"items": [{
                    "content": content,
                    "format_type": "json"
                }]}
            )
            tasks.append(task)
        
        responses = await asyncio.gather(*tasks)
        return [await resp.json() for resp in responses]
```

### 3. 连接池配置

```python
# 配置连接池
server_config = ServerConfig(
    max_connections=1000,
    keepalive_timeout=65,
    connection_pool_size=100
)
```

## 🔍 故障排除

### 常见问题

#### 1. 导入错误

**错误:** `ImportError: cannot import name 'StreamingParser'`

**解决:**
```python
# 错误的导入
from agently_format import StreamingParser

# 正确的导入
from agently_format.core import StreamingParser
```

#### 2. 异步调用错误

**错误:** `RuntimeError: cannot be called from a running event loop`

**解决:**
```python
# 错误的调用
result = parser.parse(data)  # 同步调用已移除

# 正确的调用
result = await parser.parse_async(request)
```

#### 3. 配置加载错误

**错误:** `ConfigurationError: Invalid configuration format`

**解决:**
```python
# 使用新的配置加载方式
from agently_format.config import load_config

config = load_config("config/app_config.py")
```

### 调试工具

```python
# 启用调试模式
from agently_format.debug import enable_debug_mode

enable_debug_mode(
    log_level="DEBUG",
    trace_requests=True,
    profile_performance=True
)
```

## 📚 迁移检查清单

### 代码迁移
- [ ] 更新所有导入语句
- [ ] 将同步调用改为异步调用
- [ ] 更新错误处理逻辑
- [ ] 迁移配置文件格式
- [ ] 更新 API 端点路径
- [ ] 修改请求/响应格式

### 测试迁移
- [ ] 更新测试框架（unittest → pytest）
- [ ] 添加异步测试支持
- [ ] 更新测试数据格式
- [ ] 验证性能测试

### 部署迁移
- [ ] 更新 Python 版本要求
- [ ] 更新依赖包版本
- [ ] 配置环境变量
- [ ] 更新部署脚本
- [ ] 配置监控和日志

### 验证测试
- [ ] 功能回归测试
- [ ] 性能基准测试
- [ ] 负载测试
- [ ] 安全测试

## 🆘 获取帮助

如果在迁移过程中遇到问题，可以通过以下方式获取帮助：

1. **查看文档**: [完整 API 文档](API.md)
2. **示例代码**: `examples/` 目录中的迁移示例
3. **问题反馈**: GitHub Issues
4. **社区讨论**: GitHub Discussions

## 📈 迁移后验证

迁移完成后，建议进行以下验证：

```bash
# 运行测试套件
pytest tests/ -v

# 性能基准测试
python tests/test_performance.py

# 启动服务验证
python -m uvicorn agently_format.api.app:app --reload

# API 健康检查
curl http://localhost:8000/health
```

---

**迁移完成后，您将享受到 v2.0.0 带来的显著性能提升和丰富功能！**