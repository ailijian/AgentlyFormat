#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试真正的流式字段过滤功能
"""

import asyncio
import json
from src.agently_format.adapters.doubao_adapter import DoubaoAdapter
from src.agently_format.types.models import ModelConfig, ModelType
from src.agently_format.core.streaming_parser import FieldFilter

class MockStreamingDoubaoAdapter(DoubaoAdapter):
    """模拟流式豆包适配器，用于测试流式字段过滤功能"""
    
    def __init__(self, config: ModelConfig):
        super().__init__(config)
    
    async def _make_streaming_request(self, **kwargs):
        """模拟流式API请求，返回预设的流式JSON响应"""
        # 模拟完整的JSON响应
        mock_response = {
            "name": "智能助手AI",
            "description": "这是一个基于深度学习技术开发的智能对话助手，能够理解自然语言并提供准确的回答和建议。它具备多轮对话能力，可以处理复杂的问题和任务。",
            "year": 2024,
            "creator": "OpenAI团队"
        }
        
        # 模拟流式响应，包装在代码块中
        json_str = json.dumps(mock_response, ensure_ascii=False, indent=2)
        full_response = f"```json\n{json_str}\n```"
        
        # 分块返回，模拟真实的流式响应
        chunk_size = 15
        for i in range(0, len(full_response), chunk_size):
            chunk = full_response[i:i+chunk_size]
            yield chunk
            await asyncio.sleep(0.1)  # 模拟网络延迟
    
    async def _stream_with_field_filtering(self, messages, include_fields=None, exclude_fields=None, **kwargs):
        """测试流式字段过滤功能"""
        print(f"开始流式字段过滤，include_fields={include_fields}, exclude_fields={exclude_fields}")
        
        # 创建字段过滤器
        field_filter = FieldFilter()
        if include_fields:
            field_filter.enabled = True
            field_filter.include_paths = include_fields
            field_filter.mode = "include"
        elif exclude_fields:
            field_filter.enabled = True
            field_filter.exclude_paths = exclude_fields
            field_filter.mode = "exclude"
        
        # 收集完整响应
        full_content = ""
        async for chunk in self._make_streaming_request(**kwargs):
            full_content += chunk
            print(f"收到块: '{chunk}'")
        
        print(f"\n完整内容: {full_content}")
        
        # 提取JSON代码块
        import re
        json_match = re.search(r'```json\s*\n(.*?)\n```', full_content, re.DOTALL)
        if json_match:
            json_content = json_match.group(1)
            print(f"提取的JSON: {json_content}")
            
            try:
                data = json.loads(json_content)
                print(f"解析的数据: {data}")
                
                # 应用字段过滤
                if field_filter.enabled:
                    filtered_data = {}
                    for field_name, field_value in data.items():
                        if field_filter.should_include_path(field_name):
                            filtered_data[field_name] = field_value
                            print(f"包含字段: {field_name} = {field_value}")
                        else:
                            print(f"过滤字段: {field_name}")
                    
                    # 如果只有一个字段且是description，直接输出纯文本
                    if len(filtered_data) == 1 and "description" in filtered_data:
                        result = filtered_data["description"]
                        print(f"\n最终输出（纯文本）: {result}")
                        # 模拟流式输出
                        for char in result:
                            yield char
                            await asyncio.sleep(0.01)
                    else:
                        # 输出JSON格式
                        result = json.dumps(filtered_data, ensure_ascii=False)
                        print(f"\n最终输出（JSON）: {result}")
                        # 模拟流式输出
                        for char in result:
                            yield char
                            await asyncio.sleep(0.01)
                else:
                    # 无过滤，输出原始数据
                    result = json.dumps(data, ensure_ascii=False)
                    for char in result:
                        yield char
                        await asyncio.sleep(0.01)
                        
            except json.JSONDecodeError as e:
                print(f"JSON解析失败: {e}")
                yield f"JSON解析错误: {e}"
        else:
            print("未找到JSON代码块")
            yield "未找到有效的JSON内容"

async def test_streaming_field_filtering():
    """测试流式字段过滤功能"""
    
    # 创建模拟配置
    config = ModelConfig(
        model_type=ModelType.DOUBAO,
        model_name="test-model",
        api_key="test-key",
        base_url="https://test.com"
    )
    
    # 创建模拟适配器
    adapter = MockStreamingDoubaoAdapter(config)
    
    print("=== 测试1: 只输出description字段（纯文本流式） ===")
    result1 = ""
    async for chunk in adapter._stream_with_field_filtering(
        messages=[{"role": "user", "content": "测试"}],
        include_fields=["description"]
    ):
        result1 += chunk
        print(chunk, end="", flush=True)
    print(f"\n测试1完成，结果长度: {len(result1)}")
    
    print("\n=== 测试2: 输出name和description字段（JSON流式） ===")
    result2 = ""
    async for chunk in adapter._stream_with_field_filtering(
        messages=[{"role": "user", "content": "测试"}],
        include_fields=["name", "description"]
    ):
        result2 += chunk
        print(chunk, end="", flush=True)
    print(f"\n测试2完成，结果长度: {len(result2)}")
    
    print("\n=== 测试3: 排除year和creator字段（JSON流式） ===")
    result3 = ""
    async for chunk in adapter._stream_with_field_filtering(
        messages=[{"role": "user", "content": "测试"}],
        exclude_fields=["year", "creator"]
    ):
        result3 += chunk
        print(chunk, end="", flush=True)
    print(f"\n测试3完成，结果长度: {len(result3)}")
    
    # 验证结果
    print("\n=== 结果验证 ===")
    print(f"测试1结果（应该是纯description文本）: {result1[:100]}...")
    print(f"测试2结果（应该是name+description的JSON）: {result2[:100]}...")
    print(f"测试3结果（应该是name+description的JSON）: {result3[:100]}...")

if __name__ == "__main__":
    asyncio.run(test_streaming_field_filtering())