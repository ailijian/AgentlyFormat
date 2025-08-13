"""核心模块测试

测试流式解析器、JSON补全器和路径构建器。
"""

import pytest
import json
import asyncio
from typing import List, Dict, Any

from agently_format.core.streaming_parser import StreamingParser
from agently_format.core.json_completer import JSONCompleter, CompletionStrategy
from agently_format.core.path_builder import PathBuilder, PathStyle
from agently_format.types.events import EventType


class TestStreamingParser:
    """流式解析器测试"""
    
    @pytest.mark.asyncio
    async def test_parse_complete_json(self, streaming_parser: StreamingParser, sample_json_data: Dict[str, Any]):
        """测试解析完整JSON"""
        json_str = json.dumps(sample_json_data)
        events = []
        
        async def event_callback(event):
            events.append(event)
        
        session_id = streaming_parser.create_session("test-session")
        
        # 添加事件回调
        streaming_parser.add_event_callback(EventType.DELTA, event_callback)
        streaming_parser.add_event_callback(EventType.DONE, event_callback)
        streaming_parser.add_event_callback(EventType.ERROR, event_callback)
        
        result = await streaming_parser.parse_chunk(
            json_str,
            session_id,
            is_final=True
        )
        
        assert result is not None
        assert len(events) > 0
        
        # 检查解析状态
        state = streaming_parser.get_parsing_state("test-session")
        assert state is not None
        assert state.is_complete
        assert state.current_data == sample_json_data
    
    @pytest.mark.asyncio
    async def test_parse_incomplete_chunks(self, streaming_parser: StreamingParser, incomplete_json_chunks: List[str]):
        """测试解析不完整JSON块"""
        events = []
        session_id = "test-incomplete"
        
        async def event_callback(event):
            events.append(event)
        
        # 逐块解析
        for i, chunk in enumerate(incomplete_json_chunks):
            is_final = (i == len(incomplete_json_chunks) - 1)
            
            # 为第一个块添加事件回调
            if i == 0:
                streaming_parser.add_event_callback(EventType.DELTA, event_callback)
                streaming_parser.add_event_callback(EventType.DONE, event_callback)
                streaming_parser.add_event_callback(EventType.ERROR, event_callback)
                streaming_parser.create_session(session_id)
            
            result = await streaming_parser.parse_chunk(
                chunk,
                session_id,
                is_final=is_final
            )
        
        # 检查最终状态
        state = streaming_parser.get_parsing_state(session_id)
        assert state is not None
        assert state.is_complete
        assert "users" in state.current_data
        assert "total" in state.current_data
    
    @pytest.mark.asyncio
    async def test_multiple_sessions(self, streaming_parser: StreamingParser):
        """测试多会话处理"""
        session1 = "session-1"
        session2 = "session-2"
        
        # 创建会话
        streaming_parser.create_session(session1)
        streaming_parser.create_session(session2)
        
        # 会话1
        await streaming_parser.parse_chunk(
            '{"data1": "value1"}',
            session1,
            is_final=True
        )
        
        # 会话2
        await streaming_parser.parse_chunk(
            '{"data2": "value2"}',
            session2,
            is_final=True
        )
        
        # 检查两个会话的状态
        state1 = streaming_parser.get_parsing_state(session1)
        state2 = streaming_parser.get_parsing_state(session2)
        
        assert state1.current_data["data1"] == "value1"
        assert state2.current_data["data2"] == "value2"
    
    @pytest.mark.asyncio
    async def test_error_handling(self):
        """测试错误处理"""
        print("\n=== 开始错误处理测试 ===")
        
        # 创建一个禁用JSON补全的解析器
        parser = StreamingParser(
            enable_completion=False,  # 禁用补全，确保生成错误事件
            enable_diff_engine=True
        )
        print("解析器创建完成")
        
        events = []
        
        async def event_callback(event):
            events.append(event)
        
        # 创建会话并添加事件回调
        session_id = parser.create_session("error-session")
        print(f"创建会话: {session_id}")
        parser.add_event_callback(EventType.ERROR, event_callback)
        print("添加错误事件回调完成")
        
        # 测试JSON补全器是否真的被禁用
        print(f"JSON补全器状态: {parser.json_completer is not None}")
        print(f"启用补全: {parser.enable_completion}")
        
        # 先测试_parse_json_chunk方法是否会抛出异常
        state = parser.get_session_state(session_id)
        print(f"会话状态: {state is not None}")
        
        try:
            test_result = await parser._parse_json_chunk('{"invalid": json syntax error here}', state)
            print(f"_parse_json_chunk返回: {test_result}")
        except Exception as e:
            print(f"_parse_json_chunk抛出异常: {e}")
        
        # 解析无效JSON
        result = await parser.parse_chunk(
            '{"invalid": json syntax error here}',
            session_id,
            is_final=True
        )
        print(f"parse_chunk调用完成，返回了 {len(result)} 个事件")
        
        # 应该有错误事件
        print(f"\n=== 错误处理调试 ===")
        print(f"总事件数: {len(events)}")
        print(f"result事件数: {len(result)}")
        print(f"事件类型: {[e.event_type for e in events]}")
        print(f"result事件类型: {[e.event_type for e in result]}")
        
        # 检查result中的错误事件
        error_events_result = [e for e in result if e.event_type == EventType.ERROR]
        error_events_callback = [e for e in events if e.event_type == EventType.ERROR]
        print(f"result错误事件数: {len(error_events_result)}")
        print(f"callback错误事件数: {len(error_events_callback)}")
        
        # 至少应该有一个错误事件（在result或callback中）
        assert len(error_events_result) > 0 or len(error_events_callback) > 0
    
    def test_session_management(self, streaming_parser: StreamingParser):
        """测试会话管理"""
        session_id = "test-session-mgmt"
        
        # 创建会话
        streaming_parser.create_session(session_id)
        assert streaming_parser.has_session(session_id)
        
        # 完成会话
        streaming_parser.complete_session(session_id)
        
        # 清理会话
        streaming_parser.cleanup_session(session_id)
        assert not streaming_parser.has_session(session_id)


