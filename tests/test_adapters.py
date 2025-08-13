"""适配器测试

测试模型适配器功能。
"""

import pytest
import json
import asyncio
from typing import Dict, Any, AsyncGenerator
from unittest.mock import AsyncMock, MagicMock, patch, Mock

import httpx

from agently_format.adapters.model_adapter import ModelAdapter, BaseModelAdapter, ModelResponse
from agently_format.adapters.openai_adapter import OpenAIAdapter
from agently_format.adapters.doubao_adapter import DoubaoAdapter
from agently_format.adapters.custom_adapter import CustomAdapter, create_custom_adapter
from agently_format.adapters.wenxin_adapter import WenxinAdapter
from agently_format.adapters.qianwen_adapter import QianwenAdapter
from agently_format.adapters.deepseek_adapter import DeepSeekAdapter
from agently_format.adapters.kimi_adapter import KimiAdapter
from agently_format.types.models import ModelType, create_model_config


class TestBaseModelAdapter:
    """基础模型适配器测试"""
    
    def test_adapter_initialization(self):
        """测试适配器初始化"""
        config = create_model_config(
            model_type=ModelType.OPENAI,
            model_name="gpt-3.5-turbo",
            api_key="test-key"
        )
        
        adapter = OpenAIAdapter(config)
        
        assert adapter.config == config
        assert adapter.model_name == "gpt-3.5-turbo"
        assert adapter.api_key == "test-key"
        # 客户端延迟初始化，初始为None
        assert adapter.client is None
        
        # 调用_setup_client后应该不为None
        adapter._setup_client()
        assert adapter.client is not None
    
    @pytest.mark.asyncio
    async def test_adapter_close(self):
        """测试适配器关闭"""
        config = create_model_config(
            model_type=ModelType.OPENAI,
            model_name="gpt-3.5-turbo",
            api_key="test-key"
        )
        
        adapter = OpenAIAdapter(config)
        adapter._setup_client()  # 确保客户端已初始化
        
        # 关闭适配器
        await adapter.close()
        
        # 验证客户端已关闭
        assert adapter.client.is_closed


