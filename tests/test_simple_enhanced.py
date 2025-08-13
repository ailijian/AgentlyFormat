"""简单增强功能测试"""

import pytest
import sys
import os

# 添加src路径
sys.path.insert(0, 'src')

from agently_format.core.streaming_parser import StreamingParser


class TestBasicEnhanced:
    """基本增强功能测试"""
    
    def test_streaming_parser_creation(self):
        """测试流式解析器创建"""
        parser = StreamingParser()
        assert parser is not None
    
    def test_session_creation(self):
        """测试会话创建"""
        parser = StreamingParser()
        session_id = parser.create_session("test-session")
        assert session_id == "test-session"
        assert parser.has_session(session_id)
    
    def test_basic_parsing(self):
        """测试基本解析功能"""
        parser = StreamingParser()
        session_id = parser.create_session("basic-test")
        assert parser.has_session(session_id)
        
        # 测试简单JSON解析
        import asyncio
        
        async def test_parse():
            result = await parser.parse_chunk(
                '{"test": "value"}',
                session_id,
                is_final=True
            )
            return result
        
        result = asyncio.run(test_parse())
        assert isinstance(result, list)
        
        # 检查解析状态
        state = parser.get_parsing_state(session_id)
        assert state is not None
        assert "test" in state.current_data
        assert state.current_data["test"] == "value"
    
    def test_statistics(self):
        """测试统计信息"""
        parser = StreamingParser()
        stats = parser.get_stats()
        assert isinstance(stats, dict)
        assert "active_sessions" in stats
        assert "completed_sessions" in stats
    
    def test_incomplete_chunks_parsing(self):
        """测试不完整块解析"""
        parser = StreamingParser()
        session_id = parser.create_session("incomplete-test")
        
        chunks = [
            '{"users": [',
            '{"id": 1, "name": "Alice",',
            '"email": "alice@example.com"},',
            '{"id": 2, "name": "Bob",',
            '"email": "bob@example.com"}',
            '], "total": 2}'
        ]
        
        import asyncio
        
        async def test_parse_chunks():
            for i, chunk in enumerate(chunks):
                is_final = (i == len(chunks) - 1)
                await parser.parse_chunk(chunk, session_id, is_final=is_final)
        
        asyncio.run(test_parse_chunks())
        
        # 检查最终状态
        state = parser.get_parsing_state(session_id)
        assert state is not None
        assert "users" in state.current_data
        assert "total" in state.current_data
        assert state.current_data["total"] == 2
        assert len(state.current_data["users"]) == 2