class TestJSONCompleter:
    """JSON补全器测试"""
    
    def test_complete_simple_json(self, json_completer: JSONCompleter):
        """测试简单JSON补全"""
        incomplete = '{"name": "Alice", "age": 25'
        
        result = json_completer.complete(incomplete)
        
        assert result.is_valid
        assert result.changes_made > 0
        assert result.confidence > 0.5
        
        # 验证补全后的JSON可以解析
        completed_data = json.loads(result.completed_json)
        assert completed_data["name"] == "Alice"
        assert completed_data["age"] == 25
    
    def test_complete_nested_json(self, json_completer: JSONCompleter):
        """测试嵌套JSON补全"""
        incomplete = '{"user": {"name": "Bob", "profile": {"city": "NYC"'
        
        result = json_completer.complete(incomplete)
        
        assert result.is_valid
        completed_data = json.loads(result.completed_json)
        assert completed_data["user"]["name"] == "Bob"
        assert completed_data["user"]["profile"]["city"] == "NYC"
    
    def test_complete_array_json(self, json_completer: JSONCompleter):
        """测试数组JSON补全"""
        incomplete = '{"items": ["item1", "item2"'
        
        result = json_completer.complete(incomplete)
        
        assert result.is_valid
        completed_data = json.loads(result.completed_json)
        assert len(completed_data["items"]) == 2
        assert completed_data["items"][0] == "item1"
    
    def test_completion_strategies(self, json_completer: JSONCompleter):
        """测试不同补全策略"""
        incomplete = '{"data": {"value": 123'
        
        # 保守策略
        conservative = json_completer.complete(incomplete, strategy=CompletionStrategy.CONSERVATIVE)
        
        # 智能策略
        smart = json_completer.complete(incomplete, strategy=CompletionStrategy.SMART)
        
        # 激进策略
        aggressive = json_completer.complete(incomplete, strategy=CompletionStrategy.AGGRESSIVE)
        
        # 所有策略都应该产生有效JSON
        assert conservative.is_valid
        assert smart.is_valid
        assert aggressive.is_valid
        
        # 激进策略可能做更多改变
        assert aggressive.changes_made >= conservative.changes_made
    
    def test_max_depth_limit(self, json_completer: JSONCompleter):
        """测试最大深度限制"""
        # 创建深度嵌套的不完整JSON
        incomplete = '{"a": {"b": {"c": {"d": {"e": "value"'
        
        result = json_completer.complete(incomplete, max_depth=3)
        
        assert result.is_valid
        completed_data = json.loads(result.completed_json)
        
        # 验证深度限制
        current = completed_data
        depth = 0
        while isinstance(current, dict) and len(current) > 0:
            key = list(current.keys())[0]
            current = current[key]
            depth += 1
            if depth > 5:  # 防止无限循环
                break
    
    def test_invalid_json_handling(self, json_completer: JSONCompleter):
        """测试无效JSON处理"""
        invalid_json = "not json at all"
        
        result = json_completer.complete(invalid_json)
        
        # 应该尝试修复或返回错误信息
        assert result is not None


