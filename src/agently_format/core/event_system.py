"""异步事件系统

提供事件发布订阅机制，支持异步事件处理和生命周期管理。
"""

import asyncio
from typing import Any, Dict, List, Optional, Callable, Union, Set
from dataclasses import dataclass, field
from enum import Enum
import weakref
import logging
from datetime import datetime
import uuid

from ..types.events import StreamingEvent, EventType


class EventPriority(Enum):
    """事件优先级"""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4


@dataclass
class EventHandler:
    """事件处理器"""
    handler_id: str
    callback: Callable
    event_types: Set[EventType]
    priority: EventPriority = EventPriority.NORMAL
    once: bool = False
    active: bool = True
    created_at: datetime = field(default_factory=datetime.now)
    call_count: int = 0
    last_called: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class EventStats:
    """事件统计信息"""
    total_events: int = 0
    events_by_type: Dict[EventType, int] = field(default_factory=dict)
    total_handlers: int = 0
    active_handlers: int = 0
    failed_events: int = 0
    processing_time_ms: float = 0.0
    last_event_time: Optional[datetime] = None


class EventEmitter:
    """事件发射器"""
    
    def __init__(self, max_listeners: int = 100):
        """初始化事件发射器
        
        Args:
            max_listeners: 最大监听器数量
        """
        self._handlers: Dict[EventType, List[EventHandler]] = {}
        self._global_handlers: List[EventHandler] = []
        self._max_listeners = max_listeners
        self._stats = EventStats()
        self._logger = logging.getLogger(__name__)
        self._event_queue: asyncio.Queue = asyncio.Queue()
        self._processing_task: Optional[asyncio.Task] = None
        self._shutdown = False
        
        # 弱引用集合，用于自动清理
        self._weak_refs: Set[weakref.ref] = set()
    
    def on(
        self,
        event_types: Union[EventType, List[EventType]],
        callback: Callable,
        priority: EventPriority = EventPriority.NORMAL,
        once: bool = False,
        **metadata
    ) -> str:
        """注册事件监听器
        
        Args:
            event_types: 事件类型或类型列表
            callback: 回调函数
            priority: 优先级
            once: 是否只执行一次
            **metadata: 元数据
            
        Returns:
            str: 处理器ID
        """
        if isinstance(event_types, EventType):
            event_types = [event_types]
        
        handler_id = str(uuid.uuid4())
        handler = EventHandler(
            handler_id=handler_id,
            callback=callback,
            event_types=set(event_types),
            priority=priority,
            once=once,
            metadata=metadata
        )
        
        # 注册到对应的事件类型
        for event_type in event_types:
            if event_type not in self._handlers:
                self._handlers[event_type] = []
            
            self._handlers[event_type].append(handler)
            
            # 按优先级排序
            self._handlers[event_type].sort(
                key=lambda h: h.priority.value,
                reverse=True
            )
        
        self._stats.total_handlers += 1
        self._stats.active_handlers += 1
        
        # 检查监听器数量限制
        if self._stats.active_handlers > self._max_listeners:
            self._logger.warning(
                f"Event listeners count ({self._stats.active_handlers}) "
                f"exceeds maximum ({self._max_listeners})"
            )
        
        return handler_id
    
    def once(
        self,
        event_types: Union[EventType, List[EventType]],
        callback: Callable,
        priority: EventPriority = EventPriority.NORMAL,
        **metadata
    ) -> str:
        """注册一次性事件监听器
        
        Args:
            event_types: 事件类型或类型列表
            callback: 回调函数
            priority: 优先级
            **metadata: 元数据
            
        Returns:
            str: 处理器ID
        """
        return self.on(event_types, callback, priority, once=True, **metadata)
    
    def on_any(
        self,
        callback: Callable,
        priority: EventPriority = EventPriority.NORMAL,
        once: bool = False,
        **metadata
    ) -> str:
        """注册全局事件监听器（监听所有事件）
        
        Args:
            callback: 回调函数
            priority: 优先级
            once: 是否只执行一次
            **metadata: 元数据
            
        Returns:
            str: 处理器ID
        """
        handler_id = str(uuid.uuid4())
        handler = EventHandler(
            handler_id=handler_id,
            callback=callback,
            event_types=set(),  # 空集合表示监听所有事件
            priority=priority,
            once=once,
            metadata=metadata
        )
        
        self._global_handlers.append(handler)
        
        # 按优先级排序
        self._global_handlers.sort(
            key=lambda h: h.priority.value,
            reverse=True
        )
        
        self._stats.total_handlers += 1
        self._stats.active_handlers += 1
        
        return handler_id
    
    def off(self, handler_id: str) -> bool:
        """移除事件监听器
        
        Args:
            handler_id: 处理器ID
            
        Returns:
            bool: 是否成功移除
        """
        # 从特定事件类型的处理器中移除
        for event_type, handlers in self._handlers.items():
            for i, handler in enumerate(handlers):
                if handler.handler_id == handler_id:
                    handlers.pop(i)
                    if handler.active:
                        self._stats.active_handlers -= 1
                    return True
        
        # 从全局处理器中移除
        for i, handler in enumerate(self._global_handlers):
            if handler.handler_id == handler_id:
                self._global_handlers.pop(i)
                if handler.active:
                    self._stats.active_handlers -= 1
                return True
        
        return False
    
    def off_all(self, event_type: Optional[EventType] = None):
        """移除所有监听器
        
        Args:
            event_type: 事件类型，如果为None则移除所有
        """
        if event_type is None:
            # 移除所有监听器
            for handlers in self._handlers.values():
                for handler in handlers:
                    if handler.active:
                        self._stats.active_handlers -= 1
            
            for handler in self._global_handlers:
                if handler.active:
                    self._stats.active_handlers -= 1
            
            self._handlers.clear()
            self._global_handlers.clear()
        else:
            # 移除特定事件类型的监听器
            if event_type in self._handlers:
                for handler in self._handlers[event_type]:
                    if handler.active:
                        self._stats.active_handlers -= 1
                del self._handlers[event_type]
    
    async def emit(
        self,
        event: StreamingEvent,
        sync: bool = False
    ) -> List[Any]:
        """发射事件
        
        Args:
            event: 事件对象
            sync: 是否同步执行
            
        Returns:
            List[Any]: 处理器返回值列表
        """
        if sync:
            return await self._process_event_sync(event)
        else:
            await self._event_queue.put(event)
            
            # 启动处理任务（如果还没有启动）
            if self._processing_task is None or self._processing_task.done():
                self._processing_task = asyncio.create_task(self._process_events())
            
            return []
    
    async def emit_and_wait(
        self,
        event: StreamingEvent,
        timeout: Optional[float] = None
    ) -> List[Any]:
        """发射事件并等待处理完成
        
        Args:
            event: 事件对象
            timeout: 超时时间（秒）
            
        Returns:
            List[Any]: 处理器返回值列表
        """
        return await asyncio.wait_for(
            self._process_event_sync(event),
            timeout=timeout
        )
    
    async def _process_events(self):
        """异步处理事件队列"""
        while not self._shutdown:
            try:
                # 等待事件，设置超时以便检查shutdown状态
                event = await asyncio.wait_for(
                    self._event_queue.get(),
                    timeout=1.0
                )
                
                await self._process_event_sync(event)
                self._event_queue.task_done()
                
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                self._logger.error(f"Error processing event: {e}")
                self._stats.failed_events += 1
    
    async def _process_event_sync(self, event: StreamingEvent) -> List[Any]:
        """同步处理单个事件
        
        Args:
            event: 事件对象
            
        Returns:
            List[Any]: 处理器返回值列表
        """
        start_time = asyncio.get_event_loop().time()
        results = []
        
        try:
            # 更新统计信息
            self._stats.total_events += 1
            self._stats.last_event_time = datetime.now()
            
            if event.event_type not in self._stats.events_by_type:
                self._stats.events_by_type[event.event_type] = 0
            self._stats.events_by_type[event.event_type] += 1
            
            # 获取所有相关的处理器
            handlers = []
            
            # 特定事件类型的处理器
            if event.event_type in self._handlers:
                handlers.extend(self._handlers[event.event_type])
            
            # 全局处理器
            handlers.extend(self._global_handlers)
            
            # 按优先级排序
            handlers.sort(key=lambda h: h.priority.value, reverse=True)
            
            # 执行处理器
            for handler in handlers:
                if not handler.active:
                    continue
                
                try:
                    # 更新处理器统计
                    handler.call_count += 1
                    handler.last_called = datetime.now()
                    
                    # 执行回调
                    if asyncio.iscoroutinefunction(handler.callback):
                        result = await handler.callback(event)
                    else:
                        result = handler.callback(event)
                    
                    results.append(result)
                    
                    # 如果是一次性处理器，标记为非活跃
                    if handler.once:
                        handler.active = False
                        self._stats.active_handlers -= 1
                
                except Exception as e:
                    self._logger.error(
                        f"Error in event handler {handler.handler_id}: {e}"
                    )
                    self._stats.failed_events += 1
            
            # 更新处理时间统计
            processing_time = (asyncio.get_event_loop().time() - start_time) * 1000
            self._stats.processing_time_ms += processing_time
            
            return results
            
        except Exception as e:
            self._logger.error(f"Error processing event {event.event_type}: {e}")
            self._stats.failed_events += 1
            return []
    
    def get_stats(self) -> EventStats:
        """获取事件统计信息
        
        Returns:
            EventStats: 统计信息
        """
        return self._stats
    
    def get_handlers(self, event_type: Optional[EventType] = None) -> List[EventHandler]:
        """获取处理器列表
        
        Args:
            event_type: 事件类型，如果为None则返回所有处理器
            
        Returns:
            List[EventHandler]: 处理器列表
        """
        if event_type is None:
            handlers = []
            for event_handlers in self._handlers.values():
                handlers.extend(event_handlers)
            handlers.extend(self._global_handlers)
            return handlers
        else:
            return self._handlers.get(event_type, [])
    
    def has_listeners(self, event_type: EventType) -> bool:
        """检查是否有监听器
        
        Args:
            event_type: 事件类型
            
        Returns:
            bool: 是否有监听器
        """
        return (
            event_type in self._handlers and len(self._handlers[event_type]) > 0
        ) or len(self._global_handlers) > 0
    
    def listener_count(self, event_type: Optional[EventType] = None) -> int:
        """获取监听器数量
        
        Args:
            event_type: 事件类型，如果为None则返回总数
            
        Returns:
            int: 监听器数量
        """
        if event_type is None:
            return self._stats.active_handlers
        else:
            count = len(self._handlers.get(event_type, []))
            # 全局监听器也会处理特定事件
            count += len(self._global_handlers)
            return count
    
    async def shutdown(self, timeout: float = 5.0):
        """关闭事件系统
        
        Args:
            timeout: 超时时间（秒）
        """
        self._shutdown = True
        
        # 等待队列处理完成
        if not self._event_queue.empty():
            try:
                await asyncio.wait_for(
                    self._event_queue.join(),
                    timeout=timeout
                )
            except asyncio.TimeoutError:
                self._logger.warning("Event queue shutdown timeout")
        
        # 取消处理任务
        if self._processing_task and not self._processing_task.done():
            self._processing_task.cancel()
            try:
                await self._processing_task
            except asyncio.CancelledError:
                pass
        
        # 清理所有监听器
        self.off_all()
        
        self._logger.info("Event system shutdown complete")
    
    async def close(self, timeout: float = 5.0):
        """关闭事件系统（shutdown的别名）
        
        Args:
            timeout: 超时时间（秒）
        """
        await self.shutdown(timeout)


