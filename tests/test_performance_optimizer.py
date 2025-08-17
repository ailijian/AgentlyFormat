"""性能优化器测试

测试PerformanceOptimizer类的字符串增量缓存和路径匹配缓存功能。
"""

import pytest
import time
from typing import List, Dict, Any

from src.agently_format.core.performance_optimizer import PerformanceOptimizer


class TestPerformanceOptimizer:
    """性能优化器测试类"""
    
    @pytest.fixture
    def optimizer(self):
        """创建性能优化器实例"""
        return PerformanceOptimizer(
            enable_string_optimization=True,
            enable_path_optimization=True,
            enable_memory_management=True,
            max_cache_size=1000
        )
    
    def test_string_delta_cache(self, optimizer: PerformanceOptimizer):
        """测试字符串增量缓存功能"""
        old_str = "Hello World"
        new_str = "Hello Beautiful World"
        
        # 第一次计算
        start_time = time.perf_counter()
        delta1 = optimizer.calculate_string_delta(old_str, new_str)
        first_time = time.perf_counter() - start_time
        
        # 第二次计算（应该使用缓存）
        start_time = time.perf_counter()
        delta2 = optimizer.calculate_string_delta(old_str, new_str)
        second_time = time.perf_counter() - start_time
        
        # 验证结果一致性
        assert delta1 == delta2
        assert delta1['start'] == 6
        assert delta1['end'] == 11
        assert delta1['new_text'] == "Beautiful "
        
        # 验证缓存效果（第二次应该更快）
        assert second_time < first_time or second_time < 0.001  # 允许极小的时间差
        
        # 验证缓存统计
        stats = optimizer.get_cache_stats()
        assert stats['string_delta_cache']['hits'] >= 1
        assert stats['string_delta_cache']['total'] >= 2
    
    def test_path_matching_cache(self, optimizer: PerformanceOptimizer):
        """测试路径匹配缓存功能"""
        path = "users.0.profile.name"
        patterns = ["users.*.profile.*", "users.0.*", "*.name"]
        
        # 第一次匹配
        start_time = time.perf_counter()
        result1 = optimizer.match_path_patterns(path, patterns)
        first_time = time.perf_counter() - start_time
        
        # 第二次匹配（应该使用缓存）
        start_time = time.perf_counter()
        result2 = optimizer.match_path_patterns(path, patterns)
        second_time = time.perf_counter() - start_time
        
        # 验证结果一致性
        assert result1 == result2
        assert result1 is True  # 应该匹配
        
        # 验证缓存效果
        assert second_time < first_time or second_time < 0.001
        
        # 验证缓存统计
        stats = optimizer.get_cache_stats()
        assert stats['path_matching_cache']['hits'] >= 1
        assert stats['path_matching_cache']['total'] >= 2
    
    def test_cache_size_limit(self, optimizer: PerformanceOptimizer):
        """测试缓存大小限制"""
        # 填充缓存直到超过限制
        for i in range(1200):  # 超过默认1000的限制
            old_str = f"string_{i}"
            new_str = f"string_{i}_modified"
            optimizer.calculate_string_delta(old_str, new_str)
        
        stats = optimizer.get_cache_stats()
        # 缓存应该被限制在指定大小内
        assert stats['string_delta_cache']['size'] <= 1000
    
    def test_cache_clear(self, optimizer: PerformanceOptimizer):
        """测试缓存清理功能"""
        # 添加一些缓存项
        optimizer.calculate_string_delta("test1", "test1_mod")
        optimizer.match_path_patterns("test.path", ["test.*"])
        
        # 验证缓存不为空
        stats_before = optimizer.get_cache_stats()
        assert stats_before['string_delta_cache']['size'] > 0
        assert stats_before['path_matching_cache']['size'] > 0
        
        # 清理缓存
        optimizer.clear_caches()
        
        # 验证缓存已清空
        stats_after = optimizer.get_cache_stats()
        assert stats_after['string_delta_cache']['size'] == 0
        assert stats_after['path_matching_cache']['size'] == 0
    
    def test_disabled_caches(self):
        """测试禁用缓存的情况"""
        optimizer = PerformanceOptimizer(
            enable_string_optimization=False,
            enable_path_optimization=False
        )
        
        # 执行操作
        delta = optimizer.calculate_string_delta("test", "test_mod")
        match = optimizer.match_path_patterns("test.path", ["test.*"])
        
        # 验证功能正常但无缓存
        assert delta is not None
        assert match is True
        
        stats = optimizer.get_cache_stats()
        assert stats['string_delta_cache']['size'] == 0
        assert stats['path_matching_cache']['size'] == 0
    
    def test_complex_string_delta(self, optimizer: PerformanceOptimizer):
        """测试复杂字符串增量计算"""
        test_cases = [
            ("Hello", "Hello World", {'start': 5, 'end': 5, 'new_text': ' World'}),
            ("Hello World", "Hello", {'start': 5, 'end': 11, 'new_text': ''}),
            ("ABC", "XYZ", {'start': 0, 'end': 3, 'new_text': 'XYZ'}),
            ("", "Hello", {'start': 0, 'end': 0, 'new_text': 'Hello'}),
            ("Hello", "", {'start': 0, 'end': 5, 'new_text': ''}),
        ]
        
        for old_str, new_str, expected in test_cases:
            result = optimizer.calculate_string_delta(old_str, new_str)
            assert result == expected, f"Failed for {old_str} -> {new_str}"
    
    def test_complex_path_matching(self, optimizer: PerformanceOptimizer):
        """测试复杂路径匹配"""
        test_cases = [
            ("users.0.name", ["users.*.name"], True),
            ("users.0.profile.email", ["users.*.name"], False),
            ("data.items.0.value", ["data.items.*.*"], True),
            ("config.settings.debug", ["config.*"], True),
            ("nested.deep.very.deep.value", ["nested.deep.*"], True),
        ]
        
        for path, patterns, expected in test_cases:
            result = optimizer.match_path_patterns(path, patterns)
            assert result == expected, f"Failed for {path} with patterns {patterns}"
    
    def test_performance_improvement(self, optimizer: PerformanceOptimizer):
        """测试性能提升效果"""
        # 准备测试数据
        test_strings = [(f"base_string_{i}", f"base_string_{i}_modified") for i in range(100)]
        test_paths = [(f"path.{i}.value", [f"path.{i}.*", "path.*.*"]) for i in range(100)]
        
        # 测试字符串增量计算性能
        start_time = time.perf_counter()
        for old_str, new_str in test_strings:
            optimizer.calculate_string_delta(old_str, new_str)
        first_round_time = time.perf_counter() - start_time
        
        # 重复测试（应该使用缓存）
        start_time = time.perf_counter()
        for old_str, new_str in test_strings:
            optimizer.calculate_string_delta(old_str, new_str)
        second_round_time = time.perf_counter() - start_time
        
        # 验证性能提升
        assert second_round_time < first_round_time * 0.5  # 至少50%的性能提升
        
        # 测试路径匹配性能
        start_time = time.perf_counter()
        for path, patterns in test_paths:
            optimizer.match_path_patterns(path, patterns)
        first_round_time = time.perf_counter() - start_time
        
        start_time = time.perf_counter()
        for path, patterns in test_paths:
            optimizer.match_path_patterns(path, patterns)
        second_round_time = time.perf_counter() - start_time
        
        # 验证性能提升
        assert second_round_time < first_round_time * 0.5
    
    def test_memory_management_integration(self, optimizer: PerformanceOptimizer):
        """测试内存管理集成"""
        # 启用内存管理的优化器应该有内存管理器
        assert optimizer.memory_manager is not None
        
        # 注册一些缓存对象
        test_cache = {"key": "value"}
        optimizer.memory_manager.register_cache_object("test_cache", test_cache)
        
        # 验证注册成功
        memory_info = optimizer.memory_manager.get_memory_usage()
        assert memory_info['cache_objects'] >= 1
    
    def test_cache_statistics(self, optimizer: PerformanceOptimizer):
        """测试缓存统计信息"""
        # 执行一些操作
        optimizer.calculate_string_delta("test1", "test1_mod")
        optimizer.calculate_string_delta("test1", "test1_mod")  # 重复，应该命中缓存
        optimizer.match_path_patterns("test.path", ["test.*"])
        
        stats = optimizer.get_cache_stats()
        
        # 验证统计信息结构
        assert 'string_delta_cache' in stats
        assert 'path_matching_cache' in stats
        
        # 验证字符串增量缓存统计
        string_stats = stats['string_delta_cache']
        assert string_stats['total'] >= 2
        assert string_stats['hits'] >= 1
        assert string_stats['size'] >= 1
        assert 0 <= string_stats['hit_rate'] <= 1
        
        # 验证路径匹配缓存统计
        path_stats = stats['path_matching_cache']
        assert path_stats['total'] >= 1
        assert path_stats['size'] >= 1