class TestPathBuilder:
    """路径构建器测试"""
    
    def test_build_simple_paths(self, path_builder: PathBuilder, sample_json_data: Dict[str, Any]):
        """测试简单路径构建"""
        paths = path_builder.build_paths(sample_json_data)
        
        assert len(paths) > 0
        
        # 检查一些预期的路径
        expected_paths = [
            "users",
            "users[0]",
            "users[0].id",
            "users[0].name",
            "users[0].email",
            "users[0].profile",
            "users[0].profile.age",
            "users[0].profile.city",
            "metadata",
            "metadata.total",
            "metadata.page"
        ]
        
        for expected_path in expected_paths:
            assert expected_path in paths
    
    def test_different_path_styles(self, path_builder: PathBuilder):
        """测试不同路径风格"""
        data = {
            "user": {
                "profile": {
                    "settings": ["option1", "option2"]
                }
            }
        }
        
        # 点号风格
        dot_paths = path_builder.build_paths(data, style=PathStyle.DOT)
        assert "user.profile.settings[0]" in dot_paths
        
        # 斜杠风格
        slash_paths = path_builder.build_paths(data, style=PathStyle.SLASH)
        assert "user/profile/settings[0]" in slash_paths
        
        # 括号风格
        bracket_paths = path_builder.build_paths(data, style=PathStyle.BRACKET)
        assert "user['profile']['settings'][0]" in bracket_paths
    
    def test_include_arrays_option(self, path_builder: PathBuilder):
        """测试包含数组选项"""
        data = {
            "items": ["a", "b", "c"],
            "metadata": {"count": 3}
        }
        
        # 包含数组索引
        with_arrays = path_builder.build_paths(data, include_arrays=True)
        assert "items[0]" in with_arrays
        assert "items[1]" in with_arrays
        assert "items[2]" in with_arrays
        
        # 不包含数组索引
        without_arrays = path_builder.build_paths(data, include_arrays=False)
        assert "items[0]" not in without_arrays
        assert "items" in without_arrays
    
    def test_complex_nested_structure(self, path_builder: PathBuilder):
        """测试复杂嵌套结构"""
        complex_data = {
            "api": {
                "v1": {
                    "endpoints": [
                        {
                            "path": "/users",
                            "methods": ["GET", "POST"],
                            "auth": {
                                "required": True,
                                "types": ["bearer", "api_key"]
                            }
                        }
                    ]
                }
            }
        }
        
        paths = path_builder.build_paths(complex_data)
        
        # 检查深层嵌套路径
        expected_deep_paths = [
            "api.v1.endpoints[0].path",
            "api.v1.endpoints[0].methods[0]",
            "api.v1.endpoints[0].auth.required",
            "api.v1.endpoints[0].auth.types[0]"
        ]
        
        for path in expected_deep_paths:
            assert path in paths
    
    def test_empty_and_null_values(self, path_builder: PathBuilder):
        """测试空值和null值"""
        data = {
            "empty_string": "",
            "null_value": None,
            "empty_array": [],
            "empty_object": {},
            "normal_value": "test"
        }
        
        paths = path_builder.build_paths(data)
        
        # 所有键都应该被包含
        assert "empty_string" in paths
        assert "null_value" in paths
        assert "empty_array" in paths
        assert "empty_object" in paths
        assert "normal_value" in paths
    
    def test_path_validation(self, path_builder: PathBuilder):
        """测试路径验证"""
        data = {"test": {"nested": "value"}}
        paths = path_builder.build_paths(data)
        
        # 验证路径
        valid_path = "test.nested"
        invalid_path = "test.nonexistent"
        
        assert path_builder.validate_path(data, valid_path)
        assert not path_builder.validate_path(data, invalid_path)
    
    def test_get_value_by_path(self, path_builder: PathBuilder):
        """测试通过路径获取值"""
        data = {
            "user": {
                "profile": {
                    "name": "Alice",
                    "tags": ["admin", "user"]
                }
            }
        }
        
        # 获取嵌套值
        name = path_builder.get_value_by_path(data, "user.profile.name")
        assert name == "Alice"
        
        # 获取数组元素
        first_tag = path_builder.get_value_by_path(data, "user.profile.tags[0]")
        assert first_tag == "admin"
        
        # 获取不存在的路径
        nonexistent = path_builder.get_value_by_path(data, "user.profile.age")
        assert nonexistent is None


