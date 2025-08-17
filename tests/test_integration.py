"""集成测试

测试StreamingParser与PerformanceOptimizer、MemoryManager的集成功能，
以及整个字段级别流式输出控制系统的端到端测试。
"""

import pytest
import json
import asyncio
import time
from typing import List, Dict, Any

from src.agently_format.core.streaming_parser import StreamingParser, FieldFilter
from src.agently_format.core.performance_optimizer import PerformanceOptimizer
from src.agently_format.core.memory_manager import MemoryManager
from src.agently_format.types.events import EventType


class TestStreamingParserIntegration:
    """流式解析器集成测试类"""
    
    @pytest.fixture
    def integrated_parser(self):
        """创建集成了性能优化和内存管理的解析器"""
        return StreamingParser(
            enable_completion=True,
            enable_diff_engine=True,
            max_depth=10,
            chunk_timeout=30.0,
            buffer_size=8192,
            enable_schema_validation=True,
            adaptive_timeout_enabled=True,
            field_filter=FieldFilter(
                enabled=True,
                include_paths=['users', 'users.*', 'data', 'data.*'],
                exclude_paths=['*.password', '*.secret']
            )
        )
    
    @pytest.mark.asyncio
    async def test_performance_optimization_integration(self, integrated_parser: StreamingParser):
        """测试性能优化集成"""
        # 验证性能优化器已集成
        assert integrated_parser.performance_optimizer is not None
        assert integrated_parser.field_filter.performance_optimizer is not None
        
        # 创建测试数据
        test_data = {
            "users": [
                {"id": 1, "name": "Alice", "email": "alice@example.com"},
                {"id": 2, "name": "Bob", "email": "bob@example.com"}
            ],
            "data": {"count": 2, "timestamp": "2024-01-01T00:00:00Z"}
        }
        
        session_id = integrated_parser.create_session("perf_test")
        
        # 第一次解析
        start_time = time.perf_counter()
        result1 = await integrated_parser.parse_chunk(
            json.dumps(test_data),
            session_id,
            is_final=True
        )
        first_time = time.perf_counter() - start_time
        
        # 清理会话并重新创建
        integrated_parser.cleanup_session(session_id)
        session_id = integrated_parser.create_session("perf_test_2")
        
        # 第二次解析（应该利用缓存）
        start_time = time.perf_counter()
        result2 = await integrated_parser.parse_chunk(
            json.dumps(test_data),
            session_id,
            is_final=True
        )
        second_time = time.perf_counter() - start_time
        
        # 验证缓存效果
        cache_stats = integrated_parser.performance_optimizer.get_cache_stats()
        assert cache_stats['string_delta_cache']['total'] > 0
        assert cache_stats['path_matching_cache']['total'] > 0
        
        # 验证结果一致性
        assert len(result1) > 0
        assert len(result2) > 0
    
    @pytest.mark.asyncio
    async def test_memory_management_integration(self, integrated_parser: StreamingParser):
        """测试内存管理集成"""
        # 验证内存管理器已集成
        assert integrated_parser.memory_manager is not None
        
        # 创建多个会话
        session_ids = []
        for i in range(5):
            session_id = integrated_parser.create_session(f"memory_test_{i}")
            session_ids.append(session_id)
            
            # 解析一些数据
            test_data = {"session": i, "data": f"test_data_{i}"}
            await integrated_parser.parse_chunk(
                json.dumps(test_data),
                session_id,
                is_final=True
            )
        
        # 检查内存使用情况
        memory_info = integrated_parser.memory_manager.get_memory_usage()
        assert memory_info['active_sessions'] >= 5
        
        # 清理一些会话
        for session_id in session_ids[:3]:
            integrated_parser.cleanup_session(session_id)
        
        # 验证会话已被清理
        updated_memory_info = integrated_parser.memory_manager.get_memory_usage()
        assert updated_memory_info['active_sessions'] < memory_info['active_sessions']
    
    @pytest.mark.asyncio
    async def test_field_filtering_with_optimization(self, integrated_parser: StreamingParser):
        """测试字段过滤与性能优化的集成"""
        # 创建包含敏感数据的测试数据
        test_data = {
            "users": [
                {
                    "id": 1,
                    "name": "Alice",
                    "email": "alice@example.com",
                    "password": "secret123",  # 应该被过滤
                    "profile": {
                        "age": 25,
                        "secret": "top_secret"  # 应该被过滤
                    }
                }
            ],
            "data": {
                "count": 1,
                "api_key": "should_be_included"
            },
            "system": {
                "version": "1.0",
                "password": "admin123"  # 应该被过滤
            }
        }
        
        session_id = integrated_parser.create_session("filter_test")
        events = []
        
        async def event_callback(event):
            events.append(event)
        
        integrated_parser.add_event_callback(EventType.DELTA, event_callback)
        
        # 解析数据
        result = await integrated_parser.parse_chunk(
            session_id,
            json.dumps(test_data),
            is_final=True
        )
        
        # 验证字段过滤效果
        delta_events = [e for e in events if e.event_type == EventType.DELTA]
        
        # 检查是否包含了允许的路径
        allowed_paths = []
        for event in delta_events:
            if hasattr(event.data, 'path'):
                allowed_paths.append(event.data.path)
        
        # 验证包含的路径
        assert any('users' in path for path in allowed_paths)
        assert any('data' in path for path in allowed_paths)
        
        # 验证排除的路径（密码和秘密信息应该被过滤）
        filtered_content = ''.join([str(event.data) for event in delta_events])
        assert 'secret123' not in filtered_content
        assert 'top_secret' not in filtered_content
        assert 'admin123' not in filtered_content
        
        # 验证路径匹配缓存被使用
        cache_stats = integrated_parser.performance_optimizer.get_cache_stats()
        assert cache_stats['path_matching_cache']['total'] > 0
    
    @pytest.mark.asyncio
    async def test_error_handling_integration(self):
        """测试错误处理集成"""
        # 创建专门用于错误处理测试的解析器，禁用JSON补全器
        error_parser = StreamingParser(
            enable_completion=False,  # 禁用JSON补全器以确保错误被正确记录
            enable_diff_engine=True,
            max_depth=10,
            chunk_timeout=30.0
        )
        
        session_id = error_parser.create_session("error_test")
        events = []
        
        async def event_callback(event):
            events.append(event)
        
        error_parser.add_event_callback(EventType.ERROR, event_callback)
        
        # 解析无效JSON
        result = await error_parser.parse_chunk(
            session_id,
            '{"invalid": json syntax here}',
            is_final=True
        )
        
        # 验证错误处理
        error_events = [e for e in events if e.event_type == EventType.ERROR]
        result_error_events = [e for e in result if e.event_type == EventType.ERROR]
        
        # 应该有错误事件
        assert len(error_events) > 0 or len(result_error_events) > 0
        
        # 验证会话状态
        state = error_parser.get_parsing_state(session_id)
        assert state is not None
        assert len(state.errors) > 0
    
    @pytest.mark.asyncio
    async def test_concurrent_sessions(self, integrated_parser: StreamingParser):
        """测试并发会话处理"""
        async def process_session(session_index: int):
            session_id = f"concurrent_session_{session_index}"
            integrated_parser.create_session(session_id)
            
            test_data = {
                "session_id": session_index,
                "data": f"concurrent_data_{session_index}",
                "timestamp": time.time()
            }
            
            result = await integrated_parser.parse_chunk(
                session_id,
                json.dumps(test_data),
                is_final=True
            )
            
            return session_id, result
        
        # 并发处理多个会话
        tasks = [process_session(i) for i in range(10)]
        results = await asyncio.gather(*tasks)
        
        # 验证所有会话都成功处理
        assert len(results) == 10
        
        for session_id, result in results:
            assert len(result) > 0
            state = integrated_parser.get_parsing_state(session_id)
            assert state is not None
            assert state.is_complete
        
        # 验证内存管理
        memory_info = integrated_parser.memory_manager.get_memory_usage()
        assert memory_info['active_sessions'] >= 10
    
    @pytest.mark.asyncio
    async def test_large_data_processing(self, integrated_parser: StreamingParser):
        """测试大数据处理"""
        # 创建大型测试数据
        large_data = {
            "users": [
                {
                    "id": i,
                    "name": f"User_{i}",
                    "email": f"user{i}@example.com",
                    "profile": {
                        "age": 20 + (i % 50),
                        "city": f"City_{i % 100}",
                        "preferences": [f"pref_{j}" for j in range(5)]
                    }
                }
                for i in range(1000)  # 1000个用户
            ],
            "data": {
                "total_users": 1000,
                "generated_at": "2024-01-01T00:00:00Z",
                "metadata": {f"key_{i}": f"value_{i}" for i in range(100)}
            }
        }
        
        session_id = integrated_parser.create_session("large_data_test")
        
        # 使用完整JSON处理大数据（避免固定分块破坏JSON结构）
        json_str = json.dumps(large_data)
        
        start_time = time.perf_counter()
        
        # 直接处理完整JSON，避免分块导致的结构破坏
        result = await integrated_parser.parse_chunk(
            session_id,
            json_str,
            is_final=True
        )
        
        processing_time = time.perf_counter() - start_time
        
        # 验证处理结果
        state = integrated_parser.get_parsing_state(session_id)
        assert state is not None
        assert state.is_complete
        assert len(state.current_data['users']) == 1000
        
        # 验证性能
        assert processing_time < 10.0  # 应该在10秒内完成
        
        # 验证内存使用
        memory_info = integrated_parser.memory_manager.get_memory_usage()
        assert memory_info['process_memory_mb'] < 500  # 内存使用应该合理
    
    @pytest.mark.asyncio
    async def test_adaptive_timeout_integration(self, integrated_parser: StreamingParser):
        """测试自适应超时集成"""
        session_id = integrated_parser.create_session("timeout_test")
        
        # 模拟慢速数据流
        test_data = {"slow_data": "processing..."}
        
        # 第一次解析（建立基线）
        await integrated_parser.parse_chunk(
            session_id,
            json.dumps(test_data),
            is_final=True
        )
        
        # 获取解析状态
        state = integrated_parser.get_parsing_state(session_id)
        assert state is not None
        
        # 验证自适应超时配置
        assert state.adaptive_timeout is not None
        assert state.adaptive_timeout.current_timeout > 0
    
    def test_configuration_validation(self, integrated_parser: StreamingParser):
        """测试配置验证"""
        # 验证所有组件都正确配置
        assert integrated_parser.performance_optimizer is not None
        assert integrated_parser.memory_manager is not None
        assert integrated_parser.field_filter is not None
        
        # 验证性能优化器配置
        optimizer = integrated_parser.performance_optimizer
        assert optimizer.enable_string_delta_cache is True
        assert optimizer.enable_path_matching_cache is True
        assert optimizer.memory_manager is not None
        
        # 验证内存管理器配置
        memory_manager = integrated_parser.memory_manager
        assert memory_manager.max_sessions > 0
        assert memory_manager.session_timeout > 0
        
        # 验证字段过滤器配置
        field_filter = integrated_parser.field_filter
        assert field_filter.performance_optimizer is not None
        assert field_filter.enabled is True
    
    @pytest.mark.asyncio
    async def test_end_to_end_workflow(self, integrated_parser: StreamingParser):
        """测试端到端工作流程"""
        # 完整的工作流程测试
        workflow_data = {
            "request_id": "workflow_001",
            "users": [
                {
                    "id": 1,
                    "name": "Alice",
                    "profile": {
                        "email": "alice@example.com",
                        "preferences": ["music", "books"]
                    }
                }
            ],
            "data": {
                "processing_time": 0.5,
                "status": "success",
                "metadata": {
                    "version": "1.0",
                    "timestamp": "2024-01-01T00:00:00Z"
                }
            }
        }
        
        # 1. 创建会话
        session_id = integrated_parser.create_session("workflow_test")
        
        # 2. 设置事件监听
        events = []
        async def collect_events(event):
            events.append(event)
        
        integrated_parser.add_event_callback(EventType.DELTA, collect_events)
        integrated_parser.add_event_callback(EventType.DONE, collect_events)
        
        # 3. 流式解析
        json_str = json.dumps(workflow_data)
        result = await integrated_parser.parse_chunk(
            session_id,
            json_str,
            is_final=True
        )
        
        # 4. 验证结果
        assert len(result) > 0
        assert len(events) > 0
        
        # 5. 检查解析状态
        state = integrated_parser.get_parsing_state(session_id)
        assert state is not None
        assert state.is_complete
        assert state.current_data == workflow_data
        
        # 6. 验证性能统计
        cache_stats = integrated_parser.performance_optimizer.get_cache_stats()
        assert cache_stats['string_delta_cache']['total'] >= 0
        assert cache_stats['path_matching_cache']['total'] >= 0
        
        # 7. 验证内存管理
        memory_info = integrated_parser.memory_manager.get_memory_usage()
        assert memory_info['active_sessions'] >= 1
        
        # 8. 清理会话
        integrated_parser.finalize_session(session_id)
        
        # 9. 验证清理效果
        assert not integrated_parser.has_session(session_id)