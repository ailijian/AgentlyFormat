"""Pytest配置文件

定义测试夹具和配置。
"""

import asyncio
import pytest
import tempfile
import shutil
from pathlib import Path
from typing import Dict, Any, AsyncGenerator
from unittest.mock import AsyncMock, MagicMock

from fastapi.testclient import TestClient
import httpx

from agently_format.api.app import create_app
from agently_format.api.config import Settings
from agently_format.core.streaming_parser import StreamingParser
from agently_format.core.json_completer import JSONCompleter
from agently_format.core.path_builder import PathBuilder
from agently_format.adapters.model_adapter import ModelAdapter
from agently_format.types.models import ModelType, create_model_config


# 测试配置
class TestSettings(Settings):
    """测试环境配置"""
    environment: str = "testing"
    debug: bool = True
    testing: bool = True
    
    # 数据库配置（使用内存数据库）
    database_url: str = "sqlite:///:memory:"
    
    # Redis配置（使用假Redis）
    redis_url: str = "redis://localhost:6379/15"
    
    # API配置
    api_rate_limit: int = 1000
    api_rate_limit_window: int = 60
    
    # 日志配置
    log_level: str = "DEBUG"
    
    class Config:
        env_file = ".env.test"


@pytest.fixture(scope="session")
def event_loop():
    """创建事件循环"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        yield loop
    finally:
        # 确保所有任务完成
        pending = asyncio.all_tasks(loop)
        if pending:
            loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
        loop.close()


@pytest.fixture
def test_settings():
    """测试配置夹具"""
    return TestSettings()


@pytest.fixture
def temp_dir():
    """临时目录夹具"""
    temp_path = tempfile.mkdtemp()
    yield Path(temp_path)
    shutil.rmtree(temp_path)


@pytest.fixture
def app(test_settings):
    """FastAPI应用夹具"""
    # 覆盖设置
    from agently_format.api.config import get_settings
    
    def override_get_settings():
        return test_settings
    
    # 创建测试应用
    test_app = create_app()
    test_app.dependency_overrides[get_settings] = override_get_settings
    
    yield test_app
    
    # 清理
    test_app.dependency_overrides.clear()


@pytest.fixture
def client(app):
    """测试客户端夹具"""
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
async def async_client(app):
    """异步测试客户端夹具"""
    async with httpx.AsyncClient(app=app, base_url="http://test") as client:
        yield client


@pytest.fixture
def streaming_parser():
    """流式解析器夹具"""
    return StreamingParser(
        enable_diff_engine=True,
        enable_completion=True,
        chunk_timeout=5.0
    )


@pytest.fixture
def enhanced_streaming_parser():
    """增强流式解析器夹具"""
    schema = {
        "type": "object",
        "properties": {
            "name": {"type": "string"},
            "age": {"type": "integer", "minimum": 0},
            "email": {"type": "string", "format": "email"}
        }
    }
    
    return StreamingParser(
        enable_diff_engine=True,
        enable_schema_validation=True,
        enable_enhanced_stats=True,
        adaptive_timeout_enabled=True,
        schema=schema,
        buffer_size=1024
    )


@pytest.fixture
def chunk_buffer():
    """块缓冲区夹具"""
    from agently_format.core.streaming_parser import ChunkBuffer
    return ChunkBuffer(max_size=512)


@pytest.fixture
def adaptive_timeout():
    """自适应超时夹具"""
    from agently_format.core.streaming_parser import AdaptiveTimeout
    return AdaptiveTimeout(
        initial_timeout=1.0,
        max_timeout=10.0,
        backoff_factor=2.0
    )


@pytest.fixture
def schema_validator():
    """Schema验证器夹具"""
    from agently_format.core.schemas import SchemaValidator
    schema = {
        "type": "object",
        "properties": {
            "name": {"type": "string"},
            "age": {"type": "integer", "minimum": 0}
        }
    }
    return SchemaValidator(schema)


@pytest.fixture
def diff_engine():
    """差分引擎夹具"""
    from agently_format.core.diff_engine import StructuredDiffEngine, DiffMode, CoalescingConfig
    return StructuredDiffEngine(
        diff_mode=DiffMode.SMART,
        coalescing_config=CoalescingConfig(
            enabled=True,
            time_window_ms=100,
            max_coalesced_events=5
        )
    )


@pytest.fixture
def json_completer():
    """JSON补全器夹具"""
    return JSONCompleter()


@pytest.fixture
def path_builder():
    """路径构建器夹具"""
    return PathBuilder()


@pytest.fixture
def mock_model_adapter():
    """模拟模型适配器夹具"""
    adapter = AsyncMock()
    adapter.chat_completion = AsyncMock()
    adapter.close = AsyncMock()
    return adapter


@pytest.fixture
def sample_json_data():
    """示例JSON数据夹具"""
    return {
        "users": [
            {
                "id": 1,
                "name": "Alice",
                "email": "alice@example.com",
                "profile": {
                    "age": 25,
                    "city": "New York",
                    "interests": ["reading", "coding", "travel"]
                }
            },
            {
                "id": 2,
                "name": "Bob",
                "email": "bob@example.com",
                "profile": {
                    "age": 30,
                    "city": "San Francisco",
                    "interests": ["music", "sports"]
                }
            }
        ],
        "metadata": {
            "total": 2,
            "page": 1,
            "timestamp": "2024-01-01T00:00:00Z"
        }
    }


@pytest.fixture
def incomplete_json_chunks():
    """不完整JSON块夹具"""
    return [
        '{"users": [',
        '{"id": 1, "name": "Alice",',
        '"email": "alice@example.com"},',
        '{"id": 2, "name": "Bob",',
        '"email": "bob@example.com"}',
        '], "total": 2}'
    ]


@pytest.fixture
def model_config():
    """模型配置夹具"""
    return create_model_config(
        model_type=ModelType.OPENAI,
        model_name="gpt-3.5-turbo",
        api_key="test-api-key",
        base_url="https://api.openai.com/v1"
    )


@pytest.fixture
def mock_openai_response():
    """模拟OpenAI响应夹具"""
    return {
        "id": "chatcmpl-test",
        "object": "chat.completion",
        "created": 1234567890,
        "model": "gpt-3.5-turbo",
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": "Hello! How can I help you today?"
                },
                "finish_reason": "stop"
            }
        ],
        "usage": {
            "prompt_tokens": 10,
            "completion_tokens": 8,
            "total_tokens": 18
        }
    }


@pytest.fixture
def mock_stream_chunks():
    """模拟流式响应块夹具"""
    return [
        'data: {"choices": [{"delta": {"content": "Hello"}}]}\n\n',
        'data: {"choices": [{"delta": {"content": " there"}}]}\n\n',
        'data: {"choices": [{"delta": {"content": "!"}}]}\n\n',
        'data: [DONE]\n\n'
    ]


@pytest.fixture
def mock_wenxin_response():
    """模拟文心大模型响应夹具"""
    return {
        "id": "as-bcmt5ct5ub",
        "object": "chat.completion",
        "created": 1234567890,
        "result": "Hello! How can I help you today?",
        "is_truncated": False,
        "need_clear_history": False,
        "usage": {
            "prompt_tokens": 10,
            "completion_tokens": 8,
            "total_tokens": 18
        }
    }


@pytest.fixture
def mock_qianwen_response():
    """模拟千问响应夹具"""
    return {
        "output": {
            "text": "Hello! How can I help you today?",
            "finish_reason": "stop"
        },
        "usage": {
            "input_tokens": 10,
            "output_tokens": 8,
            "total_tokens": 18
        },
        "request_id": "test-request-id"
    }


@pytest.fixture
def mock_deepseek_response():
    """模拟DeepSeek响应夹具"""
    return {
        "id": "chatcmpl-test",
        "object": "chat.completion",
        "created": 1234567890,
        "model": "deepseek-chat",
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": "Hello! How can I help you today?"
                },
                "finish_reason": "stop"
            }
        ],
        "usage": {
            "prompt_tokens": 10,
            "completion_tokens": 8,
            "total_tokens": 18
        }
    }


@pytest.fixture
def mock_kimi_response():
    """模拟Kimi响应夹具"""
    return {
        "id": "chatcmpl-test",
        "object": "chat.completion",
        "created": 1234567890,
        "model": "moonshot-v1-8k",
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": "Hello! How can I help you today?"
                },
                "finish_reason": "stop"
            }
        ],
        "usage": {
            "prompt_tokens": 10,
            "completion_tokens": 8,
            "total_tokens": 18
        }
    }


@pytest.fixture
def test_session_data():
    """测试会话数据夹具"""
    return {
        "session_id": "test-session-123",
        "metadata": {
            "user_id": "user-456",
            "project_id": "project-789"
        },
        "ttl": 3600
    }


@pytest.fixture
def performance_test_data():
    """性能测试数据夹具"""
    # 生成大量测试数据
    large_data = {
        "items": []
    }
    
    for i in range(1000):
        large_data["items"].append({
            "id": i,
            "name": f"Item {i}",
            "description": f"Description for item {i}" * 10,
            "tags": [f"tag{j}" for j in range(5)],
            "metadata": {
                "created_at": f"2024-01-{(i % 30) + 1:02d}T00:00:00Z",
                "updated_at": f"2024-01-{(i % 30) + 1:02d}T12:00:00Z",
                "version": i % 10
            }
        })
    
    return large_data


# 测试标记
pytestmark = [
    pytest.mark.asyncio
]


# 测试工具函数
def assert_json_equal(actual: Dict[str, Any], expected: Dict[str, Any]):
    """断言JSON数据相等"""
    import json
    assert json.dumps(actual, sort_keys=True) == json.dumps(expected, sort_keys=True)


def assert_response_success(response, expected_status: int = 200):
    """断言响应成功"""
    assert response.status_code == expected_status
    data = response.json()
    assert data["status"] == "success"
    return data


def assert_response_error(response, expected_status: int = 400):
    """断言响应错误"""
    assert response.status_code == expected_status
    data = response.json()
    assert "detail" in data or "error" in data
    return data