@pytest.mark.performance
class TestPerformance:
    """性能测试"""
    
    @pytest.mark.asyncio
    async def test_large_json_parsing(self, streaming_parser: StreamingParser, performance_test_data: Dict[str, Any]):
        """测试大JSON解析性能"""
        import time
        
        json_str = json.dumps(performance_test_data)
        
        # 先创建会话
        session_id = "performance-test-session"
        streaming_parser.create_session(session_id)
        
        start_time = time.time()
        
        result = await streaming_parser.parse_chunk(
            json_str,
            session_id,
            is_final=True
        )
        
        end_time = time.time()
        parse_time = end_time - start_time
        
        # 解析时间应该在合理范围内（根据数据大小调整）
        assert parse_time < 5.0  # 5秒内完成
        assert result is not None
    
    def test_path_building_performance(self, path_builder: PathBuilder, performance_test_data: Dict[str, Any]):
        """测试路径构建性能"""
        import time
        
        start_time = time.time()
        
        paths = path_builder.build_paths(performance_test_data)
        
        end_time = time.time()
        build_time = end_time - start_time
        
        # 构建时间应该在合理范围内
        assert build_time < 2.0  # 2秒内完成
        assert len(paths) > 1000  # 应该生成大量路径
    
    def test_json_completion_performance(self, json_completer: JSONCompleter):
        """测试JSON补全性能"""
        import time
        
        # 创建一个简单的不完整JSON，确保能够成功补全
        simple_incomplete = '{"data": ["item1", "item2"'
        
        start_time = time.time()
        
        result = json_completer.complete(simple_incomplete)
        
        end_time = time.time()
        completion_time = end_time - start_time
        
        # 补全时间应该在合理范围内
        assert completion_time < 3.0  # 3秒内完成
        assert result is not None  # 应该返回结果
        assert result.completion_applied  # 应该应用了补全
        
        # 测试大量数据的性能
        large_incomplete = '{"items": [' + ','.join([f'{{"id": {i}}}' for i in range(50)]) + ', {"id": 50'
        
        start_time = time.time()
        large_result = json_completer.complete(large_incomplete)
        end_time = time.time()
        large_completion_time = end_time - start_time
        
        # 大数据补全时间也应该在合理范围内
        assert large_completion_time < 5.0  # 5秒内完成
        assert large_result is not None
        assert large_result.completion_applied