class TestOpenAIAdapter:
    """OpenAI适配器测试"""
    
    def test_openai_adapter_creation(self):
        """测试OpenAI适配器创建"""
        config = create_model_config(
            model_type=ModelType.OPENAI,
            model_name="gpt-4",
            api_key="test-openai-key",
            base_url="https://api.openai.com/v1"
        )
        
        adapter = OpenAIAdapter(config)
        
        assert adapter.model_name == "gpt-4"
        assert adapter.api_key == "test-openai-key"
        assert adapter.base_url == "https://api.openai.com/v1"
    
    def test_build_request_payload(self):
        """测试构建请求载荷"""
        config = create_model_config(
            model_type=ModelType.OPENAI,
            model_name="gpt-3.5-turbo",
            api_key="test-key"
        )
        
        adapter = OpenAIAdapter(config)
        
        messages = [
            {"role": "user", "content": "Hello"}
        ]
        
        payload = adapter._build_request_payload(messages, stream=False)
        
        assert payload["model"] == "gpt-3.5-turbo"
        assert payload["messages"] == messages
        assert "stream" not in payload  # stream=False时不包含stream字段
        assert "temperature" in payload
        assert "max_tokens" in payload
    
    def test_parse_response(self, mock_openai_response):
        """测试解析响应"""
        config = create_model_config(
            model_type=ModelType.OPENAI,
            model_name="gpt-3.5-turbo",
            api_key="test-key"
        )
        
        adapter = OpenAIAdapter(config)
        
        response = adapter._parse_response(mock_openai_response)
        
        assert isinstance(response, ModelResponse)
        assert response.content == "Hello! How can I help you today?"
        assert response.model == "gpt-3.5-turbo"
        assert response.finish_reason == "stop"
        assert response.usage["total_tokens"] == 18
    
    @pytest.mark.asyncio
    async def test_parse_stream_chunk(self, mock_stream_chunks):
        """测试解析流式响应块"""
        config = create_model_config(
            model_type=ModelType.OPENAI,
            model_name="gpt-3.5-turbo",
            api_key="test-key"
        )
        
        adapter = OpenAIAdapter(config)
        
        chunks = []
        for chunk_data in mock_stream_chunks[:-1]:  # 排除 [DONE]
            chunk = await adapter._parse_stream_chunk(chunk_data)
            if chunk:
                chunks.append(chunk)
        
        assert len(chunks) > 0
        
        # 验证内容
        full_content = "".join(chunks)
        assert "Hello there!" in full_content
    
    def test_get_auth_headers(self):
        """测试获取认证头"""
        config = create_model_config(
            model_type=ModelType.OPENAI,
            model_name="gpt-3.5-turbo",
            api_key="test-openai-key"
        )
        
        adapter = OpenAIAdapter(config)
        
        headers = adapter._get_auth_headers()
        
        assert "Authorization" in headers
        assert headers["Authorization"] == "Bearer test-openai-key"
        assert headers["Content-Type"] == "application/json"
    
    def test_get_model_info(self):
        """测试获取模型信息"""
        config = create_model_config(
            model_type=ModelType.OPENAI,
            model_name="gpt-4",
            api_key="test-key"
        )
        
        adapter = OpenAIAdapter(config)
        
        info = adapter.get_model_info()
        
        assert "max_tokens" in info
        assert "context_window" in info
        assert info["max_tokens"] > 0
        assert info["context_window"] > 0
    
    @pytest.mark.asyncio
    async def test_validate_api_key_success(self):
        """测试API密钥验证成功"""
        config = create_model_config(
            model_type=ModelType.OPENAI,
            model_name="gpt-3.5-turbo",
            api_key="valid-key"
        )
        
        adapter = OpenAIAdapter(config)
        
        # 模拟成功响应
        with patch.object(adapter, '_make_request') as mock_request:
            mock_request.return_value = {
                "choices": [{"message": {"content": "test"}}]
            }
            
            is_valid = await adapter.validate_api_key()
            assert is_valid is True
    
    @pytest.mark.asyncio
    async def test_validate_api_key_failure(self):
        """测试API密钥验证失败"""
        config = create_model_config(
            model_type=ModelType.OPENAI,
            model_name="gpt-3.5-turbo",
            api_key="invalid-key"
        )
        
        adapter = OpenAIAdapter(config)
        
        # 模拟失败响应
        with patch.object(adapter, '_make_request') as mock_request:
            mock_request.side_effect = Exception("Invalid API key")
            
            is_valid = await adapter.validate_api_key()
            assert is_valid is False
    
    @pytest.mark.asyncio
    async def test_chat_completion_non_stream(self):
        """测试非流式聊天补全"""
        config = create_model_config(
            model_type=ModelType.OPENAI,
            model_name="gpt-3.5-turbo",
            api_key="test-key"
        )
        
        adapter = OpenAIAdapter(config)
        
        messages = [{"role": "user", "content": "Hello"}]
        
        # 模拟响应
        with patch.object(adapter, '_make_request') as mock_request:
            mock_request.return_value = {
                "choices": [{
                    "message": {
                        "content": "Hello! How can I help?",
                        "role": "assistant"
                    },
                    "finish_reason": "stop"
                }],
                "model": "gpt-3.5-turbo",
                "usage": {"total_tokens": 15}
            }
            
            response = await adapter.chat_completion(messages, stream=False)
            
            assert isinstance(response, ModelResponse)
            assert response.content == "Hello! How can I help?"
            assert response.model == "gpt-3.5-turbo"
    
    @pytest.mark.asyncio
    async def test_chat_completion_stream(self):
        """测试流式聊天补全"""
        config = create_model_config(
            model_type=ModelType.OPENAI,
            model_name="gpt-3.5-turbo",
            api_key="test-key"
        )
        
        adapter = OpenAIAdapter(config)
        
        messages = [{"role": "user", "content": "Hello"}]
        
        # 模拟流式响应
        async def mock_stream():
            chunks = [
                'data: {"choices": [{"delta": {"content": "Hello"}}]}\n\n',
                'data: {"choices": [{"delta": {"content": " there"}}]}\n\n',
                'data: [DONE]\n\n'
            ]
            for chunk in chunks:
                yield chunk
        
        with patch.object(adapter, '_stream_request') as mock_stream_request:
            mock_stream_request.return_value = mock_stream()
            
            chunks = []
            stream_generator = adapter.chat_completion(messages, stream=True)
            async for chunk in stream_generator:
                chunks.append(chunk)
            
            assert len(chunks) > 0
            full_content = "".join(chunks)
            assert "Hello there" in full_content


