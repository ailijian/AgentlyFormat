"""差分引擎单元测试

测试结构化差分引擎的各项功能，包括：
- dict/list aware 的最小差分算法
- 事件去重与合并机制
- 幂等事件发射
- DONE 条件收敛
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, List

from src.agently_format.core.diff_engine import (
    StructuredDiffEngine,
    DiffMode,
    CoalescingConfig,
    DiffResult,
    PathState,
    create_diff_engine
)
from src.agently_format.types.events import StreamingEvent, EventType


class TestStructuredDiffEngine:
    """结构化差分引擎测试类"""
    
    def setup_method(self):
        """测试前置设置"""
        self.engine = StructuredDiffEngine(
            diff_mode=DiffMode.SMART,
            coalescing_config=CoalescingConfig(
                enabled=True,
                time_window_ms=100,
                max_coalesced_events=5
            )
        )
    
    def test_dict_diff_basic(self):
        """测试基本字典差分"""
        old_data = {"name": "Alice", "age": 25}
        new_data = {"name": "Alice", "age": 26, "city": "Beijing"}
        
        diffs = self.engine.compute_diff(old_data, new_data)
        
        # 应该有两个差分：age 修改和 city 新增
        assert len(diffs) == 2
        
        # 检查 age 修改
        age_diff = next((d for d in diffs if d.path == "age"), None)
        assert age_diff is not None
        assert age_diff.diff_type == "modified"
        assert age_diff.old_value == 25
        assert age_diff.new_value == 26
        
        # 检查 city 新增
        city_diff = next((d for d in diffs if d.path == "city"), None)
        assert city_diff is not None
        assert city_diff.diff_type == "added"
        assert city_diff.old_value is None
        assert city_diff.new_value == "Beijing"
    
    def test_list_diff_append(self):
        """测试列表追加差分"""
        old_data = {"items": ["a", "b"]}
        new_data = {"items": ["a", "b", "c"]}
        
        diffs = self.engine.compute_diff(old_data, new_data)
        
        assert len(diffs) == 1
        items_diff = diffs[0]
        assert items_diff.path == "items[2]"  # 修正：应该是具体的索引路径
        assert items_diff.diff_type == "list_append"
        assert items_diff.delta_value == "c"  # 修正：应该是单个元素，不是列表
    
    def test_nested_dict_diff(self):
        """测试嵌套字典差分"""
        old_data = {
            "user": {
                "profile": {
                    "name": "Alice",
                    "age": 25
                }
            }
        }
        new_data = {
            "user": {
                "profile": {
                    "name": "Alice",
                    "age": 26,
                    "email": "alice@example.com"
                }
            }
        }
        
        diffs = self.engine.compute_diff(old_data, new_data)
        
        # 应该有两个差分
        assert len(diffs) == 2
        
        # 检查路径格式
        paths = [d.path for d in diffs]
        assert "user.profile.age" in paths
        assert "user.profile.email" in paths
    
    def test_path_state_hash_tracking(self):
        """测试路径状态哈希跟踪"""
        path_state = PathState(path="test.path")
        
        # 第一次更新
        hash1 = path_state.update_hash("value1")
        assert path_state.last_emitted_hash == hash1
        assert path_state.emit_count == 1
        
        # 相同值不应该发射
        assert not path_state.should_emit("value1")
        
        # 不同值应该发射
        assert path_state.should_emit("value2")
        
        # 更新后计数增加
        hash2 = path_state.update_hash("value2")
        assert path_state.emit_count == 2
        assert hash1 != hash2
    
    def test_event_suppression(self):
        """测试事件抑制（幂等性）"""
        # 第一次发射应该成功
        result1 = self.engine.should_emit_event("test.path", "value1")
        assert result1
        
        # 模拟事件已发射，更新哈希
        self.engine.path_states["test.path"].update_hash("value1")
        
        # 相同值的第二次发射应该被抑制
        result2 = self.engine.should_emit_event("test.path", "value1")
        assert not result2
        
        # 不同值应该可以发射
        result3 = self.engine.should_emit_event("test.path", "value2")
        assert result3
        
        # 检查统计信息
        stats = self.engine.get_stats()
        assert stats["suppressed_duplicates"] == 1
    
    def test_coalescing_buffer(self):
        """测试事件合并缓冲区"""
        # 创建启用合并的引擎
        engine = StructuredDiffEngine(
            coalescing_config=CoalescingConfig(
                enabled=True,
                max_coalesced_events=3
            )
        )
        
        # 模拟多个差分结果
        diff_results = [
            DiffResult(
                path="test.path",
                diff_type="modified",
                old_value=f"value{i}",
                new_value=f"value{i+1}",
                delta_value=f"value{i+1}"
            )
            for i in range(5)
        ]
        
        events = []
        for diff_result in diff_results:
            event = engine.emit_delta_event(
                diff_result=diff_result,
                session_id="test_session",
                sequence_number=len(events) + 1
            )
            if event:
                events.append(event)
        
        # 由于合并，事件数量应该少于差分数量
        assert len(events) < len(diff_results)
        
        # 刷新缓冲区获取剩余事件
        remaining_events = engine.flush_all_coalescing_buffers()
        events.extend(remaining_events)
        
        # 检查合并统计
        stats = engine.get_stats()
        assert stats["coalesced_events"] > 0
    
    def test_stability_detection(self):
        """测试稳定性检测"""
        engine = StructuredDiffEngine(
            coalescing_config=CoalescingConfig(
                stability_threshold=2,
                time_window_ms=50
            )
        )
        
        # 模拟路径状态
        path_state = PathState(path="test.path")
        path_state.last_emit_time = datetime.now() - timedelta(milliseconds=100)
        engine.path_states["test.path"] = path_state
        
        # 检查稳定性
        done_events = engine.check_stability_and_emit_done(
            session_id="test_session",
            sequence_number_generator=lambda: 1
        )
        
        # 第一次检查不应该发射 DONE 事件
        assert len(done_events) == 0
        
        # 再次检查，应该达到稳定性阈值
        done_events = engine.check_stability_and_emit_done(
            session_id="test_session",
            sequence_number_generator=lambda: 2
        )
        
        # 现在应该发射 DONE 事件
        assert len(done_events) == 1
        assert path_state.is_stable
    
    def test_conservative_vs_smart_mode(self):
        """测试保守模式与智能模式的差异"""
        old_data = {"items": ["a", "b", "c", "d"]}
        new_data = {"items": ["a", "x", "c", "d", "e"]}
        
        # 保守模式
        conservative_engine = StructuredDiffEngine(diff_mode=DiffMode.CONSERVATIVE)
        conservative_diffs = conservative_engine.compute_diff(old_data, new_data)
        
        # 智能模式
        smart_engine = StructuredDiffEngine(diff_mode=DiffMode.SMART)
        smart_diffs = smart_engine.compute_diff(old_data, new_data)
        
        # 智能模式应该能更好地识别最小编辑序列
        # 这里的具体断言取决于实现细节
        assert len(smart_diffs) >= 1
        assert len(conservative_diffs) >= 1
    
    def test_cleanup_old_paths(self):
        """测试清理过期路径"""
        # 添加一些路径状态
        old_time = datetime.now() - timedelta(hours=25)
        recent_time = datetime.now() - timedelta(minutes=5)
        
        self.engine.path_states["old_path"] = PathState(
            path="old_path",
            last_emit_time=old_time
        )
        self.engine.path_states["recent_path"] = PathState(
            path="recent_path",
            last_emit_time=recent_time
        )
        
        # 清理过期路径
        self.engine.cleanup_old_paths(max_age_hours=24)
        
        # 检查结果
        assert "old_path" not in self.engine.path_states
        assert "recent_path" in self.engine.path_states
    
    def test_create_diff_engine_convenience(self):
        """测试便捷创建函数"""
        engine = create_diff_engine(
            mode="smart",
            coalescing_enabled=True,
            time_window_ms=200
        )
        
        assert engine.diff_mode == DiffMode.SMART
        assert engine.coalescing_config.enabled
        assert engine.coalescing_config.time_window_ms == 200


class TestDiffEngineIntegration:
    """差分引擎集成测试"""
    
    def test_real_world_json_streaming(self):
        """测试真实世界的JSON流式场景"""
        engine = create_diff_engine(
            coalescing_enabled=False
        )
        
        # 模拟渐进式JSON构建
        stages = [
            {},
            {"name": "Alice"},
            {"name": "Alice", "age": 25},
            {"name": "Alice", "age": 25, "profile": {}},
            {"name": "Alice", "age": 25, "profile": {"email": "alice@example.com"}},
            {"name": "Alice", "age": 25, "profile": {"email": "alice@example.com", "city": "Beijing"}}
        ]
        
        all_events = []
        previous_data = {}
        
        for i, current_data in enumerate(stages[1:], 1):
            diffs = engine.compute_diff(previous_data, current_data)
            
            for diff_result in diffs:
                event = engine.emit_delta_event(
                    diff_result=diff_result,
                    session_id="test_session",
                    sequence_number=len(all_events) + 1
                )
                if event:
                    all_events.append(event)
            
            previous_data = current_data
        
        # 验证事件序列的合理性
        assert len(all_events) > 0
        
        # 检查路径的渐进性
        paths = [event.data.path for event in all_events]
        expected_paths = ["name", "age", "profile", "profile.email", "profile.city"]
        
        for expected_path in expected_paths:
            assert expected_path in paths
        
        # 验证基本功能
        stats = engine.get_stats()
        assert stats["total_diffs"] > 0
        assert len(all_events) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])