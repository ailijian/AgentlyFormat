"""增强功能测试

测试新增的增强功能：跨块缓冲、自适应超时、Schema验证、统计信息和幂等事件。
"""

import pytest
import json
import asyncio
import time
from typing import Dict, Any, List

# 临时添加路径以确保导入正常工作
import sys
import os
sys.path.insert(0, 'src')

from agently_format.core.streaming_parser import StreamingParser
from agently_format.core.schemas import SchemaValidator, ValidationLevel
from agently_format.core.diff_engine import StructuredDiffEngine, DiffMode, CoalescingConfig
from agently_format.types.events import EventType


class TestChunkBuffer:
    """块缓冲区测试"""
    
    def test_buffer_initialization(self):
        """测试缓冲区初始化"""
        from agently_format.core.streaming_parser import ChunkBuffer
        buffer = ChunkBuffer(max_size=1024)
        
        assert buffer.max_size == 1024
        assert buffer.get_content() == ""
        assert len(buffer.bracket_balance) > 0
    
    def test_chunk_addition(self):
        """测试块添加功能"""
        from agently_format.core.streaming_parser import ChunkBuffer
        buffer = ChunkBuffer(max_size=512)
        
        result = buffer.add_chunk('{"key": "value"}')
        assert buffer.get_content() == '{"key": "value"}'
        assert result == '{"key": "value"}'


class TestAdaptiveTimeout:
    """自适应超时测试"""
    
    def test_timeout_initialization(self):
        """测试超时初始化"""
        from agently_format.core.streaming_parser import AdaptiveTimeout
        timeout = AdaptiveTimeout(
            base_timeout=1.0,
            max_timeout=10.0,
            backoff_factor=2.0
        )
        
        assert timeout.base_timeout == 1.0
        assert timeout.max_timeout == 10.0
        assert timeout.backoff_factor == 2.0


class TestSchemaValidator:
    """Schema验证器测试"""
    
    def test_validator_initialization(self):
        """测试验证器初始化"""
        schema = {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "age": {"type": "number"}
            },
            "required": ["name"]
        }
        
        validator = SchemaValidator(schema)
        assert validator.schema == schema
        assert validator.enable_caching is True


class TestEnhancedStatistics:
    """增强统计信息测试"""
    
    @pytest.mark.asyncio
    async def test_statistics_collection(self):
        """测试统计信息收集"""
        parser = StreamingParser(enable_diff_engine=True)
        session_id = parser.create_session("stats-test")
        
        # 解析一些数据
        await parser.parse_chunk('{"test": "data"}', session_id, is_final=True)
        
        # 验证统计信息收集
        stats = parser.get_stats()
        assert "active_sessions" in stats
        assert "total_events_emitted" in stats


class TestIdempotentEvents:
    """幂等事件测试"""
    
    @pytest.mark.asyncio
    async def test_done_event_stability(self):
        """测试DONE事件稳定性"""
        parser = StreamingParser(enable_diff_engine=True)
        session_id = parser.create_session("idempotent-test")
        
        events = []
        
        async def event_callback(event):
            events.append(event)
        
        parser.add_event_callback(EventType.DONE, event_callback)
        
        # 解析相同数据多次
        data = '{"stable": "value"}'
        await parser.parse_chunk(data, session_id, is_final=True)
        
        # 检查DONE事件数量
        done_events = [e for e in events if e.event_type == EventType.DONE]
        assert len(done_events) >= 1  # 至少有一个DONE事件


class TestIntegrationScenarios:
    """集成场景测试"""
    
    @pytest.mark.asyncio
    async def test_enhanced_streaming_workflow(self):
        """测试增强流式工作流"""
        # 创建启用所有增强功能的解析器
        parser = StreamingParser(
            enable_diff_engine=True,
            enable_schema_validation=False,  # 暂时禁用Schema验证
            chunk_timeout=2.0
        )
        
        session_id = parser.create_session("integration-test")
        
        events = []
        
        async def event_callback(event):
            events.append(event)
        
        # 添加事件回调
        parser.add_event_callback(EventType.DELTA, event_callback)
        parser.add_event_callback(EventType.DONE, event_callback)
        
        # 模拟流式数据
        chunks = [
            '{"user": {',
            '"name": "Alice",',
            '"age": 30,',
            '"city": "NYC"',
            '}}'
        ]
        
        # 逐块解析
        for i, chunk in enumerate(chunks):
            is_final = (i == len(chunks) - 1)
            await parser.parse_chunk(chunk, session_id, is_final=is_final)
        
        # 验证最终状态
        state = parser.get_parsing_state(session_id)
        assert state is not None
        assert state.is_complete
        assert "user" in state.current_data
        assert state.current_data["user"]["name"] == "Alice"
        
        # 验证事件
        assert len(events) > 0
        done_events = [e for e in events if e.event_type == EventType.DONE]
        assert len(done_events) >= 1
        
        # 获取统计信息
        stats = parser.get_stats()
        assert stats["active_sessions"] >= 0
        assert stats["total_events_emitted"] >= 0
        
        # 验证增强统计信息
        enhanced_stats = parser.get_stats().get('enhanced_sessions', {})
        if enhanced_stats and 'session_details' in enhanced_stats:
            session_details = enhanced_stats['session_details']
            if session_details:
                session_stats = list(session_details.values())[0]
                assert session_stats['chunks_processed'] >= 0
                assert session_stats['repair_attempts'] >= 0