class TestDoubaoAdapter:
    """豆包适配器测试"""
    
    def test_doubao_adapter_creation(self):
        """测试豆包适配器创建"""
        config = create_model_config(
            model_type=ModelType.DOUBAO,
            model_name="doubao-pro-4k",
            api_key="test-doubao-key",
            base_url="https://ark.cn-beijing.volces.com/api/v3"
        )
        
        adapter = DoubaoAdapter(config)
        
        assert adapter.model_name == "doubao-pro-4k"
        assert adapter.api_key == "test-doubao-key"
        assert "volces.com" in adapter.base_url
    
    def test_doubao_auth_headers(self):
        """测试豆包认证头"""
        config = create_model_config(
            model_type=ModelType.DOUBAO,
            model_name="doubao-pro-4k",
            api_key="test-doubao-key"
        )
        
        adapter = DoubaoAdapter(config)
        
        headers = adapter._get_auth_headers()
        
        assert "Authorization" in headers
        assert headers["Authorization"] == "Bearer test-doubao-key"
    
    def test_doubao_model_info(self):
        """测试豆包模型信息"""
        config = create_model_config(
            model_type=ModelType.DOUBAO,
            model_name="doubao-pro-32k",
            api_key="test-key"
        )
        
        adapter = DoubaoAdapter(config)
        
        info = adapter.get_model_info()
        
        assert "max_tokens" in info
        assert "context_window" in info
        # 32k模型应该有更大的上下文窗口
        assert info["context_window"] >= 32000


class TestCustomAdapter:
    """自定义适配器测试"""
    
    def test_custom_adapter_creation(self):
        """测试自定义适配器创建"""
        config = create_model_config(
            model_type=ModelType.CUSTOM,
            model_name="custom-model",
            api_key="custom-key",
            base_url="https://custom-api.example.com"
        )
        
        adapter = CustomAdapter(config)
        
        assert adapter.model_name == "custom-model"
        assert adapter.api_key == "custom-key"
        assert adapter.base_url == "https://custom-api.example.com"
    
    def test_custom_adapter_with_transformers(self):
        """测试带转换器的自定义适配器"""
        def custom_request_transformer(messages, **kwargs):
            return {
                "input": messages,
                "parameters": kwargs
            }
        
        def custom_response_parser(response):
            return ModelResponse(
                content=response.get("output", ""),
                model="custom-model",
                usage={"tokens": 10},
                finish_reason="stop"
            )
        
        config = create_model_config(
            model_type=ModelType.CUSTOM,
            model_name="custom-model",
            api_key="custom-key"
        )
        
        adapter = CustomAdapter(
            config,
            request_transformer=custom_request_transformer,
            response_parser=custom_response_parser
        )
        
        # 测试请求转换
        messages = [{"role": "user", "content": "test"}]
        payload = adapter._build_request_payload(messages)
        
        assert "input" in payload
        assert "parameters" in payload
        assert payload["input"] == messages
        
        # 测试响应解析
        mock_response = {"output": "Custom response"}
        parsed = adapter._parse_response(mock_response)
        
        assert isinstance(parsed, ModelResponse)
        assert parsed.content == "Custom response"
        assert parsed.model == "custom-model"
    
    def test_create_custom_adapter_helper(self):
        """测试自定义适配器创建助手"""
        def custom_auth_handler(api_key):
            return {"X-API-Key": api_key}
        
        adapter = create_custom_adapter(
            model_name="helper-model",
            api_key="helper-key",
            base_url="https://helper-api.com",
            auth_handler=custom_auth_handler
        )
        
        assert isinstance(adapter, CustomAdapter)
        assert adapter.model_name == "helper-model"
        
        # 测试自定义认证
        headers = adapter._get_auth_headers()
        assert "X-API-Key" in headers
        assert headers["X-API-Key"] == "helper-key"