# 全局事件发射器实例
_global_emitter: Optional[EventEmitter] = None


def get_global_emitter() -> EventEmitter:
    """获取全局事件发射器
    
    Returns:
        EventEmitter: 全局事件发射器实例
    """
    global _global_emitter
    if _global_emitter is None:
        _global_emitter = EventEmitter()
    return _global_emitter


def set_global_emitter(emitter: EventEmitter):
    """设置全局事件发射器
    
    Args:
        emitter: 事件发射器实例
    """
    global _global_emitter
    _global_emitter = emitter


# 便捷函数
async def emit_event(
    event_type: EventType,
    data: Any = None,
    session_id: Optional[str] = None,
    **kwargs
) -> List[Any]:
    """发射事件的便捷函数
    
    Args:
        event_type: 事件类型
        data: 事件数据
        session_id: 会话ID
        **kwargs: 其他参数
        
    Returns:
        List[Any]: 处理器返回值列表
    """
    from ..types.events import StreamingEvent
    
    event = StreamingEvent(
        event_type=event_type,
        data=data,
        session_id=session_id,
        **kwargs
    )
    
    emitter = get_global_emitter()
    return await emitter.emit(event)


def on_event(
    event_types: Union[EventType, List[EventType]],
    priority: EventPriority = EventPriority.NORMAL,
    once: bool = False,
    **metadata
):
    """事件监听器装饰器
    
    Args:
        event_types: 事件类型或类型列表
        priority: 优先级
        once: 是否只执行一次
        **metadata: 元数据
    """
    def decorator(func):
        emitter = get_global_emitter()
        handler_id = emitter.on(
            event_types,
            func,
            priority=priority,
            once=once,
            **metadata
        )
        
        # 将handler_id附加到函数上，便于后续移除
        func._event_handler_id = handler_id
        return func
    
    return decorator