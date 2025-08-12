"""流式JSON解析器模块

基于Agently框架的StreamingJSONParser优化实现，
用于异步逐块解析流式JSON数据，支持增量更新和事件通知。
"""

import json
import json5
import asyncio
from typing import Any, Dict, List, Optional, Callable, AsyncGenerator, Union
from datetime import datetime
from dataclasses import dataclass, field
import uuid
import copy

from ..types.events import (
    StreamingEvent, EventType, EventData,
    create_delta_event, create_done_event, create_error_event
)
from .path_builder import PathBuilder, PathStyle
from .json_completer import JSONCompleter, CompletionStrategy


@dataclass
class ParsingState:
    """解析状态"""
    session_id: str
    current_data: Dict[str, Any] = field(default_factory=dict)
    previous_data: Dict[str, Any] = field(default_factory=dict)
    completed_fields: set = field(default_factory=set)
    parsing_paths: List[str] = field(default_factory=list)
    sequence_number: int = 0
    total_chunks: int = 0
    processed_chunks: int = 0
    start_time: datetime = field(default_factory=datetime.now)
    last_update_time: datetime = field(default_factory=datetime.now)
    errors: List[str] = field(default_factory=list)
    
    def increment_sequence(self) -> int:
        """递增序列号"""
        self.sequence_number += 1
        return self.sequence_number
    
    def update_timestamp(self):
        """更新时间戳"""
        self.last_update_time = datetime.now()