class TestModelAdapterFactory:
    """模型适配器工厂测试"""
    
    def test_register_adapter(self):
        """测试注册适配器"""
        # 保存原来的适配器
        original_adapter = ModelAdapter._adapters.get(ModelType.CUSTOM)
        
        try:
            # 创建自定义适配器类
            class TestAdapter(BaseModelAdapter):
                async def chat_completion(self, messages, **kwargs):
                    return ModelResponse(
                        content="test response",
                        model=self.model_name,
                        usage={},
                        finish_reason="stop"
                    )
                
                def _build_request_payload(self, messages, **kwargs):
                    return {"messages": messages, "model": self.model_name}
                
                def _parse_response(self, response_data):
                    return ModelResponse(
                        content="test response",
                        model=self.model_name,
                        usage={},
                        finish_reason="stop"
                    )
                
                async def _parse_stream_chunk(self, chunk):
                    return "test chunk"
                
                def _get_auth_headers(self):
                    return {"Authorization": f"Bearer {self.api_key}"}
            
            # 注册适配器 - 使用 ModelType.CUSTOM 而不是字符串
            ModelAdapter.register_adapter(ModelType.CUSTOM, TestAdapter)
            
            # 验证注册成功
            supported_models = ModelAdapter.get_supported_models()
            assert ModelType.CUSTOM in supported_models
            
        finally:
            # 恢复原来的适配器
            if original_adapter:
                ModelAdapter.register_adapter(ModelType.CUSTOM, original_adapter)
            else:
                # 如果原来没有注册，则删除
                if ModelType.CUSTOM in ModelAdapter._adapters:
                    del ModelAdapter._adapters[ModelType.CUSTOM]
    
    def test_create_adapter(self):
        """测试创建适配器"""
        config = create_model_config(
            model_type=ModelType.OPENAI,
            model_name="gpt-3.5-turbo",
            api_key="test-key"
        )
        
        adapter = ModelAdapter.create_adapter(config)
        
        assert isinstance(adapter, OpenAIAdapter)
        assert adapter.model_name == "gpt-3.5-turbo"
    
    def test_create_adapter_unknown_type(self):
        """测试创建未知类型适配器"""
        # 测试无效的 model_type 字符串会在 create_model_config 时抛出 ValueError
        with pytest.raises(ValueError, match="'unknown_type' is not a valid ModelType"):
            create_model_config(
                model_type="unknown_type",
                model_name="unknown-model",
                api_key="test-key"
            )
    
    def test_get_supported_models(self):
        """测试获取支持的模型"""
        supported = ModelAdapter.get_supported_models()
        
        assert isinstance(supported, list)
        # 检查 ModelType 枚举值
        supported_values = [model_type.value for model_type in supported]
        assert "openai" in supported_values
        assert "doubao" in supported_values
        assert "custom" in supported_values
    
    @pytest.mark.asyncio
    async def test_test_adapter_success(self):
        """测试适配器测试成功"""
        config = create_model_config(
            model_type=ModelType.OPENAI,
            model_name="gpt-3.5-turbo",
            api_key="valid-key"
        )
        
        # 模拟成功的适配器
        with patch('agently_format.adapters.openai_adapter.OpenAIAdapter._non_stream_chat_completion') as mock_chat:
            mock_response = ModelResponse(
                content="Test response",
                model="gpt-3.5-turbo",
                usage={"total_tokens": 10},
                finish_reason="stop"
            )
            mock_chat.return_value = mock_response
            
            result = await ModelAdapter.test_adapter(config)
            
            assert result["success"] is True
            assert "model_name" in result
            assert "response_length" in result
            assert result["model_name"] == "gpt-3.5-turbo"
    
    @pytest.mark.asyncio
    async def test_test_adapter_failure(self):
        """测试适配器测试失败"""
        config = create_model_config(
            model_type=ModelType.OPENAI,
            model_name="gpt-3.5-turbo",
            api_key="invalid-key"
        )
        
        # 模拟失败的适配器
        with patch('agently_format.adapters.openai_adapter.OpenAIAdapter.chat_completion') as mock_chat:
            mock_chat.side_effect = Exception("Invalid API key")
            
            result = await ModelAdapter.test_adapter(config)
            
            assert result["success"] is False
            assert "error" in result
            assert "Invalid API key" in result["error"]


