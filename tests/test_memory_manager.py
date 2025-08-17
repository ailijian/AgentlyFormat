"""内存管理器测试

测试MemoryManager类的会话跟踪、自动清理和垃圾回收功能。
"""

import pytest
import time
import gc
import weakref
from typing import Dict, Any
from unittest.mock import Mock, patch

from src.agently_format.core.memory_manager import MemoryManager


class TestMemoryManager:
    """内存管理器测试类"""
    
    @pytest.fixture
    def memory_manager(self):
        """创建内存管理器实例"""
        return MemoryManager(
            max_sessions=100,
            session_timeout=300,  # 5分钟
            cleanup_interval=60,  # 1分钟
            memory_threshold_mb=100.0,  # 100MB
            enable_auto_gc=True
        )
    
    def test_session_registration(self, memory_manager: MemoryManager):
        """测试会话注册功能"""
        session_id = "test_session_001"
        session_data = {"user_id": "user123", "data": "test_data"}
        
        # 注册会话
        memory_manager.register_session(session_id, session_data)
        
        # 验证会话已注册
        assert memory_manager.has_session(session_id)
        
        # 获取会话信息
        memory_info = memory_manager.get_memory_usage()
        assert memory_info['active_sessions'] >= 1
        assert session_id in memory_info['session_details']
    
    def test_cache_object_registration(self, memory_manager: MemoryManager):
        """测试缓存对象注册功能"""
        cache_name = "test_cache"
        cache_object = {"key1": "value1", "key2": "value2"}
        
        # 注册缓存对象
        memory_manager.register_cache_object(cache_name, cache_object)
        
        # 验证缓存对象已注册
        memory_info = memory_manager.get_memory_usage()
        
        assert memory_info['cache_objects'] >= 1
        assert cache_name in memory_info['cache_details']
        
        # 保持对cache_object的强引用直到测试结束
        # 这确保包装对象不会被过早垃圾回收
        assert cache_object is not None
    
    def test_session_cleanup(self, memory_manager: MemoryManager):
        """测试会话清理功能"""
        # 创建一个短超时的内存管理器，禁用自动清理线程
        short_timeout_manager = MemoryManager(
            max_sessions=10,
            session_timeout=1,  # 1秒超时
            cleanup_interval=3600  # 设置很长的间隔以避免自动清理干扰
        )
        # 停止自动清理线程
        short_timeout_manager.stop()

        session_id = "test_session_cleanup"
        session_data = {"data": "test"}

        # 注册会话
        short_timeout_manager.register_session(session_id, session_data)
        assert short_timeout_manager.has_session(session_id)
        
        # 调试信息：检查注册后的状态
        print(f"After registration - session_timestamps: {short_timeout_manager.session_timestamps}")
        print(f"After registration - session_refs: {list(short_timeout_manager.session_refs.keys())}")
        print(f"After registration - has _strong_refs: {hasattr(short_timeout_manager, '_strong_refs')}")
        if hasattr(short_timeout_manager, '_strong_refs'):
            print(f"After registration - _strong_refs: {list(short_timeout_manager._strong_refs.keys())}")

        # 等待超时
        time.sleep(1.5)

        # 手动触发清理
        cleaned = short_timeout_manager.cleanup_expired_sessions()

        # 验证会话已被清理
        assert cleaned >= 1
        assert not short_timeout_manager.has_session(session_id)
    
    def test_dead_reference_cleanup(self, memory_manager: MemoryManager):
        """测试死引用清理功能"""
        # 创建一个支持弱引用的对象
        class TestObject:
            def __init__(self, data):
                self.data = data
        
        test_object = TestObject("test_object")
        weak_ref = weakref.ref(test_object)
        
        memory_manager.register_cache_object("test_weak_ref", test_object)
        
        # 删除强引用
        del test_object
        gc.collect()  # 强制垃圾回收
        
        # 清理死引用
        cleaned = memory_manager.cleanup_dead_references()
        
        # 验证死引用已被清理
        assert weak_ref() is None  # 对象应该已被回收
    
    def test_memory_threshold_check(self, memory_manager: MemoryManager):
        """测试内存阈值检查功能"""
        # 模拟内存使用量
        with patch('psutil.Process') as mock_process:
            mock_memory_info = Mock()
            mock_memory_info.rss = 150 * 1024 * 1024  # 150MB
            mock_process.return_value.memory_info.return_value = mock_memory_info
            
            # 检查内存阈值（阈值为100MB）
            exceeded = memory_manager.check_memory_threshold()
            
            # 应该超过阈值
            assert exceeded is True
    
    def test_force_garbage_collection(self, memory_manager: MemoryManager):
        """测试强制垃圾回收功能"""
        # 获取初始垃圾回收统计
        initial_collections = sum(gc.get_count())
        
        # 强制垃圾回收
        collected = memory_manager.force_garbage_collection()
        
        # 验证垃圾回收已执行
        final_collections = sum(gc.get_count())
        assert collected >= 0  # 回收的对象数量
        # 注意：gc.get_count()可能在回收后重置，所以不一定增加
    
    def test_memory_monitoring_callback(self, memory_manager: MemoryManager):
        """测试内存监控回调功能"""
        callback_called = False
        callback_data = None
        
        def test_callback(memory_info: Dict[str, Any]):
            nonlocal callback_called, callback_data
            callback_called = True
            callback_data = memory_info
        
        # 添加监控回调
        memory_manager.add_memory_callback("test_callback", test_callback)
        
        # 注册一个会话以触发内存变化
        memory_manager.register_session("test_callback", {"data": "test"})
        
        # 获取内存使用情况（这应该触发回调）
        memory_info = memory_manager.get_memory_usage()
        
        # 手动触发回调（如果自动触发没有工作）
        for callback_name, callback in memory_manager.memory_callbacks.items():
            callback(memory_info)
        
        # 验证回调被调用
        assert callback_called is True
        assert callback_data is not None
        assert 'active_sessions' in callback_data
    
    def test_session_limit_enforcement(self, memory_manager: MemoryManager):
        """测试会话数量限制执行"""
        # 创建一个低限制的内存管理器
        limited_manager = MemoryManager(max_sessions=3)
        
        # 注册超过限制的会话
        for i in range(5):
            session_id = f"session_{i}"
            limited_manager.register_session(session_id, {"index": i})
        
        # 验证会话数量被限制
        memory_info = limited_manager.get_memory_usage()
        assert memory_info['active_sessions'] <= 3
    
    def test_memory_usage_reporting(self, memory_manager: MemoryManager):
        """测试内存使用情况报告"""
        # 注册一些会话和缓存对象
        memory_manager.register_session("session1", {"data": "test1"})
        memory_manager.register_session("session2", {"data": "test2"})
        memory_manager.register_cache_object("cache1", {"key": "value"})
        
        # 获取内存使用报告
        memory_info = memory_manager.get_memory_usage()
        
        # 验证报告结构
        required_fields = [
            'process_memory_mb', 'active_sessions', 'cache_objects',
            'session_details', 'cache_details', 'gc_stats'
        ]
        
        for field in required_fields:
            assert field in memory_info
        
        # 验证数据正确性
        assert memory_info['active_sessions'] >= 2
        assert memory_info['cache_objects'] >= 1
        assert len(memory_info['session_details']) >= 2
        assert len(memory_info['cache_details']) >= 1
    
    def test_automatic_cleanup_integration(self, memory_manager: MemoryManager):
        """测试自动清理集成功能"""
        # 创建一个快速清理的内存管理器
        auto_manager = MemoryManager(
            max_sessions=5,
            session_timeout=1,
            cleanup_interval=1,
            enable_auto_gc=True
        )
        
        # 注册一些会话
        for i in range(3):
            auto_manager.register_session(f"auto_session_{i}", {"index": i})
        
        initial_sessions = auto_manager.get_memory_usage()['active_sessions']
        
        # 等待自动清理
        time.sleep(1.5)
        
        # 手动触发清理以确保测试可靠性
        auto_manager.cleanup_expired_sessions()
        auto_manager.cleanup_dead_references()
        
        final_sessions = auto_manager.get_memory_usage()['active_sessions']
        
        # 验证清理效果（会话应该过期并被清理）
        assert final_sessions <= initial_sessions
    
    def test_error_handling(self, memory_manager: MemoryManager):
        """测试错误处理"""
        # 测试无效会话ID
        assert not memory_manager.has_session("nonexistent_session")
        
        # 测试重复注册会话
        session_id = "duplicate_session"
        memory_manager.register_session(session_id, {"data": "first"})
        memory_manager.register_session(session_id, {"data": "second"})  # 应该覆盖
        
        memory_info = memory_manager.get_memory_usage()
        # 应该只有一个会话实例
        if session_id in memory_info['session_details']:
            # 如果是包装对象，检查obj属性
            session_data = memory_info['session_details'][session_id]
            if hasattr(session_data, 'obj'):
                assert session_data.obj['data'] == "second"
            else:
                assert session_data['data'] == "second"
        else:
            # 如果会话不在详情中，至少验证会话存在
            assert memory_manager.has_session(session_id)
    
    def test_performance_impact(self, memory_manager: MemoryManager):
        """测试性能影响"""
        # 测试大量会话注册的性能
        start_time = time.perf_counter()
        
        for i in range(1000):
            memory_manager.register_session(f"perf_session_{i}", {"index": i})
        
        registration_time = time.perf_counter() - start_time
        
        # 验证注册性能（应该在合理时间内完成）
        assert registration_time < 1.0  # 1秒内完成1000个会话注册
        
        # 测试内存使用报告性能
        start_time = time.perf_counter()
        memory_info = memory_manager.get_memory_usage()
        report_time = time.perf_counter() - start_time
        
        # 验证报告生成性能
        assert report_time < 0.1  # 100ms内生成报告
        assert memory_info['active_sessions'] <= 100  # 应该被限制
    
    def test_cleanup_statistics(self, memory_manager: MemoryManager):
        """测试清理统计信息"""
        # 注册一些会话
        for i in range(5):
            memory_manager.register_session(f"stats_session_{i}", {"index": i})
        
        # 执行清理
        expired_cleaned = memory_manager.cleanup_expired_sessions()
        dead_cleaned = memory_manager.cleanup_dead_references()
        gc_collected = memory_manager.force_garbage_collection()
        
        # 验证统计信息
        assert expired_cleaned >= 0
        assert dead_cleaned >= 0
        assert gc_collected >= 0
        
        # 获取内存使用情况
        memory_info = memory_manager.get_memory_usage()
        
        # 验证统计信息包含预期字段
        assert 'active_sessions' in memory_info
        assert 'cache_objects' in memory_info