class StreamingParser:
    """流式JSON解析器
    
    异步逐块解析流式JSON数据，维护解析状态，
    并为每个字段在结构构建过程中发出增量和完成事件。
    """
    
    def __init__(
        self,
        enable_completion: bool = True,
        completion_strategy: CompletionStrategy = CompletionStrategy.SMART,
        path_style: PathStyle = PathStyle.DOT,
        max_depth: int = 10,
        chunk_timeout: float = 5.0
    ):
        """初始化流式解析器
        
        Args:
            enable_completion: 是否启用JSON补全
            completion_strategy: JSON补全策略
            path_style: 路径风格
            max_depth: 最大解析深度
            chunk_timeout: 块处理超时时间
        """
        self.enable_completion = enable_completion
        self.completion_strategy = completion_strategy
        self.path_style = path_style
        self.max_depth = max_depth
        self.chunk_timeout = chunk_timeout
        
        # 组件初始化
        self.path_builder = PathBuilder(path_style)
        self.json_completer = JSONCompleter(completion_strategy) if enable_completion else None
        
        # 解析状态
        self.parsing_states: Dict[str, ParsingState] = {}
        
        # 事件回调
        self.event_callbacks: Dict[EventType, List[Callable]] = {
            EventType.DELTA: [],
            EventType.DONE: [],
            EventType.ERROR: [],
            EventType.START: [],
            EventType.FINISH: [],
            EventType.PROGRESS: []
        }
        
        # 统计信息
        self.stats = {
            "total_sessions": 0,
            "active_sessions": 0,
            "completed_sessions": 0,
            "failed_sessions": 0,
            "total_events_emitted": 0
        }
    
    def create_session(self, session_id: Optional[str] = None) -> str:
        """创建新的解析会话
        
        Args:
            session_id: 可选的会话ID，如果不提供则自动生成
        
        Returns:
            str: 会话ID
        """
        if session_id is None:
            session_id = str(uuid.uuid4())
        
        self.parsing_states[session_id] = ParsingState(session_id=session_id)
        self.stats["total_sessions"] += 1
        self.stats["active_sessions"] += 1
        return session_id
    
    def add_event_callback(self, event_type: EventType, callback: Callable):
        """添加事件回调
        
        Args:
            event_type: 事件类型
            callback: 回调函数
        """
        if event_type in self.event_callbacks:
            self.event_callbacks[event_type].append(callback)
    
    def remove_event_callback(self, event_type: EventType, callback: Callable):
        """移除事件回调
        
        Args:
            event_type: 事件类型
            callback: 回调函数
        """
        if event_type in self.event_callbacks and callback in self.event_callbacks[event_type]:
            self.event_callbacks[event_type].remove(callback)
    
    async def _emit_event(self, event: StreamingEvent):
        """发出事件
        
        Args:
            event: 流式事件
        """
        self.stats["total_events_emitted"] += 1
        
        # 调用注册的回调函数
        callbacks = self.event_callbacks.get(event.event_type, [])
        for callback in callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(event)
                else:
                    callback(event)
            except Exception as e:
                # 记录回调错误，但不中断处理
                print(f"Event callback error: {e}")
    
    async def parse_chunk(self, chunk: str, session_id: str, is_final: bool = False) -> List[StreamingEvent]:
        """解析JSON块
        
        Args:
            session_id: 会话ID
            chunk: JSON块
            
        Returns:
            List[StreamingEvent]: 生成的事件列表
        """
        if session_id not in self.parsing_states:
            raise ValueError(f"Session {session_id} not found")
        
        state = self.parsing_states[session_id]
        state.total_chunks += 1
        state.update_timestamp()
        
        events = []
        
        try:
            # 尝试解析当前块
            parsed_data = await self._parse_json_chunk(chunk, state)
            
            if parsed_data is not None:
                # 比较并生成事件
                chunk_events = await self._compare_and_generate_events(state, parsed_data)
                events.extend(chunk_events)
                
                # 更新状态
                state.previous_data = copy.deepcopy(state.current_data)
                state.current_data = parsed_data
                state.processed_chunks += 1
            
        except Exception as e:
            # 生成错误事件
            error_event = create_error_event(
                path="",
                error_type="parsing_error",
                error_message=str(e),
                session_id=session_id,
                sequence_number=state.increment_sequence()
            )
            events.append(error_event)
            state.errors.append(str(e))
        
        # 发出所有事件
        for event in events:
            await self._emit_event(event)
        
        return events
    
    async def _parse_json_chunk(self, chunk: str, state: ParsingState) -> Optional[Dict[str, Any]]:
        """解析JSON块
        
        Args:
            chunk: JSON块
            state: 解析状态
            
        Returns:
            Optional[Dict[str, Any]]: 解析结果
        """
        if not chunk.strip():
            return None
        
        try:
            # 首先尝试直接解析
            return json.loads(chunk)
        except json.JSONDecodeError:
            pass
        
        try:
            # 尝试使用json5解析（支持更宽松的语法）
            return json5.loads(chunk)
        except Exception:
            pass
        
        # 如果启用了补全，尝试补全后解析
        if self.json_completer:
            try:
                completion_result = self.json_completer.complete(chunk)
                if completion_result.is_valid:
                    return json.loads(completion_result.completed_json)
            except Exception:
                pass
        
        # 如果都失败了，返回None
        return None
    
    async def _compare_and_generate_events(
        self, 
        state: ParsingState, 
        new_data: Dict[str, Any]
    ) -> List[StreamingEvent]:
        """比较数据并生成事件
        
        Args:
            state: 解析状态
            new_data: 新数据
            
        Returns:
            List[StreamingEvent]: 事件列表
        """
        events = []
        
        # 获取所有路径
        new_paths = set(self.path_builder.extract_parsing_key_orders(new_data))
        old_paths = set(self.path_builder.extract_parsing_key_orders(state.current_data))
        
        # 处理新增和更新的路径
        for path in new_paths:
            success, new_value = self.path_builder.get_value_at_path(new_data, path)
            if not success:
                continue
            
            old_success, old_value = self.path_builder.get_value_at_path(state.current_data, path)
            
            if not old_success:
                # 新字段
                delta_event = create_delta_event(
                    path=path,
                    value=new_value,
                    delta_value=new_value,
                    session_id=state.session_id,
                    sequence_number=state.increment_sequence(),
                    previous_value=None,
                    is_partial=self._is_value_partial(new_value)
                )
                events.append(delta_event)
            elif old_value != new_value:
                # 字段更新
                delta_event = create_delta_event(
                    path=path,
                    value=new_value,
                    delta_value=self._calculate_delta(old_value, new_value),
                    session_id=state.session_id,
                    sequence_number=state.increment_sequence(),
                    previous_value=old_value,
                    is_partial=self._is_value_partial(new_value)
                )
                events.append(delta_event)
            
            # 检查字段是否完成
            if self._should_mark_field_complete(path, new_value, state):
                if path not in state.completed_fields:
                    done_event = create_done_event(
                        path=path,
                        final_value=new_value,
                        session_id=state.session_id,
                        sequence_number=state.increment_sequence(),
                        validation_passed=True
                    )
                    events.append(done_event)
                    state.completed_fields.add(path)
        
        return events
    
    def _is_value_partial(self, value: Any) -> bool:
        """判断值是否为部分值
        
        Args:
            value: 值
            
        Returns:
            bool: 是否为部分值
        """
        if isinstance(value, str):
            # 字符串可能不完整
            return len(value) < 1000  # 简单启发式
        elif isinstance(value, (dict, list)):
            # 复杂对象可能不完整
            return True
        else:
            # 基本类型通常是完整的
            return False
    
    def _calculate_delta(self, old_value: Any, new_value: Any) -> Any:
        """计算增量值
        
        Args:
            old_value: 旧值
            new_value: 新值
            
        Returns:
            Any: 增量值
        """
        if isinstance(old_value, str) and isinstance(new_value, str):
            # 字符串增量
            if new_value.startswith(old_value):
                return new_value[len(old_value):]
            else:
                return new_value
        elif isinstance(old_value, list) and isinstance(new_value, list):
            # 数组增量
            if len(new_value) > len(old_value):
                return new_value[len(old_value):]
            else:
                return new_value
        elif isinstance(old_value, dict) and isinstance(new_value, dict):
            # 对象增量
            delta = {}
            for key, value in new_value.items():
                if key not in old_value or old_value[key] != value:
                    delta[key] = value
            return delta
        else:
            # 其他情况返回新值
            return new_value
    
    def _should_mark_field_complete(self, path: str, value: Any, state: ParsingState) -> bool:
        """判断字段是否应该标记为完成
        
        Args:
            path: 字段路径
            value: 字段值
            state: 解析状态
            
        Returns:
            bool: 是否应该标记为完成
        """
        # 简单启发式：基本类型通常是完成的
        if isinstance(value, (int, float, bool, type(None))):
            return True
        
        # 字符串：检查是否看起来完整
        if isinstance(value, str):
            # 如果字符串很短或以标点符号结尾，可能是完整的
            return len(value) < 100 or value.endswith(('.', '!', '?', '"', "'"))
        
        # 复杂对象：需要更复杂的逻辑
        return False
    
    async def finalize_session(self, session_id: str) -> List[StreamingEvent]:
        """完成解析会话
        
        Args:
            session_id: 会话ID
            
        Returns:
            List[StreamingEvent]: 最终事件列表
        """
        if session_id not in self.parsing_states:
            raise ValueError(f"Session {session_id} not found")
        
        state = self.parsing_states[session_id]
        events = []
        
        # 标记所有剩余字段为完成
        all_paths = set(self.path_builder.extract_parsing_key_orders(state.current_data))
        remaining_paths = all_paths - state.completed_fields
        
        for path in remaining_paths:
            success, value = self.path_builder.get_value_at_path(state.current_data, path)
            if success:
                done_event = create_done_event(
                    path=path,
                    final_value=value,
                    session_id=session_id,
                    sequence_number=state.increment_sequence(),
                    validation_passed=True
                )
                events.append(done_event)
                state.completed_fields.add(path)
        
        # 发出所有事件
        for event in events:
            await self._emit_event(event)
        
        # 更新统计
        self.stats["active_sessions"] -= 1
        if state.errors:
            self.stats["failed_sessions"] += 1
        else:
            self.stats["completed_sessions"] += 1
        
        return events
    
    async def parse_stream(
        self,
        stream: AsyncGenerator[str, None],
        session_id: Optional[str] = None
    ) -> AsyncGenerator[StreamingEvent, None]:
        """解析流式数据
        
        Args:
            stream: 异步数据流
            session_id: 会话ID，如果为None则自动创建
            
        Yields:
            StreamingEvent: 流式事件
        """
        if session_id is None:
            session_id = self.create_session()
        
        try:
            async for chunk in stream:
                events = await self.parse_chunk(session_id, chunk)
                for event in events:
                    yield event
                
                # 添加超时检查
                await asyncio.sleep(0)  # 让出控制权
        
        except Exception as e:
            # 生成错误事件
            error_event = create_error_event(
                path="",
                error_type="stream_error",
                error_message=str(e),
                session_id=session_id,
                sequence_number=self.parsing_states[session_id].increment_sequence()
            )
            await self._emit_event(error_event)
            yield error_event
        
        finally:
            # 完成会话
            final_events = await self.finalize_session(session_id)
            for event in final_events:
                yield event
    
    def get_session_state(self, session_id: str) -> Optional[ParsingState]:
        """获取会话状态
        
        Args:
            session_id: 会话ID
            
        Returns:
            Optional[ParsingState]: 会话状态
        """
        return self.parsing_states.get(session_id)
    
    def get_parsing_state(self, session_id: str) -> Optional[ParsingState]:
        """获取解析状态（别名方法）
        
        Args:
            session_id: 会话ID
            
        Returns:
            Optional[ParsingState]: 解析状态
        """
        state = self.parsing_states.get(session_id)
        if state:
            # 添加is_complete属性
            state.is_complete = len(state.errors) == 0 and state.processed_chunks > 0
        return state
    
    def has_session(self, session_id: str) -> bool:
        """检查会话是否存在
        
        Args:
            session_id: 会话ID
            
        Returns:
            bool: 会话是否存在
        """
        return session_id in self.parsing_states
    
    def complete_session(self, session_id: str):
        """完成会话（同步版本）
        
        Args:
            session_id: 会话ID
        """
        if session_id in self.parsing_states:
            state = self.parsing_states[session_id]
            state.is_complete = True
            if self.stats["active_sessions"] > 0:
                self.stats["active_sessions"] -= 1
            self.stats["completed_sessions"] += 1
    
    def get_current_data(self, session_id: str) -> Optional[Dict[str, Any]]:
        """获取当前解析数据
        
        Args:
            session_id: 会话ID
            
        Returns:
            Optional[Dict[str, Any]]: 当前数据
        """
        state = self.parsing_states.get(session_id)
        return state.current_data if state else None
    
    def cleanup_session(self, session_id: str):
        """清理会话
        
        Args:
            session_id: 会话ID
        """
        if session_id in self.parsing_states:
            del self.parsing_states[session_id]
            if self.stats["active_sessions"] > 0:
                self.stats["active_sessions"] -= 1
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息
        
        Returns:
            Dict[str, Any]: 统计信息
        """
        return {
            **self.stats,
            "completion_stats": self.json_completer.get_completion_stats() if self.json_completer else None
        }
    
    def reset_stats(self):
        """重置统计信息"""
        self.stats = {
            "total_sessions": 0,
            "active_sessions": 0,
            "completed_sessions": 0,
            "failed_sessions": 0,
            "total_events_emitted": 0
        }
        if self.json_completer:
            self.json_completer.reset_stats()


# 便捷函数
async def parse_json_stream(
    stream: AsyncGenerator[str, None],
    enable_completion: bool = True,
    completion_strategy: CompletionStrategy = CompletionStrategy.SMART
) -> AsyncGenerator[StreamingEvent, None]:
    """解析JSON流的便捷函数
    
    Args:
        stream: 异步数据流
        enable_completion: 是否启用补全
        completion_strategy: 补全策略
        
    Yields:
        StreamingEvent: 流式事件
    """
    parser = StreamingParser(
        enable_completion=enable_completion,
        completion_strategy=completion_strategy
    )
    
    async for event in parser.parse_stream(stream):
        yield event