@pytest.mark.integration
class TestAdapterIntegration:
    """适配器集成测试"""
    
    @pytest.mark.asyncio
    async def test_adapter_lifecycle(self):
        """测试适配器生命周期"""
        config = create_model_config(
            model_type=ModelType.OPENAI,
            model_name="gpt-3.5-turbo",
            api_key="test-key"
        )
        
        # 创建适配器
        adapter = ModelAdapter.create_adapter(config)
        
        # 验证初始化
        assert adapter is not None
        assert adapter.model_name == "gpt-3.5-turbo"
        
        # 模拟使用
        with patch.object(adapter, '_non_stream_chat_completion') as mock_chat:
            mock_chat.return_value = ModelResponse(
                content="Test response",
                model="gpt-3.5-turbo",
                usage={"total_tokens": 10},
                finish_reason="stop"
            )
            
            response = await adapter.chat_completion([{"role": "user", "content": "test"}])
            assert response.content == "Test response"
        
        # 关闭适配器
        adapter._setup_client()  # 确保客户端已初始化
        await adapter.close()
        assert adapter.client.is_closed
    
    @pytest.mark.asyncio
    async def test_multiple_adapters(self):
        """测试多个适配器"""
        # 创建多个不同类型的适配器
        configs = [
            create_model_config(
                model_type=ModelType.OPENAI,
                model_name="gpt-3.5-turbo",
                api_key="openai-key"
            ),
            create_model_config(
                model_type=ModelType.DOUBAO,
                model_name="doubao-pro-4k",
                api_key="doubao-key"
            ),
            create_model_config(
                model_type=ModelType.CUSTOM,
                model_name="custom-model",
                api_key="custom-key",
                base_url="https://custom.api.com"
            )
        ]
        
        adapters = []
        
        try:
            # 创建所有适配器
            for config in configs:
                adapter = ModelAdapter.create_adapter(config)
                adapters.append(adapter)
            
            # 验证所有适配器都正确创建
            assert len(adapters) == 3
            assert isinstance(adapters[0], OpenAIAdapter)
            assert isinstance(adapters[1], DoubaoAdapter)
            assert isinstance(adapters[2], CustomAdapter)
            
        finally:
            # 清理所有适配器
            for adapter in adapters:
                await adapter.close()


