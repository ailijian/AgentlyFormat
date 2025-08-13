"""API测试

测试FastAPI应用的所有端点。
"""

import pytest
import json
import asyncio
from typing import Dict, Any
from unittest.mock import patch, AsyncMock

from fastapi.testclient import TestClient
import httpx

from agently_format.api.models import *
from agently_format.types.models import ModelType


class TestHealthAndStats:
    """健康检查和统计测试"""
    
    def test_health_check(self, client: TestClient):
        """测试健康检查端点"""
        response = client.get("/api/v1/health")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "success"
        assert "version" in data
        assert "uptime" in data
        assert "dependencies" in data
        
        # 检查依赖状态
        deps = data["dependencies"]
        assert deps["streaming_parser"] == "healthy"
        assert deps["json_completer"] == "healthy"
        assert deps["path_builder"] == "healthy"
        assert deps["model_adapter"] == "healthy"
    
    def test_stats_endpoint(self, client: TestClient):
        """测试统计端点"""
        response = client.get("/api/v1/stats")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "success"
        assert "total_requests" in data
        assert "active_sessions" in data
        assert "total_events" in data
        assert "average_response_time" in data
        assert "error_rate" in data
        assert "uptime" in data


class TestJSONCompletion:
    """JSON补全测试"""
    
    def test_json_complete_success(self, client: TestClient):
        """测试JSON补全成功"""
        request_data = {
            "content": '{"name": "Alice", "age": 25',
            "strategy": "smart",
            "max_depth": 10
        }
        
        response = client.post("/api/v1/json/complete", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "success"
        assert "completed_json" in data
        assert data["is_valid"] is True
        assert data["changes_made"] > 0
        assert data["confidence"] > 0
        
        # 验证补全的JSON可以解析
        completed = json.loads(data["completed_json"])
        assert completed["name"] == "Alice"
        assert completed["age"] == 25
    
    def test_json_complete_different_strategies(self, client: TestClient):
        """测试不同补全策略"""
        base_request = {
            "content": '{"data": {"value": 123',
            "max_depth": 5
        }
        
        strategies = ["conservative", "smart", "aggressive"]
        
        for strategy in strategies:
            request_data = {**base_request, "strategy": strategy}
            response = client.post("/api/v1/json/complete", json=request_data)
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            assert data["is_valid"] is True
    
    def test_json_complete_invalid_input(self, client: TestClient):
        """测试无效输入"""
        request_data = {
            "content": "",  # 空内容
            "strategy": "smart"
        }
        
        response = client.post("/api/v1/json/complete", json=request_data)
        
        # 应该返回错误或处理空输入
        assert response.status_code in [200, 400, 422]


class TestPathBuilding:
    """路径构建测试"""
    
    def test_path_build_success(self, client: TestClient, sample_json_data: Dict[str, Any]):
        """测试路径构建成功"""
        request_data = {
            "data": sample_json_data,
            "style": "dot",
            "include_arrays": True
        }
        
        response = client.post("/api/v1/path/build", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "success"
        assert "paths" in data
        assert "total_paths" in data
        assert len(data["paths"]) > 0
        assert data["total_paths"] == len(data["paths"])
        
        # 检查一些预期路径
        paths = data["paths"]
        assert "users[0].name" in paths
        assert "metadata.total" in paths
    
    def test_path_build_different_styles(self, client: TestClient):
        """测试不同路径风格"""
        test_data = {
            "user": {
                "profile": {
                    "tags": ["admin", "user"]
                }
            }
        }
        
        styles = ["dot", "slash", "bracket", "mixed"]
        
        for style in styles:
            request_data = {
                "data": test_data,
                "style": style,
                "include_arrays": True
            }
            
            response = client.post("/api/v1/path/build", json=request_data)
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            assert len(data["paths"]) > 0
    
    def test_path_build_array_options(self, client: TestClient):
        """测试数组选项"""
        test_data = {
            "items": ["a", "b", "c"]
        }
        
        # 包含数组索引
        request_with_arrays = {
            "data": test_data,
            "style": "dot",
            "include_arrays": True
        }
        
        response = client.post("/api/v1/path/build", json=request_with_arrays)
        assert response.status_code == 200
        data = response.json()
        paths_with_arrays = data["paths"]
        
        # 不包含数组索引
        request_without_arrays = {
            "data": test_data,
            "style": "dot",
            "include_arrays": False
        }
        
        response = client.post("/api/v1/path/build", json=request_without_arrays)
        assert response.status_code == 200
        data = response.json()
        paths_without_arrays = data["paths"]
        
        # 包含数组的路径应该更多
        assert len(paths_with_arrays) > len(paths_without_arrays)


class TestSessionManagement:
    """会话管理测试"""
    
    def test_create_session(self, client: TestClient):
        """测试创建会话"""
        request_data = {
            "session_id": "test-session-123",
            "ttl": 3600,
            "metadata": {
                "user_id": "user-456",
                "project_id": "project-789"
            }
        }
        
        response = client.post("/api/v1/session/create", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "success"
        assert data["session_id"] == "test-session-123"
        assert "expires_at" in data
    
    def test_create_session_auto_id(self, client: TestClient):
        """测试自动生成会话ID"""
        request_data = {
            "ttl": 1800,
            "metadata": {}
        }
        
        response = client.post("/api/v1/session/create", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "success"
        assert "session_id" in data
        assert len(data["session_id"]) > 0
    
    def test_get_session_info(self, client: TestClient):
        """测试获取会话信息"""
        # 先创建会话
        create_data = {
            "session_id": "info-test-session",
            "ttl": 3600,
            "metadata": {"test": "data"}
        }
        
        create_response = client.post("/api/v1/session/create", json=create_data)
        assert create_response.status_code == 200
        
        # 获取会话信息
        response = client.get("/api/v1/session/info-test-session")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "success"
        assert data["session_id"] == "info-test-session"
        assert "created_at" in data
        assert "expires_at" in data
        assert data["metadata"]["test"] == "data"
    
    def test_delete_session(self, client: TestClient):
        """测试删除会话"""
        # 先创建会话
        create_data = {
            "session_id": "delete-test-session",
            "ttl": 3600
        }
        
        create_response = client.post("/api/v1/session/create", json=create_data)
        assert create_response.status_code == 200
        
        # 删除会话
        response = client.delete("/api/v1/session/delete-test-session")
        
        assert response.status_code == 200
        data = response.json()
        assert "deleted successfully" in data["message"]
        
        # 再次获取应该失败
        get_response = client.get("/api/v1/session/delete-test-session")
        assert get_response.status_code == 404
    
    def test_session_not_found(self, client: TestClient):
        """测试会话不存在"""
        response = client.get("/api/v1/session/nonexistent-session")
        assert response.status_code == 404
        
        delete_response = client.delete("/api/v1/session/nonexistent-session")
        assert delete_response.status_code == 404


class TestStreamParsing:
    """流式解析测试"""
    
    def test_stream_parse_success(self, client: TestClient):
        """测试流式解析成功"""
        request_data = {
            "chunk": '{"name": "Alice", "age": 25}',
            "session_id": "stream-test-session",
            "is_final": True
        }
        
        response = client.post("/api/v1/parse/stream", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "success"
        assert data["session_id"] == "stream-test-session"
        assert "events" in data
        assert "current_data" in data
        assert "is_complete" in data
        assert "progress" in data
    
    def test_stream_parse_chunks(self, client: TestClient, incomplete_json_chunks):
        """测试分块流式解析"""
        session_id = "chunk-test-session"
        
        for i, chunk in enumerate(incomplete_json_chunks):
            is_final = (i == len(incomplete_json_chunks) - 1)
            
            request_data = {
                "chunk": chunk,
                "session_id": session_id,
                "is_final": is_final
            }
            
            response = client.post("/api/v1/parse/stream", json=request_data)
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            assert data["session_id"] == session_id
        
        # 最后一个响应应该是完成状态
        assert data["is_complete"] is True
    
    def test_stream_parse_with_schema(self, client: TestClient):
        """测试带模式的流式解析"""
        request_data = {
            "chunk": '{"user_id": 123, "username": "alice"}',
            "session_id": "schema-test-session",
            "is_final": True,
            "expected_schema": {
                "type": "object",
                "properties": {
                    "user_id": {"type": "integer"},
                    "username": {"type": "string"}
                }
            }
        }
        
        response = client.post("/api/v1/parse/stream", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"


class TestModelConfig:
    """模型配置测试"""
    
    @patch('agently_format.adapters.model_adapter.ModelAdapter.test_adapter')
    def test_create_model_config_success(self, mock_test, client: TestClient):
        """测试创建模型配置成功"""
        # 模拟测试成功
        mock_test.return_value = {
            "success": True,
            "model_name": "gpt-3.5-turbo",
            "max_tokens": 4096
        }
        
        request_data = {
            "model_type": ModelType.OPENAI.value,
            "model_name": "gpt-3.5-turbo",
            "api_key": "test-api-key",
            "base_url": "https://api.openai.com/v1",
            "timeout": 30
        }
        
        response = client.post("/api/v1/model/config", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "success"
        assert "config_id" in data
        assert "model_info" in data
        assert data["model_info"]["success"] is True
    
    @patch('agently_format.adapters.model_adapter.ModelAdapter.test_adapter')
    def test_create_model_config_failure(self, mock_test, client: TestClient):
        """测试创建模型配置失败"""
        # 模拟测试失败
        mock_test.return_value = {
            "success": False,
            "error": "Invalid API key"
        }
        
        request_data = {
            "model_type": ModelType.OPENAI.value,
            "model_name": "gpt-3.5-turbo",
            "api_key": "invalid-key",
            "base_url": "https://api.openai.com/v1"
        }
        
        response = client.post("/api/v1/model/config", json=request_data)
        
        assert response.status_code == 400
        data = response.json()
        assert "Invalid API key" in data["detail"]


class TestChat:
    """聊天测试"""
    
    @patch('agently_format.adapters.model_adapter.ModelAdapter.create_adapter')
    def test_chat_success(self, mock_create_adapter, client: TestClient, mock_openai_response):
        """测试聊天成功"""
        # 模拟适配器
        mock_adapter = AsyncMock()
        mock_adapter.chat_completion.return_value = AsyncMock(
            content="Hello! How can I help you?",
            usage={"total_tokens": 18},
            model="gpt-3.5-turbo",
            finish_reason="stop"
        )
        mock_create_adapter.return_value = mock_adapter
        
        request_data = {
            "messages": [
                {
                    "role": "user",
                    "content": "Hello"
                }
            ],
            "model_config": {
                "model_type": ModelType.OPENAI.value,
                "model_name": "gpt-3.5-turbo",
                "api_key": "test-key"
            },
            "stream": False
        }
        
        response = client.post("/api/v1/chat", json=request_data)
        
        # 调试信息
        if response.status_code != 200:
            print(f"Response status: {response.status_code}")
            print(f"Response content: {response.text}")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "success"
        assert "content" in data
        assert "usage" in data
        assert "model" in data
    
    def test_chat_missing_config(self, client: TestClient):
        """测试缺少模型配置"""
        request_data = {
            "messages": [
                {
                    "role": "user",
                    "content": "Hello"
                }
            ],
            "stream": False
        }
        
        response = client.post("/api/v1/chat", json=request_data)
        
        assert response.status_code == 400
        data = response.json()
        assert "Model config required" in data["detail"]


class TestBatchProcessing:
    """批量处理测试"""
    
    def test_batch_json_complete(self, client: TestClient):
        """测试批量JSON补全"""
        request_data = {
            "operation": "json_complete",
            "items": [
                {"content": '{"name": "Alice"'},
                {"content": '{"name": "Bob", "age": 30'},
                {"content": '{"invalid": json'}
            ]
        }
        
        response = client.post("/api/v1/batch/process", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "success"
        assert data["total_items"] == 3
        assert data["processed_items"] >= 2  # 至少处理2个有效项
        assert "results" in data
        assert "errors" in data
    
    def test_batch_path_build(self, client: TestClient):
        """测试批量路径构建"""
        request_data = {
            "operation": "path_build",
            "items": [
                {"data": {"user": {"name": "Alice"}}},
                {"data": {"items": [1, 2, 3]}},
                {"data": {}}
            ]
        }
        
        response = client.post("/api/v1/batch/process", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "success"
        assert data["total_items"] == 3
        assert data["processed_items"] == 3
        assert len(data["results"]) == 3
    
    def test_batch_unknown_operation(self, client: TestClient):
        """测试未知批量操作"""
        request_data = {
            "operation": "unknown_operation",
            "items": [{"data": "test"}]
        }
        
        response = client.post("/api/v1/batch/process", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        
        # 应该有错误
        assert data["failed_items"] > 0
        assert len(data["errors"]) > 0


@pytest.mark.asyncio
class TestWebSocket:
    """WebSocket测试"""
    
    async def test_websocket_connection(self, async_client: httpx.AsyncClient):
        """测试WebSocket连接"""
        # 注意：这里需要使用WebSocket测试客户端
        # 由于httpx.AsyncClient不直接支持WebSocket，这里只是示例结构
        pass
    
    async def test_websocket_parse_chunk(self, async_client: httpx.AsyncClient):
        """测试WebSocket解析块"""
        # WebSocket测试需要特殊的测试客户端
        pass
    
    async def test_websocket_ping_pong(self, async_client: httpx.AsyncClient):
        """测试WebSocket心跳"""
        pass


@pytest.mark.integration
class TestIntegration:
    """集成测试"""
    
    def test_full_workflow(self, client: TestClient):
        """测试完整工作流程"""
        # 1. 创建会话
        session_response = client.post("/api/v1/session/create", json={
            "ttl": 3600,
            "metadata": {"test": "integration"}
        })
        assert session_response.status_code == 200
        session_id = session_response.json()["session_id"]
        
        # 2. 流式解析
        parse_response = client.post("/api/v1/parse/stream", json={
            "chunk": '{"user": {"name": "Alice", "profile": {"age": 25}}}',
            "session_id": session_id,
            "is_final": True
        })
        assert parse_response.status_code == 200
        
        # 3. 构建路径
        parse_data = parse_response.json()
        if parse_data.get("current_data"):
            path_response = client.post("/api/v1/path/build", json={
                "data": parse_data["current_data"],
                "style": "dot",
                "include_arrays": True
            })
            assert path_response.status_code == 200
        
        # 4. 删除会话
        delete_response = client.delete(f"/api/v1/session/{session_id}")
        assert delete_response.status_code == 200
    
    def test_error_handling_workflow(self, client: TestClient):
        """测试错误处理工作流程"""
        # 测试各种错误情况的处理
        
        # 1. 无效JSON补全
        complete_response = client.post("/api/v1/json/complete", json={
            "content": "completely invalid",
            "strategy": "smart"
        })
        # 应该优雅处理错误
        assert complete_response.status_code in [200, 400]
        
        # 2. 不存在的会话
        parse_response = client.post("/api/v1/parse/stream", json={
            "chunk": '{"test": "data"}',
            "session_id": "nonexistent-session",
            "is_final": True
        })
        # 应该自动创建会话或返回错误
        assert parse_response.status_code in [200, 404]
        
        # 3. 空数据路径构建
        path_response = client.post("/api/v1/path/build", json={
            "data": {},
            "style": "dot"
        })
        assert path_response.status_code == 200