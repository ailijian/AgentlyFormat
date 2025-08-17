#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
字段过滤功能全面测试
测试各种字段过滤场景，验证功能的正确性和完整性
"""

import asyncio
import json
from agently_format.adapters.doubao_adapter import DoubaoAdapter

# 测试数据
test_json = {
    "languages": [
        {
            "name": "Python",
            "year": 1991,
            "creator": "Guido van Rossum",
            "description": "一种解释型、面向对象、动态数据类型的高级程序设计语言，以其简洁的语法和丰富的库而闻名。",
            "popularity": 9
        },
        {
            "name": "Java",
            "year": 1995,
            "creator": "James Gosling",
            "description": "一种广泛使用的编程语言和平台，具有跨平台、面向对象、多线程等特性，常用于企业级应用开发。",
            "popularity": 8
        },
        {
            "name": "JavaScript",
            "year": 1995,
            "creator": "Brendan Eich",
            "description": "一种脚本语言，主要用于网页开发，可实现网页的交互效果和动态内容。",
            "popularity": 7
        }
    ]
}

class MockDoubaoAdapter(DoubaoAdapter):
    """模拟DoubaoAdapter用于测试"""
    
    def __init__(self):
        # 初始化必要的属性
        self.client = None
        self.api_key = "mock_key"
        self.base_url = "mock_url"
    
    async def _stream_request(self, endpoint, payload, headers):
        """模拟流式请求，返回测试数据"""
        json_str = json.dumps(test_json, ensure_ascii=False)
        
        # 模拟流式输出，每次输出一小部分
        chunk_size = 50
        for i in range(0, len(json_str), chunk_size):
            chunk = json_str[i:i + chunk_size]
            yield f'data: {{"choices":[{{"delta":{{"content":"{chunk}"}}}}]}}\n\n'
        
        yield 'data: [DONE]\n\n'
    
    def _parse_stream_chunk(self, line):
        """解析流式数据块"""
        if line.startswith('data: ') and not line.strip().endswith('[DONE]'):
            try:
                data = json.loads(line[6:])
                if 'choices' in data and len(data['choices']) > 0:
                    delta = data['choices'][0].get('delta', {})
                    return delta.get('content', '')
            except:
                pass
        return None

async def test_exclude_fields():
    """测试排除字段功能"""
    print("\n=== 测试排除字段 (exclude year, creator) ===")
    
    adapter = MockDoubaoAdapter()
    
    result = []
    async for chunk in adapter._stream_with_field_filtering(
        payload={},
        headers={},
        include_fields=None,
        exclude_fields=["year", "creator"]
    ):
        result.append(chunk)
        print(chunk, end='', flush=True)
    
    print("\n=== 排除字段测试完成 ===")
    return ''.join(result)

async def test_include_fields():
    """测试包含字段功能"""
    print("\n=== 测试包含字段 (include name, description) ===")
    
    adapter = MockDoubaoAdapter()
    
    result = []
    async for chunk in adapter._stream_with_field_filtering(
        payload={},
        headers={},
        include_fields=["name", "description"],
        exclude_fields=None
    ):
        result.append(chunk)
        print(chunk, end='', flush=True)
    
    print("\n=== 包含字段测试完成 ===")
    return ''.join(result)

async def test_nested_field_filtering():
    """测试嵌套字段过滤"""
    print("\n=== 测试嵌套字段过滤 (include languages[0].name, languages[1].description) ===")
    
    adapter = MockDoubaoAdapter()
    
    result = []
    async for chunk in adapter._stream_with_field_filtering(
        payload={},
        headers={},
        include_fields=["languages[0].name", "languages[1].description"],
        exclude_fields=None
    ):
        result.append(chunk)
        print(chunk, end='', flush=True)
    
    print("\n=== 嵌套字段过滤测试完成 ===")
    return ''.join(result)

async def main():
    """主测试函数"""
    print("=== 字段过滤功能全面测试 ===")
    print(f"测试数据: {json.dumps(test_json, ensure_ascii=False, indent=2)}")
    
    # 测试1: 排除字段
    exclude_result = await test_exclude_fields()
    
    # 测试2: 包含字段
    include_result = await test_include_fields()
    
    # 测试3: 嵌套字段过滤
    nested_result = await test_nested_field_filtering()
    
    print("\n=== 所有测试完成 ===")
    
    # 验证结果
    print("\n=== 结果验证 ===")
    print(f"排除字段结果包含'year': {'year' in exclude_result}")
    print(f"排除字段结果包含'creator': {'creator' in exclude_result}")
    print(f"排除字段结果包含'name': {'name' in exclude_result}")
    print(f"排除字段结果包含'description': {'description' in exclude_result}")
    
if __name__ == "__main__":
    asyncio.run(main())