@pytest.mark.performance
class TestAdapterPerformance:
    """适配器性能测试"""
    
    @pytest.mark.asyncio
    async def test_concurrent_requests(self):
        """测试并发请求"""
        config = create_model_config(
            model_type=ModelType.OPENAI,
            model_name="gpt-3.5-turbo",
            api_key="test-key"
        )
        
        adapter = ModelAdapter.create_adapter(config)
        
        # 模拟并发请求
        async def mock_request():
            with patch.object(adapter, '_non_stream_chat_completion') as mock_chat:
                mock_chat.return_value = ModelResponse(
                    content="Response",
                    model="gpt-3.5-turbo",
                    usage={"total_tokens": 5},
                    finish_reason="stop"
                )
                return await adapter.chat_completion([{"role": "user", "content": "test"}])
        
        # 并发执行多个请求
        tasks = [mock_request() for _ in range(10)]
        responses = await asyncio.gather(*tasks)
        
        # 验证所有请求都成功
        assert len(responses) == 10
        for response in responses:
            assert response.content == "Response"
        
        await adapter.close()
    
    @pytest.mark.asyncio
    async def test_adapter_creation_performance(self):
        """测试适配器创建性能"""
        import time
        
        config = create_model_config(
            model_type=ModelType.OPENAI,
            model_name="gpt-3.5-turbo",
            api_key="test-key"
        )
        
        start_time = time.time()
        
        # 创建多个适配器
        adapters = []
        for _ in range(100):
            adapter = ModelAdapter.create_adapter(config)
            adapters.append(adapter)
        
        end_time = time.time()
        creation_time = end_time - start_time
        
        # 创建时间应该在合理范围内
        assert creation_time < 1.0  # 1秒内创建100个适配器
        
        # 清理
        for adapter in adapters:
            await adapter.close()


class TestWenxinAdapter:
    """文心大模型适配器测试"""
    
    def test_wenxin_adapter_creation(self):
        """测试文心适配器创建"""
        config = create_model_config(
            model_type=ModelType.BAIDU,
            model_name="ernie-4.0-8k",
            api_key="test-wenxin-key",
            base_url="https://aip.baidubce.com"
        )
        
        adapter = WenxinAdapter(config)
        
        assert adapter.model_name == "ernie-4.0-8k"
        assert adapter.api_key == "test-wenxin-key"
        assert "baidubce.com" in adapter.base_url
    
    def test_wenxin_model_mapping(self):
        """测试文心模型映射"""
        config = create_model_config(
            model_type=ModelType.BAIDU,
            model_name="ernie-3.5-8k",
            api_key="test-key"
        )
        
        adapter = WenxinAdapter(config)
        
        # 测试模型映射
        mapped_name = adapter._get_mapped_model_name("ernie-3.5-8k")
        assert mapped_name == "ERNIE-3.5-8K"
    
    def test_wenxin_auth_headers(self):
        """测试文心认证头"""
        config = create_model_config(
            model_type=ModelType.BAIDU,
            model_name="ernie-4.0-8k",
            api_key="test-wenxin-key"
        )
        
        adapter = WenxinAdapter(config)
        
        headers = adapter._get_auth_headers()
        
        assert "Content-Type" in headers
        assert headers["Content-Type"] == "application/json"
    
    @pytest.mark.asyncio
    async def test_wenxin_get_access_token(self):
        """测试获取访问令牌"""
        config = create_model_config(
            model_type=ModelType.BAIDU,
            model_name="ernie-4.0-8k",
            api_key="test-api-key",
            api_secret="test-secret-key"
        )
        
        adapter = WenxinAdapter(config)
        adapter._setup_client()  # 确保客户端已初始化
        
        # 模拟HTTP客户端响应
        with patch.object(adapter.client, 'post') as mock_post:
            mock_response = Mock()
            mock_response.json.return_value = {
                "access_token": "test-access-token",
                "expires_in": 2592000
            }
            mock_response.raise_for_status.return_value = None
            mock_post.return_value = mock_response
            
            token = await adapter._get_access_token()
            assert token == "test-access-token"
    
    def test_wenxin_model_info(self):
        """测试文心模型信息"""
        config = create_model_config(
            model_type=ModelType.BAIDU,
            model_name="ernie-4.0-8k",
            api_key="test-key"
        )
        
        adapter = WenxinAdapter(config)
        
        info = adapter.get_model_info()
        
        assert "max_tokens" in info
        assert "context_window" in info
        assert info["max_tokens"] > 0
        assert info["context_window"] > 0


