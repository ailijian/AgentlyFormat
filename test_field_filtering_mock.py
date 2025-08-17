#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
模拟测试字段选择性流式输出功能
"""

import asyncio
import json
from src.agently_format.core.streaming_parser import StreamingParser, FieldFilter
from src.agently_format.adapters.doubao_adapter import DoubaoAdapter
from src.agently_format.types.models import ModelConfig, ModelType

class MockDoubaoAdapter(DoubaoAdapter):
    """模拟豆包适配器，用于测试字段过滤功能"""
    
    def __init__(self, config: ModelConfig):
        super().__init__(config)
    
    async def _make_request(self, **kwargs):
        """模拟API请求，返回预设的JSON响应"""
        # 模拟完整的JSON响应
        mock_response = {
            "name": "智能助手AI",
            "description": "这是一个基于深度学习技术开发的智能对话助手，能够理解自然语言并提供准确的回答和建议。它具备多轮对话能力，可以处理复杂的问题和任务。",
            "year": 2024,
            "creator": "OpenAI团队"
        }
        
        # 模拟流式响应
        json_str = json.dumps(mock_response, ensure_ascii=False)
        
        # 分块返回，模拟真实的流式响应
        chunks = []
        chunk_size = 10
        for i in range(0, len(json_str), chunk_size):
            chunks.append(json_str[i:i+chunk_size])
        
        return chunks

async def test_field_filtering_logic():
    """测试字段过滤逻辑"""
    
    # 创建模拟配置
    config = ModelConfig(
        model_type=ModelType.DOUBAO,
        model_name="test-model",
        api_key="test-key",
        base_url="https://test.com"
    )
    
    # 创建模拟适配器
    adapter = MockDoubaoAdapter(config)
    
    print("=== 测试1: 只输出description字段 ===")
    try:
        # 获取模拟响应数据
        chunks = await adapter._make_request()
        full_text = ''.join(chunks)
        
        # 创建字段过滤器
        field_filter = FieldFilter(enabled=True, include_paths=["description"], mode="include")
        
        # 解析JSON并提取字段
        try:
            data = json.loads(full_text)
            if field_filter.should_include_path("description"):
                result = data.get("description", "")
                print(f"过滤结果: {result}")
            else:
                print("字段被过滤")
        except json.JSONDecodeError as e:
            print(f"JSON解析失败: {e}")
    except Exception as e:
        print(f"测试1失败: {e}")
    
    print("\n=== 测试2: 输出name和description字段 ===")
    try:
        chunks = await adapter._make_request()
        full_text = ''.join(chunks)
        
        field_filter = FieldFilter(enabled=True, include_paths=["name", "description"], mode="include")
        
        try:
            data = json.loads(full_text)
            result = {}
            for field in ["name", "description"]:
                if field_filter.should_include_path(field):
                    result[field] = data.get(field, "")
            print(f"过滤结果: {json.dumps(result, ensure_ascii=False)}")
        except json.JSONDecodeError as e:
            print(f"JSON解析失败: {e}")
    except Exception as e:
        print(f"测试2失败: {e}")
    
    print("\n=== 测试3: 排除year和creator字段 ===")
    try:
        chunks = await adapter._make_request()
        full_text = ''.join(chunks)
        
        field_filter = FieldFilter(enabled=True, exclude_paths=["year", "creator"], mode="exclude")
        
        try:
            data = json.loads(full_text)
            result = {}
            for field in data.keys():
                if field_filter.should_include_path(field):
                    result[field] = data[field]
            print(f"过滤结果: {json.dumps(result, ensure_ascii=False)}")
        except json.JSONDecodeError as e:
            print(f"JSON解析失败: {e}")
    except Exception as e:
        print(f"测试3失败: {e}")

if __name__ == "__main__":
    asyncio.run(test_field_filtering_logic())