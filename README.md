# AgentlyFormat

> 专注于大模型输出稳定的格式化数据处理

[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Python](https://img.shields.io/badge/Python-3.11+-green.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-red.svg)](https://fastapi.tiangolo.com/)

## 🎯 核心问题

大模型在生成JSON数据时经常遇到以下问题：

- **格式不完整**：输出被截断，缺少闭合括号
- **流式输出**：数据分块传输，需要实时解析
- **结构复杂**：嵌套深度大，路径访问困难
- **格式不一致**：不同模型输出格式差异

**AgentlyFormat** 专门解决这些问题，提供稳定可靠的JSON处理能力。

## ✨ 核心特性

- 🔧 **智能JSON补全** - 自动修复不完整的JSON结构
- 🌊 **流式解析** - 支持大文件分块处理，内存高效
- 🛣️ **路径构建** - 灵活的数据路径生成和访问
- 🤖 **模型适配** - 支持OpenAI、豆包、文心大模型、千问、DeepSeek、Kimi等主流AI模型
- ⚡ **事件驱动** - 实时状态更新和事件通知
- 🌐 **REST API** - 完整的Web服务接口

## 🚀 快速开始

### 安装

```bash
pip install AgentlyFormat
```

### 基础使用

#### 1. JSON智能补全

```python
from agently_format import JSONCompleter

# 创建补全器
completer = JSONCompleter()

# 不完整的JSON
incomplete_json = '{"name": "Alice", "age": 25, "skills": ["Python"'

# 智能补全
result = completer.complete(incomplete_json)
print(result.completed_json)
# 输出: {"name": "Alice", "age": 25, "skills": ["Python"]}
```

#### 2. 流式JSON解析

```python
import asyncio
from agently_format import StreamingParser

async def parse_stream():
    parser = StreamingParser()
    session_id = parser.create_session()
    
    # 模拟分块数据
    chunks = [
        '{"users": [',
        '{"id": 1, "name": "Alice"},',
        '{"id": 2, "name": "Bob"}',
        '], "total": 2}'
    ]
    
    for chunk in chunks:
        result = await parser.parse_chunk(chunk, session_id)
        print(f"进度: {result.progress:.1%}")
    
    # 获取完整数据
    final_data = parser.get_current_data(session_id)
    print(final_data)

asyncio.run(parse_stream())
```

#### 3. 数据路径构建

```python
from agently_format import PathBuilder

builder = PathBuilder()
data = {
    "api": {
        "users": [
            {"id": 1, "profile": {"name": "Alice"}},
            {"id": 2, "profile": {"name": "Bob"}}
        ]
    }
}

# 提取所有路径
paths = builder.build_paths(data)
print(paths)
# ['api.users.0.id', 'api.users.0.profile.name', 'api.users.1.id', 'api.users.1.profile.name']

# 通过路径获取值
value = builder.get_value_by_path(data, "api.users.0.profile.name")
print(value)  # "Alice"
```

## 🔧 高级功能

### 模型适配器

支持多种主流AI模型，统一的接口设计：

```python
from agently_format.adapters import (
    OpenAIAdapter, DoubaoAdapter, WenxinAdapter, 
    QianwenAdapter, DeepSeekAdapter, KimiAdapter
)
from agently_format.types import ModelConfig

# OpenAI适配器
openai_config = ModelConfig(
    model_type="openai",
    model_name="gpt-3.5-turbo",
    api_key="your-api-key"
)
adapter = OpenAIAdapter(openai_config)

# 文心大模型适配器
wenxin_config = ModelConfig(
    model_type="baidu",
    model_name="ernie-4.0-8k",
    api_key="your-api-key",
    api_secret="your-api-secret"
)
wenxin_adapter = WenxinAdapter(wenxin_config)

# 千问适配器
qianwen_config = ModelConfig(
    model_type="qwen",
    model_name="qwen-turbo",
    api_key="your-api-key"
)
qianwen_adapter = QianwenAdapter(qianwen_config)

# DeepSeek适配器
deepseek_config = ModelConfig(
    model_type="deepseek",
    model_name="deepseek-chat",
    api_key="your-api-key"
)
deepseek_adapter = DeepSeekAdapter(deepseek_config)

# Kimi适配器
kimi_config = ModelConfig(
    model_type="kimi",
    model_name="moonshot-v1-8k",
    api_key="your-api-key"
)
kimi_adapter = KimiAdapter(kimi_config)

# 统一的聊天补全接口
response = await adapter.chat_completion([
    {"role": "user", "content": "生成一个用户信息的JSON"}
])
print(response.content)
```

### REST API服务

```bash
# 启动API服务
cd AgentlyFormat
python -m agently_format.api.app
```

```bash
# JSON补全API
curl -X POST "http://localhost:8000/api/v1/json/complete" \
     -H "Content-Type: application/json" \
     -d '{"content": "{\"name\": \"Alice\", \"age\": 25", "strategy": "smart"}'

# 路径构建API
curl -X POST "http://localhost:8000/api/v1/path/build" \
     -H "Content-Type: application/json" \
     -d '{"data": {"user": {"name": "Alice"}}, "style": "dot"}'
```

## 📚 API文档

### 核心类

#### JSONCompleter

```python
class JSONCompleter:
    def complete(self, json_str: str, strategy: str = "smart") -> CompletionResult:
        """补全不完整的JSON字符串"""
        
    def validate(self, json_str: str) -> bool:
        """验证JSON格式是否正确"""
```

#### StreamingParser

```python
class StreamingParser:
    def create_session(self, session_id: str = None) -> str:
        """创建解析会话"""
        
    async def parse_chunk(self, chunk: str, session_id: str, is_final: bool = False) -> ParseResult:
        """解析JSON数据块"""
        
    def get_current_data(self, session_id: str) -> dict:
        """获取当前解析的数据"""
```

#### PathBuilder

```python
class PathBuilder:
    def build_paths(self, data: dict, style: str = "dot") -> List[str]:
        """构建数据路径列表"""
        
    def get_value_by_path(self, data: dict, path: str) -> Any:
        """通过路径获取值"""
        
    def convert_path(self, path: str, target_style: str) -> str:
        """转换路径格式"""
```

## 🛠️ 配置

### 环境变量

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
```

### 配置文件

```yaml
# config.yaml
server:
  host: "0.0.0.0"
  port: 8000
  debug: false

processing:
  max_chunk_size: 1048576  # 1MB
  session_ttl: 3600       # 1小时
  max_sessions: 1000

models:
  openai:
    api_key: "${OPENAI_API_KEY}"
    timeout: 30
  doubao:
    api_key: "${DOUBAO_API_KEY}"
    timeout: 30
  wenxin:
    api_key: "${WENXIN_API_KEY}"
    api_secret: "${WENXIN_SECRET_KEY}"
    timeout: 30
  qianwen:
    api_key: "${QIANWEN_API_KEY}"
    timeout: 30
  deepseek:
    api_key: "${DEEPSEEK_API_KEY}"
    timeout: 30
  kimi:
    api_key: "${KIMI_API_KEY}"
    timeout: 30
```

## 🧪 测试

```bash
# 安装开发依赖
pip install -e ".[dev]"

# 运行测试
pytest

# 运行特定测试
pytest tests/test_core.py

# 生成覆盖率报告
pytest --cov=agently_format --cov-report=html
```

## 📖 示例

查看 `examples/` 目录获取更多示例：

- `basic_usage.py` - 基础功能演示
- `streaming_example.py` - 流式处理示例
- `api_client_example.py` - API客户端使用
- `model_adapter_example.py` - 模型适配器示例
- `advanced_usage.py` - 高级功能演示

## 🚀 性能

- **JSON补全**: 处理1MB文件 < 100ms
- **流式解析**: 10MB数据流 < 500ms
- **路径构建**: 1000个路径 < 50ms
- **并发处理**: 支持1000+并发会话

## 🤝 贡献

欢迎贡献代码！请遵循以下步骤：

1. Fork 项目
2. 创建功能分支 (`git checkout -b feature/amazing-feature`)
3. 提交更改 (`git commit -m 'Add amazing feature'`)
4. 推送到分支 (`git push origin feature/amazing-feature`)
5. 创建 Pull Request

## 📄 许可证

本项目采用 [Apache-2.0](https://opensource.org/licenses/Apache-2.0) 许可证。

## 🔗 链接

- **GitHub**: https://github.com/ailijian/AgentlyFormat
- **文档**: https://AgentlyFormat.readthedocs.io
- **PyPI**: https://pypi.org/project/AgentlyFormat
- **问题反馈**: https://github.com/ailijian/AgentlyFormat/issues

## 🙏 致谢

- [Agently](https://github.com/AgentEra/Agently) - 强大的agent通用框架，本项目主要基于Agently强大的格式化输出能力构建，主打轻量化
- [FastAPI](https://fastapi.tiangolo.com/) - 现代化的Web框架
- [Pydantic](https://pydantic-docs.helpmanual.io/) - 数据验证库
- [asyncio](https://docs.python.org/3/library/asyncio.html) - 异步编程支持

---

**AgentlyFormat** - 让大模型JSON输出更稳定、更可靠！ 🚀