class TestQianwenAdapter:
    """千问适配器测试"""
    
    def test_qianwen_adapter_creation(self):
        """测试千问适配器创建"""
        config = create_model_config(
            model_type=ModelType.QWEN,
            model_name="qwen-turbo",
            api_key="test-qianwen-key",
            base_url="https://dashscope.aliyuncs.com/api/v1"
        )
        
        adapter = QianwenAdapter(config)
        
        assert adapter.model_name == "qwen-turbo"
        assert adapter.api_key == "test-qianwen-key"
        assert "dashscope.aliyuncs.com" in adapter.base_url
    
    def test_qianwen_model_mapping(self):
        """测试千问模型映射"""
        config = create_model_config(
            model_type=ModelType.QWEN,
            model_name="qwen-plus",
            api_key="test-key"
        )
        
        adapter = QianwenAdapter(config)
        
        # 测试模型映射
        mapped_name = adapter._get_mapped_model_name("qwen-plus")
        assert mapped_name == "qwen-plus"
    
    def test_qianwen_auth_headers(self):
        """测试千问认证头"""
        config = create_model_config(
            model_type=ModelType.QWEN,
            model_name="qwen-turbo",
            api_key="test-qianwen-key"
        )
        
        adapter = QianwenAdapter(config)
        
        headers = adapter._get_auth_headers()
        
        assert "Authorization" in headers
        assert headers["Authorization"] == "Bearer test-qianwen-key"
        assert headers["Content-Type"] == "application/json"
    
    def test_qianwen_model_info(self):
        """测试千问模型信息"""
        config = create_model_config(
            model_type=ModelType.QWEN,
            model_name="qwen-max",
            api_key="test-key"
        )
        
        adapter = QianwenAdapter(config)
        
        info = adapter.get_model_info()
        
        assert "max_tokens" in info
        assert "context_window" in info
        assert info["max_tokens"] > 0
        assert info["context_window"] > 0
    
    @pytest.mark.asyncio
    async def test_qianwen_validate_api_key_success(self):
        """测试千问API密钥验证成功"""
        config = create_model_config(
            model_type=ModelType.QWEN,
            model_name="qwen-turbo",
            api_key="valid-key"
        )
        
        adapter = QianwenAdapter(config)
        
        # 模拟成功响应
        with patch.object(adapter, '_make_request') as mock_request:
            mock_request.return_value = {
                "output": {"text": "test response"},
                "usage": {"total_tokens": 10}
            }
            
            is_valid = await adapter.validate_api_key()
            assert is_valid is True


