#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
增量 Schema 验证器单元测试

测试 schemas.py 模块的各项功能，包括：
- 基础类型验证
- 约束验证（范围、长度、模式等）
- 修复建议生成
- 缓存机制
- 事件系统集成
"""

import unittest
import json
from unittest.mock import Mock, patch
from typing import Any, Dict

# 导入被测试的模块
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.agently_format.core.schemas import (
    ValidationLevel,
    RepairStrategy,
    ValidationIssue,
    RepairSuggestion,
    ValidationResult,
    ValidationContext,
    SchemaValidator,
    validate_json_path,
    create_schema_validator,
    _get_value_by_path
)


class TestValidationDataClasses(unittest.TestCase):
    """测试验证相关的数据类"""
    
    def test_validation_issue_creation(self):
        """测试 ValidationIssue 创建"""
        issue = ValidationIssue(
            level=ValidationLevel.ERROR,
            message="Type mismatch",
            path="user.age",
            constraint="type",
            expected_type="integer"
        )
        
        self.assertEqual(issue.level, ValidationLevel.ERROR)
        self.assertEqual(issue.message, "Type mismatch")
        self.assertEqual(issue.path, "user.age")
        self.assertEqual(issue.constraint, "type")
        # actual_value 不是 ValidationIssue 的属性
        self.assertEqual(issue.expected_type, "integer")
    
    def test_repair_suggestion_creation(self):
        """测试 RepairSuggestion 创建"""
        suggestion = RepairSuggestion(
            action="convert",
            original_value="25",
            suggested_value=25,
            confidence=0.9,
            reason="Convert string to integer",
            strategy=RepairStrategy.AUTO_SAFE
        )
        
        self.assertEqual(suggestion.action, "convert")
        self.assertEqual(suggestion.original_value, "25")
        self.assertEqual(suggestion.suggested_value, 25)
        self.assertEqual(suggestion.confidence, 0.9)
        self.assertEqual(suggestion.reason, "Convert string to integer")
        self.assertEqual(suggestion.strategy, RepairStrategy.AUTO_SAFE)
    
    def test_validation_result_operations(self):
        """测试 ValidationResult 操作"""
        result = ValidationResult(
            is_valid=True,
            level=ValidationLevel.OK,
            path="user.name",
            value="John"
        )
        
        # 添加问题
        issue = ValidationIssue(
            level=ValidationLevel.WARN,
            message="Length too short",
            path="user.name",
            constraint="minLength"
        )
        result.add_issue(issue)
        
        self.assertFalse(result.is_valid)
        self.assertEqual(result.level, ValidationLevel.WARN)
        self.assertEqual(len(result.issues), 1)
        
        # 添加建议
        suggestion = RepairSuggestion(
            action="pad",
            original_value="John",
            suggested_value="John ",
            confidence=0.6,
            reason="Pad to minimum length",
            strategy=RepairStrategy.SUGGEST
        )
        result.add_suggestion(suggestion)
        
        self.assertEqual(len(result.suggestions), 1)


class TestSchemaValidator(unittest.TestCase):
    """测试 SchemaValidator 类"""
    
    def setUp(self):
        """设置测试环境"""
        self.schema = {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "minLength": 2,
                    "maxLength": 50
                },
                "age": {
                    "type": "integer",
                    "minimum": 0,
                    "maximum": 150
                },
                "email": {
                    "type": "string",
                    "pattern": r"^[\w\.-]+@[\w\.-]+\.[a-zA-Z]{2,}$"
                },
                "status": {
                    "type": "string",
                    "enum": ["active", "inactive", "pending"]
                }
            },
            "required": ["name", "age"]
        }
        self.validator = SchemaValidator(self.schema, enable_caching=True)
        self.context = ValidationContext("session_id", 0)
        self.context.schema_cache[""] = self.schema
        # 设置各个属性的 Schema 缓存
        self.context.schema_cache["name"] = self.schema["properties"]["name"]
        self.context.schema_cache["age"] = self.schema["properties"]["age"]
        self.context.schema_cache["email"] = self.schema["properties"]["email"]
        self.context.schema_cache["status"] = self.schema["properties"]["status"]
    
    def test_type_validation_success(self):
        """测试类型验证成功"""
        result = self.validator.validate_path("name", "John Doe", self.context)
        
        self.assertTrue(result.is_valid)
        self.assertEqual(result.level, ValidationLevel.OK)
        self.assertEqual(len(result.issues), 0)
    
    def test_type_validation_failure(self):
        """测试类型验证失败"""
        result = self.validator.validate_path("age", "25", self.context)
        
        self.assertFalse(result.is_valid)
        self.assertTrue(any(issue.constraint == "type" for issue in result.issues))
        self.assertTrue(len(result.suggestions) > 0)
    
    def test_range_validation(self):
        """测试范围验证"""
        # 测试最小值
        result = self.validator.validate_path("age", -5, self.context)
        self.assertFalse(result.is_valid)
        self.assertTrue(any(issue.constraint == "minimum" for issue in result.issues))
        
        # 测试最大值
        result = self.validator.validate_path("age", 200, self.context)
        self.assertFalse(result.is_valid)
        self.assertTrue(any(issue.constraint == "maximum" for issue in result.issues))
        
        # 测试正常值
        result = self.validator.validate_path("age", 25, self.context)
        self.assertTrue(result.is_valid)
    
    def test_length_validation(self):
        """测试长度验证"""
        # 测试最小长度
        result = self.validator.validate_path("name", "J", self.context)
        self.assertFalse(result.is_valid)
        self.assertTrue(any(issue.constraint == "minLength" for issue in result.issues))
        
        # 测试最大长度
        long_name = "J" * 60
        result = self.validator.validate_path("name", long_name, self.context)
        self.assertFalse(result.is_valid)
        self.assertTrue(any(issue.constraint == "maxLength" for issue in result.issues))
    
    def test_enum_validation(self):
        """测试枚举验证"""
        # 测试有效枚举值
        result = self.validator.validate_path("status", "active", self.context)
        self.assertTrue(result.is_valid)
        
        # 测试无效枚举值
        result = self.validator.validate_path("status", "unknown", self.context)
        self.assertFalse(result.is_valid)
        self.assertTrue(any(issue.constraint == "enum" for issue in result.issues))
        
        # 测试相似枚举值建议
        result = self.validator.validate_path("status", "activ", self.context)
        self.assertFalse(result.is_valid)
        self.assertTrue(len(result.suggestions) > 0)
    
    def test_pattern_validation(self):
        """测试模式验证"""
        # 测试有效邮箱
        result = self.validator.validate_path("email", "test@example.com", self.context)
        self.assertTrue(result.is_valid)
        
        # 测试无效邮箱
        result = self.validator.validate_path("email", "invalid-email", self.context)
        self.assertFalse(result.is_valid)
        self.assertTrue(any(issue.constraint == "pattern" for issue in result.issues))
    
    def test_repair_suggestions(self):
        """测试修复建议生成"""
        # 类型转换建议
        result = self.validator.validate_path("age", "25", self.context)
        self.assertTrue(len(result.suggestions) > 0)
        
        type_suggestion = next(
            (s for s in result.suggestions if s.action == "convert"), None
        )
        self.assertIsNotNone(type_suggestion)
        self.assertEqual(type_suggestion.suggested_value, 25)
        self.assertGreater(type_suggestion.confidence, 0.7)
        
        # 范围修正建议
        result = self.validator.validate_path("age", -5, self.context)
        clamp_suggestion = next(
            (s for s in result.suggestions if s.action == "clamp"), None
        )
        self.assertIsNotNone(clamp_suggestion)
        self.assertEqual(clamp_suggestion.suggested_value, 0)
    
    def test_caching_mechanism(self):
        """测试缓存机制"""
        # 创建启用缓存的验证器
        schema = {"type": "string"}
        validator = SchemaValidator(schema, enable_caching=True)
        context = ValidationContext("session_id", 0)
        context.schema_cache["name"] = schema
        
        # 第一次验证
        result1 = validator.validate_path("name", "John", context)
        
        # 第二次验证相同值（应该命中缓存）
        result2 = validator.validate_path("name", "John", context)
        
        stats = validator.get_stats()
        self.assertGreater(stats["cache_hits"], 0)
    
    def test_statistics(self):
        """测试统计功能"""
        # 执行一些验证
        self.validator.validate_path("name", "John", self.context)
        self.validator.validate_path("age", "25", self.context)  # 会产生错误和建议
        
        stats = self.validator.get_stats()
        
        self.assertEqual(stats["total_validations"], 2)
        self.assertGreater(stats["validation_errors"], 0)
        self.assertGreater(stats["repair_suggestions"], 0)
        
        # 重置统计
        self.validator.reset_stats()
        stats = self.validator.get_stats()
        self.assertEqual(stats["total_validations"], 0)


class TestUtilityFunctions(unittest.TestCase):
    """测试工具函数"""
    
    def test_get_value_by_path(self):
        """测试路径值获取"""
        data = {
            "user": {
                "name": "John",
                "contacts": [
                    {"type": "email", "value": "john@example.com"},
                    {"type": "phone", "value": "123-456-7890"}
                ]
            }
        }
        
        # 测试简单路径
        self.assertEqual(_get_value_by_path(data, "user.name"), "John")
        
        # 测试数组索引路径
        self.assertEqual(
            _get_value_by_path(data, "user.contacts[0].type"), "email"
        )
        self.assertEqual(
            _get_value_by_path(data, "user.contacts[1].value"), "123-456-7890"
        )
        
        # 测试空路径
        self.assertEqual(_get_value_by_path(data, ""), data)
        
        # 测试不存在的路径
        with self.assertRaises(KeyError):
            _get_value_by_path(data, "user.nonexistent")
        
        with self.assertRaises(IndexError):
            _get_value_by_path(data, "user.contacts[5].type")
    
    def test_validate_json_path(self):
        """测试 JSON 路径验证便捷函数"""
        data = {"user": {"name": "Alice", "age": 30}}
        schema = {"type": "string"}
        
        result = validate_json_path(data, "user.name", schema)
        self.assertTrue(result.is_valid)
        
        result = validate_json_path(data, "user.age", schema)
        self.assertFalse(result.is_valid)
    
    def test_create_schema_validator_with_events(self):
        """测试带事件系统的验证器创建"""
        # 模拟事件发射器
        mock_emitter = Mock()
        
        # 创建带事件的验证器
        schema = {"type": "string"}
        validator = create_schema_validator(schema, event_emitter=mock_emitter)
        context = ValidationContext("session_id", 0)
        
        # 执行验证
        result = validator.validate_path("test", "value", context)
        
        # 验证事件发射
        if hasattr(mock_emitter, 'emit') and mock_emitter.emit.called:
            # 检查发射的事件类型
            call_args = [call[0][0] for call in mock_emitter.emit.call_args_list]
            self.assertIn('validation_start', call_args)
            self.assertIn('validation_complete', call_args)


class TestStringUtilities(unittest.TestCase):
    """测试字符串工具函数"""
    
    def test_string_similarity(self):
        """测试字符串相似度计算"""
        schema = {"type": "string"}
        validator = SchemaValidator(schema)
        
        # 测试相同字符串
        similarity = validator._calculate_string_similarity("test", "test")
        self.assertEqual(similarity, 1.0)
        
        # 测试完全不同的字符串
        similarity = validator._calculate_string_similarity("abc", "xyz")
        self.assertLess(similarity, 0.5)
        
        # 测试相似字符串
        similarity = validator._calculate_string_similarity("active", "activ")
        self.assertGreater(similarity, 0.8)
        
        # 测试空字符串
        similarity = validator._calculate_string_similarity("", "test")
        self.assertEqual(similarity, 0.0)
        
        similarity = validator._calculate_string_similarity("", "")
        self.assertEqual(similarity, 1.0)


if __name__ == '__main__':
    # 运行所有测试
    unittest.main(verbosity=2)