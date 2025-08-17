#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试字段选择性流式输出功能
"""

import asyncio
import os
from src.agently_format.adapters.doubao_adapter import DoubaoAdapter
from src.agently_format.types.models import ModelConfig, ModelType

async def test_field_filtering():
    """测试字段过滤功能"""
    
    # 设置环境变量（使用测试密钥）
    os.environ['DOUBAO_API_KEY'] = 'test-key-12345'
    
    # 创建模型配置
    config = ModelConfig(
        model_type=ModelType.DOUBAO,
        model_name="ep-20241230140526-8xqzr",
        api_key="test-key-12345",
        base_url="https://ark.cn-beijing.volces.com/api/v3"
    )
    
    # 创建豆包适配器
    adapter = DoubaoAdapter(config)
    
    print("=== 测试1: 只输出description字段 ===")
    async for chunk in adapter.chat_completion(
        messages=[
            {"role": "user", "content": "请生成一个关于人工智能的产品信息，包含name、description、year、creator字段"}
        ],
        stream=True,
        include_fields=["description"]
    ):
        print(chunk, end="", flush=True)
    print("\n")
    
    print("=== 测试2: 输出name和description字段 ===")
    async for chunk in adapter.chat_completion(
        messages=[
            {"role": "user", "content": "请生成一个关于人工智能的产品信息，包含name、description、year、creator字段"}
        ],
        stream=True,
        include_fields=["name", "description"]
    ):
        print(chunk, end="", flush=True)
    print("\n")
    
    print("=== 测试3: 排除year和creator字段 ===")
    async for chunk in adapter.chat_completion(
        messages=[
            {"role": "user", "content": "请生成一个关于人工智能的产品信息，包含name、description、year、creator字段"}
        ],
        stream=True,
        exclude_fields=["year", "creator"]
    ):
        print(chunk, end="", flush=True)
    print("\n")

if __name__ == "__main__":
    asyncio.run(test_field_filtering())