class TestDeepSeekAdapter:
    """DeepSeek适配器测试"""
    
    def test_deepseek_adapter_creation(self):
        """测试DeepSeek适配器创建"""
        config = create_model_config(
            model_type=ModelType.DEEPSEEK,
            model_name="deepseek-chat",
            api_key="test-deepseek-key",
            base_url="https://api.deepseek.com/v1"
        )
        
        adapter = DeepSeekAdapter(config)
        
        assert adapter.model_name == "deepseek-chat"
        assert adapter.api_key == "test-deepseek-key"
        assert "deepseek.com" in adapter.base_url
    
    def test_deepseek_model_mapping(self):
        """测试DeepSeek模型映射"""
        config = create_model_config(
            model_type=ModelType.DEEPSEEK,
            model_name="deepseek-coder",
            api_key="test-key"
        )
        
        adapter = DeepSeekAdapter(config)
        
        # 测试模型映射
        mapped_name = adapter._get_mapped_model_name("deepseek-coder")
        assert mapped_name == "deepseek-coder"
    
    def test_deepseek_auth_headers(self):
        """测试DeepSeek认证头"""
        config = create_model_config(
            model_type=ModelType.DEEPSEEK,
            model_name="deepseek-chat",
            api_key="test-deepseek-key"
        )
        
        adapter = DeepSeekAdapter(config)
        
        headers = adapter._get_auth_headers()
        
        assert "Authorization" in headers
        assert headers["Authorization"] == "Bearer test-deepseek-key"
        assert headers["Content-Type"] == "application/json"
    
    def test_deepseek_model_info(self):
        """测试DeepSeek模型信息"""
        config = create_model_config(
            model_type=ModelType.DEEPSEEK,
            model_name="deepseek-reasoner",
            api_key="test-key"
        )
        
        adapter = DeepSeekAdapter(config)
        
        info = adapter.get_model_info()
        
        assert "max_tokens" in info
        assert "context_window" in info
        assert info["max_tokens"] > 0
        assert info["context_window"] > 0
    
    @pytest.mark.asyncio
    async def test_deepseek_validate_api_key_success(self):
        """测试DeepSeek API密钥验证成功"""
        config = create_model_config(
            model_type=ModelType.DEEPSEEK,
            model_name="deepseek-chat",
            api_key="valid-key"
        )
        
        adapter = DeepSeekAdapter(config)
        
        # 模拟成功响应
        with patch.object(adapter, '_make_request') as mock_request:
            mock_request.return_value = {
                "choices": [{"message": {"content": "test response"}}],
                "usage": {"total_tokens": 10}
            }
            
            is_valid = await adapter.validate_api_key()
            assert is_valid is True


class TestKimiAdapter:
    """Kimi适配器测试"""
    
    def test_kimi_adapter_creation(self):
        """测试Kimi适配器创建"""
        config = create_model_config(
            model_type=ModelType.KIMI,
            model_name="moonshot-v1-8k",
            api_key="test-kimi-key",
            base_url="https://api.moonshot.cn/v1"
        )
        
        adapter = KimiAdapter(config)
        
        assert adapter.model_name == "moonshot-v1-8k"
        assert adapter.api_key == "test-kimi-key"
        assert "moonshot.cn" in adapter.base_url
    
    def test_kimi_model_mapping(self):
        """测试Kimi模型映射"""
        config = create_model_config(
            model_type=ModelType.KIMI,
            model_name="moonshot-v1-32k",
            api_key="test-key"
        )
        
        adapter = KimiAdapter(config)
        
        # 测试模型映射
        mapped_name = adapter._get_mapped_model_name("moonshot-v1-32k")
        assert mapped_name == "moonshot-v1-32k"
    
    def test_kimi_auth_headers(self):
        """测试Kimi认证头"""
        config = create_model_config(
            model_type=ModelType.KIMI,
            model_name="moonshot-v1-8k",
            api_key="test-kimi-key"
        )
        
        adapter = KimiAdapter(config)
        
        headers = adapter._get_auth_headers()
        
        assert "Authorization" in headers
        assert headers["Authorization"] == "Bearer test-kimi-key"
        assert headers["Content-Type"] == "application/json"
    
    def test_kimi_model_info(self):
        """测试Kimi模型信息"""
        config = create_model_config(
            model_type=ModelType.KIMI,
            model_name="moonshot-v1-128k",
            api_key="test-key"
        )
        
        adapter = KimiAdapter(config)
        
        info = adapter.get_model_info()
        
        assert "max_tokens" in info
        assert "context_window" in info
        assert info["max_tokens"] > 0
        assert info["context_window"] > 0
    
    @pytest.mark.asyncio
    async def test_kimi_validate_api_key_success(self):
        """测试Kimi API密钥验证成功"""
        config = create_model_config(
            model_type=ModelType.KIMI,
            model_name="moonshot-v1-8k",
            api_key="valid-key"
        )
        
        adapter = KimiAdapter(config)
        
        # 模拟成功响应
        with patch.object(adapter, '_make_request') as mock_request:
            mock_request.return_value = {
                "choices": [{"message": {"content": "test response"}}],
                "usage": {"total_tokens": 10}
            }
            
            is_valid = await adapter.validate_api_key()
            assert is_valid is True