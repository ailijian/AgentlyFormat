"""内存管理模块

提供内存监控、清理和优化功能，确保流式解析器在长时间运行时的内存稳定性。
"""

import gc
import weakref
import threading
import time
from typing import Dict, Any, Optional, Set, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta


@dataclass
class MemoryStats:
    """内存统计信息"""
    total_sessions: int = 0
    active_sessions: int = 0
    cached_items: int = 0
    memory_usage_mb: float = 0.0
    last_cleanup: Optional[datetime] = None
    cleanup_count: int = 0
    gc_collections: int = 0


class MemoryManager:
    """内存管理器
    
    负责监控和管理StreamingParser的内存使用，包括：
    1. 会话状态清理
    2. 缓存管理
    3. 垃圾回收优化
    4. 内存泄漏检测
    """
    
    def __init__(self, 
                 max_sessions: int = 1000,
                 session_timeout: int = 3600,  # 1小时
                 cleanup_interval: int = 300,   # 5分钟
                 memory_threshold_mb: float = 500.0,
                 enable_auto_gc: bool = True):
        """初始化内存管理器
        
        Args:
            max_sessions: 最大会话数量
            session_timeout: 会话超时时间（秒）
            cleanup_interval: 清理间隔（秒）
            memory_threshold_mb: 内存阈值（MB）
            enable_auto_gc: 是否启用自动垃圾回收
        """
        self.max_sessions = max_sessions
        self.session_timeout = session_timeout
        self.cleanup_interval = cleanup_interval
        self.memory_threshold_mb = memory_threshold_mb
        self.enable_auto_gc = enable_auto_gc
        
        # 统计信息
        self.stats = MemoryStats()
        
        # 会话引用跟踪
        self.session_refs: Dict[str, weakref.ref] = {}
        self.session_timestamps: Dict[str, datetime] = {}
        
        # 缓存引用跟踪
        self.cache_refs: Dict[str, weakref.ref] = {}
        
        # 清理线程
        self._cleanup_thread: Optional[threading.Thread] = None
        self._stop_cleanup = threading.Event()
        
        # 内存监控回调
        self.memory_callbacks: Dict[str, Callable] = {}
        
        # 启动清理线程
        self._start_cleanup_thread()
    
    def register_session(self, session_id: str, session_obj: Any) -> None:
        """注册会话对象
        
        Args:
            session_id: 会话ID
            session_obj: 会话对象
        """
        # 检查会话数量限制
        if len(self.session_refs) >= self.max_sessions:
            # 清理最旧的会话
            oldest_session = min(self.session_timestamps.items(), key=lambda x: x[1])
            self.unregister_session(oldest_session[0])
        
        # 创建弱引用
        def cleanup_callback(ref):
            self.session_refs.pop(session_id, None)
            self.session_timestamps.pop(session_id, None)
            self.stats.active_sessions = max(0, self.stats.active_sessions - 1)
        
        try:
            self.session_refs[session_id] = weakref.ref(session_obj, cleanup_callback)
        except TypeError:
            # 对于不支持弱引用的对象（如dict），将其存储在实例变量中以保持引用
            if not hasattr(self, '_strong_refs'):
                self._strong_refs = {}
            
            class ObjectWrapper:
                def __init__(self, obj):
                    self.obj = obj
            
            wrapper = ObjectWrapper(session_obj)
            # 保持对包装对象的强引用
            self._strong_refs[session_id] = wrapper
            self.session_refs[session_id] = weakref.ref(wrapper, cleanup_callback)
        
        self.session_timestamps[session_id] = datetime.now()
        self.stats.total_sessions += 1
        self.stats.active_sessions += 1
    
    def unregister_session(self, session_id: str) -> None:
        """注销会话对象
        
        Args:
            session_id: 会话ID
        """
        if session_id in self.session_refs:
            del self.session_refs[session_id]
        if session_id in self.session_timestamps:
            del self.session_timestamps[session_id]
        # 清理强引用
        if hasattr(self, '_strong_refs') and session_id in self._strong_refs:
            del self._strong_refs[session_id]
        self.stats.active_sessions = max(0, self.stats.active_sessions - 1)
    
    def has_session(self, session_id: str) -> bool:
        """检查会话是否存在
        
        Args:
            session_id: 会话ID
            
        Returns:
            bool: 会话是否存在且有效
        """
        if session_id not in self.session_refs:
            return False
        ref = self.session_refs[session_id]
        return ref() is not None
    
    def register_cache(self, cache_obj: Any) -> None:
        """注册缓存对象
        
        Args:
            cache_obj: 缓存对象
        """
        # 生成唯一的缓存名称
        cache_name = f"cache_{id(cache_obj)}"
        
        def cleanup_callback(ref):
            self.cache_refs.pop(cache_name, None)
            self.stats.cached_items = max(0, self.stats.cached_items - 1)
        
        try:
            # 尝试创建弱引用
            cache_ref = weakref.ref(cache_obj, cleanup_callback)
            self.cache_refs[cache_name] = cache_ref
            self.stats.cached_items += 1
        except TypeError:
            # 对于不支持弱引用的对象（如dict、list等），直接计数
            self.stats.cached_items += 1
            # 可以选择存储对象ID或其他标识符用于统计
    
    def register_cache_object(self, cache_name: str, cache_obj: Any) -> None:
        """注册缓存对象（测试兼容方法）
        
        Args:
            cache_name: 缓存名称
            cache_obj: 缓存对象
        """
        # 创建弱引用
        def cleanup_callback(ref):
            self.cache_refs.pop(cache_name, None)
            self.stats.cached_items = max(0, self.stats.cached_items - 1)
        
        try:
            self.cache_refs[cache_name] = weakref.ref(cache_obj, cleanup_callback)
            self.stats.cached_items += 1
        except TypeError:
            # 对于不支持弱引用的对象（如dict），创建一个包装类
            class CacheWrapper:
                def __init__(self, obj):
                    self.obj = obj
            
            wrapper = CacheWrapper(cache_obj)
            # 将wrapper存储在实例中以保持强引用
            if not hasattr(self, '_cache_wrappers'):
                self._cache_wrappers = {}
            self._cache_wrappers[cache_name] = wrapper
            
            def wrapper_cleanup_callback(ref):
                self.cache_refs.pop(cache_name, None)
                self._cache_wrappers.pop(cache_name, None)
                self.stats.cached_items = max(0, self.stats.cached_items - 1)
            
            self.cache_refs[cache_name] = weakref.ref(wrapper, wrapper_cleanup_callback)
            self.stats.cached_items += 1
    
    def cleanup_expired_sessions(self) -> int:
        """清理过期会话
        
        Returns:
            int: 清理的会话数量
        """
        now = datetime.now()
        expired_sessions = []
        
        for session_id, timestamp in self.session_timestamps.items():
            if now - timestamp > timedelta(seconds=self.session_timeout):
                expired_sessions.append(session_id)
        
        for session_id in expired_sessions:
            self.unregister_session(session_id)
        
        return len(expired_sessions)
    
    def cleanup_dead_references(self) -> int:
        """清理死引用
        
        Returns:
            int: 清理的引用数量
        """
        # 清理会话死引用
        dead_sessions = []
        for session_id, ref in self.session_refs.items():
            if ref() is None:
                dead_sessions.append(session_id)
        
        for session_id in dead_sessions:
            self.unregister_session(session_id)
        
        # 清理缓存死引用
        dead_cache_names = []
        for cache_name, cache_ref in self.cache_refs.items():
            if cache_ref() is None:
                dead_cache_names.append(cache_name)
        
        for cache_name in dead_cache_names:
            self.cache_refs.pop(cache_name, None)
            # 减少缓存计数
            if self.stats.cached_items > 0:
                self.stats.cached_items -= 1
        
        return len(dead_sessions) + len(dead_cache_names)
    
    def force_garbage_collection(self) -> int:
        """强制垃圾回收
        
        Returns:
            int: 回收的对象数量
        """
        if not self.enable_auto_gc:
            return 0
        
        # 执行垃圾回收
        collected = gc.collect()
        self.stats.gc_collections += 1
        
        return collected
    
    def get_memory_usage(self) -> Dict[str, Any]:
        """获取当前内存使用量和统计信息
        
        Returns:
            Dict[str, Any]: 包含内存使用量和缓存对象数量的字典
        """
        try:
            import psutil
            import os
            process = psutil.Process(os.getpid())
            memory_mb = process.memory_info().rss / 1024 / 1024
            self.stats.memory_usage_mb = memory_mb
        except ImportError:
            memory_mb = 0.0
            
        # 构建详细的会话信息
        session_details = {}
        for session_id, ref in self.session_refs.items():
            session_obj = ref()
            if session_obj is not None:
                # 如果是包装对象，提取原始对象
                if hasattr(session_obj, 'obj'):
                    session_details[session_id] = session_obj.obj
                else:
                    session_details[session_id] = session_obj
                
        # 构建缓存详细信息
        cache_details = {}
        cache_count = 0
        for cache_name, cache_ref in self.cache_refs.items():
            cache_obj = cache_ref()
            if cache_obj is not None:
                # 如果是包装对象，提取原始对象
                if hasattr(cache_obj, 'obj'):
                    cache_details[cache_name] = cache_obj.obj
                else:
                    cache_details[cache_name] = cache_obj
                cache_count += 1
                
        # 获取垃圾回收统计
        gc_stats = {
            'collections': self.stats.gc_collections,
            'counts': gc.get_count()
        }
            
        return {
            'memory_mb': memory_mb,
            'process_memory_mb': memory_mb,
            'cache_objects': cache_count,
            'active_sessions': len(session_details),
            'total_sessions': self.stats.total_sessions,
            'session_details': session_details,
            'cache_details': cache_details,
            'gc_stats': gc_stats
        }
    
    def check_memory_threshold(self) -> bool:
        """检查是否超过内存阈值
        
        Returns:
            bool: 是否超过阈值
        """
        current_memory = self.get_memory_usage()
        return current_memory['memory_mb'] > self.memory_threshold_mb
    
    def perform_cleanup(self) -> Dict[str, int]:
        """执行完整清理
        
        Returns:
            Dict[str, int]: 清理统计信息
        """
        cleanup_stats = {
            'expired_sessions': 0,
            'dead_references': 0,
            'gc_collected': 0
        }
        
        # 清理过期会话
        cleanup_stats['expired_sessions'] = self.cleanup_expired_sessions()
        
        # 清理死引用
        cleanup_stats['dead_references'] = self.cleanup_dead_references()
        
        # 如果超过内存阈值，执行垃圾回收
        if self.check_memory_threshold():
            cleanup_stats['gc_collected'] = self.force_garbage_collection()
        
        # 更新统计信息
        self.stats.last_cleanup = datetime.now()
        self.stats.cleanup_count += 1
        
        # 触发内存监控回调
        memory_info = self.get_memory_usage()
        for callback_name, callback in self.memory_callbacks.items():
            try:
                callback(memory_info)
            except Exception as e:
                print(f"Memory callback '{callback_name}' error: {e}")
        
        return cleanup_stats
    
    def add_memory_callback(self, name: str, callback: Callable) -> None:
        """添加内存监控回调
        
        Args:
            name: 回调名称
            callback: 回调函数
        """
        self.memory_callbacks[name] = callback
    
    def remove_memory_callback(self, name: str) -> None:
        """移除内存监控回调
        
        Args:
            name: 回调名称
        """
        self.memory_callbacks.pop(name, None)
    
    def _start_cleanup_thread(self) -> None:
        """启动清理线程"""
        if self._cleanup_thread is not None:
            return
        
        def cleanup_worker():
            while not self._stop_cleanup.wait(self.cleanup_interval):
                try:
                    self.perform_cleanup()
                except Exception as e:
                    print(f"Memory cleanup error: {e}")
        
        self._cleanup_thread = threading.Thread(target=cleanup_worker, daemon=True)
        self._cleanup_thread.start()
    
    def stop(self) -> None:
        """停止内存管理器"""
        self._stop_cleanup.set()
        if self._cleanup_thread:
            self._cleanup_thread.join(timeout=5.0)
            self._cleanup_thread = None
    
    def get_stats(self) -> MemoryStats:
        """获取内存统计信息
        
        Returns:
            MemoryStats: 统计信息
        """
        # 更新实时统计
        self.stats.active_sessions = len([ref for ref in self.session_refs.values() if ref() is not None])
        # 不重新计算cached_items，保持register/unregister时的计数
        self.get_memory_usage()  # 更新内存使用量
        
        return self.stats
    
    def __del__(self):
        """析构函数"""
        self.stop()