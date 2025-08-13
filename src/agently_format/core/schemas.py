"""增量 Schema 验证器模块

实现 JSON Schema 子集的增量验证功能，支持逐路径验证、修复建议缓存和置信度计算。
基于优化方案 Phase 1 设计，为流式解析提供实时 schema 校验能力。
"""

import re
import json
import time
from typing import Any, Dict, List, Optional, Tuple, Union, Set
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime
import hashlib
import asyncio

from ..types.events import StreamingEvent, EventType, create_error_event, create_delta_event
from .path_builder import PathBuilder


class ValidationLevel(Enum):
    """验证级别枚举"""
    OK = "ok"                    # 验证通过
    WARN = "warn"                # 警告（可修复）
    ERROR = "error"              # 错误（需等待更多上下文）
    CRITICAL = "critical"        # 严重错误（无法修复）


class RepairStrategy(Enum):
    """修复策略枚举"""
    NONE = "none"                # 不修复
    SUGGEST = "suggest"          # 仅建议
    AUTO_SAFE = "auto_safe"      # 自动安全修复
    AUTO_AGGRESSIVE = "auto_aggressive"  # 自动激进修复


@dataclass
class ValidationIssue:
    """验证问题"""
    level: ValidationLevel
    message: str
    path: str
    expected_type: Optional[str] = None
    actual_type: Optional[str] = None
    constraint: Optional[str] = None
    suggestion: Optional[str] = None
    confidence: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "level": self.level.value,
            "message": self.message,
            "path": self.path,
            "expected_type": self.expected_type,
            "actual_type": self.actual_type,
            "constraint": self.constraint,
            "suggestion": self.suggestion,
            "confidence": self.confidence
        }


@dataclass
class RepairSuggestion:
    """修复建议"""
    action: str                  # 修复动作（convert, default, truncate, format等）
    original_value: Any          # 原始值
    suggested_value: Any         # 建议值
    confidence: float            # 置信度 (0.0-1.0)
    reason: str                  # 修复原因
    strategy: RepairStrategy     # 修复策略
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "action": self.action,
            "original_value": self.original_value,
            "suggested_value": self.suggested_value,
            "confidence": self.confidence,
            "reason": self.reason,
            "strategy": self.strategy.value
        }


@dataclass
class ValidationResult:
    """验证结果"""
    is_valid: bool
    level: ValidationLevel
    issues: List[ValidationIssue] = field(default_factory=list)
    suggestions: List[RepairSuggestion] = field(default_factory=list)
    confidence: float = 1.0
    path: str = ""
    value: Any = None
    
    def add_issue(self, issue: ValidationIssue):
        """添加验证问题"""
        self.issues.append(issue)
        if issue.level in [ValidationLevel.WARN, ValidationLevel.ERROR, ValidationLevel.CRITICAL]:
            # WARN 级别及以上都会影响 is_valid 状态
            self.is_valid = False
            # 更新级别为最高的问题级别
            level_values = {ValidationLevel.OK: 0, ValidationLevel.WARN: 1, ValidationLevel.ERROR: 2, ValidationLevel.CRITICAL: 3}
            if level_values[issue.level] > level_values[self.level]:
                self.level = issue.level
    
    def add_suggestion(self, suggestion: RepairSuggestion):
        """添加修复建议"""
        self.suggestions.append(suggestion)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "is_valid": self.is_valid,
            "level": self.level.value,
            "issues": [issue.to_dict() for issue in self.issues],
            "suggestions": [suggestion.to_dict() for suggestion in self.suggestions],
            "confidence": self.confidence,
            "path": self.path,
            "value": self.value
        }


@dataclass
class ValidationContext:
    """验证上下文"""
    session_id: str
    sequence_number: int
    full_data: Dict[str, Any] = field(default_factory=dict)
    completed_paths: Set[str] = field(default_factory=set)
    validation_cache: Dict[str, ValidationResult] = field(default_factory=dict)
    repair_cache: Dict[str, List[RepairSuggestion]] = field(default_factory=dict)
    schema_cache: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    
    def get_cached_validation(self, path: str, value_hash: str) -> Optional[ValidationResult]:
        """获取缓存的验证结果"""
        cache_key = f"{path}:{value_hash}"
        return self.validation_cache.get(cache_key)
    
    def cache_validation(self, path: str, value_hash: str, result: ValidationResult):
        """缓存验证结果"""
        cache_key = f"{path}:{value_hash}"
        self.validation_cache[cache_key] = result
    
    def get_cached_repairs(self, path: str) -> List[RepairSuggestion]:
        """获取缓存的修复建议"""
        return self.repair_cache.get(path, [])
    
    def cache_repairs(self, path: str, suggestions: List[RepairSuggestion]):
        """缓存修复建议"""
        self.repair_cache[path] = suggestions


class SchemaValidator:
    """JSON Schema 子集验证器
    
    支持 JSON Schema 的核心子集：
    - type: 类型验证
    - required: 必填字段验证
    - enum: 枚举值验证
    - minimum/maximum: 数值范围验证
    - minLength/maxLength: 字符串长度验证
    - pattern: 正则表达式验证
    - items: 数组元素验证
    - properties: 对象属性验证
    """
    
    def __init__(self, 
                 schema: Dict[str, Any],
                 path_builder: Optional[PathBuilder] = None,
                 enable_caching: bool = True,
                 max_cache_size: int = 1000):
        """初始化 Schema 验证器
        
        Args:
            schema: JSON Schema 定义
            path_builder: 路径构建器
            enable_caching: 是否启用缓存
            max_cache_size: 最大缓存大小
        """
        self.schema = schema
        self.path_builder = path_builder or PathBuilder()
        self.enable_caching = enable_caching
        self.max_cache_size = max_cache_size
        
        # 统计信息
        self.stats = {
            "total_validations": 0,
            "cache_hits": 0,
            "validation_errors": 0,
            "repair_suggestions": 0,
            "auto_repairs": 0
        }
        
        # 预编译正则表达式缓存
        self._regex_cache: Dict[str, re.Pattern] = {}
    
    def validate_path(self, path: str, value: Any, context: ValidationContext) -> ValidationResult:
        """验证指定路径的值
        
        Args:
            path: JSON 路径
            value: 要验证的值
            context: 验证上下文
            
        Returns:
            ValidationResult: 验证结果
        """
        self.stats["total_validations"] += 1
        
        # 检查缓存
        if self.enable_caching:
            value_hash = self._get_value_hash(value)
            cached_result = context.get_cached_validation(path, value_hash)
            if cached_result:
                self.stats["cache_hits"] += 1
                return cached_result
        
        # 获取路径对应的 Schema
        schema = self._get_schema_for_path(path, context)
        
        # 创建验证结果
        result = ValidationResult(
            is_valid=True,
            level=ValidationLevel.OK,
            path=path,
            value=value
        )
        
        # 如果没有 Schema 定义，跳过验证
        if not schema:
            return result
        
        # 执行各种验证
        all_issues = []
        all_suggestions = []
        
        # 类型验证
        if "type" in schema:
            type_issues = self._validate_type(value, schema["type"], path)
            all_issues.extend(type_issues)
            
            # 生成类型转换建议
            if type_issues:
                suggestions = self._generate_type_suggestions(value, schema["type"], path)
                all_suggestions.extend(suggestions)
        
        # 范围验证（数值）
        if isinstance(value, (int, float)):
            if "minimum" in schema and value < schema["minimum"]:
                all_issues.append(ValidationIssue(
                    level=ValidationLevel.ERROR,
                    message=f"Value {value} is below minimum {schema['minimum']}",
                    path=path,
                    constraint="minimum"
                ))
                all_suggestions.append(RepairSuggestion(
                    action="clamp",
                    original_value=value,
                    suggested_value=schema["minimum"],
                    confidence=0.9,
                    reason=f"Clamp to minimum value {schema['minimum']}",
                    strategy=RepairStrategy.AUTO_SAFE
                ))
            
            if "maximum" in schema and value > schema["maximum"]:
                all_issues.append(ValidationIssue(
                    level=ValidationLevel.ERROR,
                    message=f"Value {value} is above maximum {schema['maximum']}",
                    path=path,
                    constraint="maximum"
                ))
                all_suggestions.append(RepairSuggestion(
                    action="clamp",
                    original_value=value,
                    suggested_value=schema["maximum"],
                    confidence=0.9,
                    reason=f"Clamp to maximum value {schema['maximum']}",
                    strategy=RepairStrategy.AUTO_SAFE
                ))
        
        # 长度验证（字符串）
        if isinstance(value, str):
            if "minLength" in schema and len(value) < schema["minLength"]:
                all_issues.append(ValidationIssue(
                    level=ValidationLevel.ERROR,
                    message=f"String length {len(value)} is below minimum {schema['minLength']}",
                    path=path,
                    constraint="minLength"
                ))
            
            if "maxLength" in schema and len(value) > schema["maxLength"]:
                all_issues.append(ValidationIssue(
                    level=ValidationLevel.ERROR,
                    message=f"String length {len(value)} is above maximum {schema['maxLength']}",
                    path=path,
                    constraint="maxLength"
                ))
        
        # 枚举验证
        if "enum" in schema and value not in schema["enum"]:
            all_issues.append(ValidationIssue(
                level=ValidationLevel.ERROR,
                message=f"Value '{value}' is not in allowed enum values {schema['enum']}",
                path=path,
                constraint="enum"
            ))
            
            # 生成相似值建议
            if isinstance(value, str):
                best_match = self._find_best_enum_match(value, schema["enum"])
                if best_match:
                    all_suggestions.append(RepairSuggestion(
                        action="replace",
                        original_value=value,
                        suggested_value=best_match,
                        confidence=0.8,
                        reason=f"Replace with similar enum value '{best_match}'",
                        strategy=RepairStrategy.SUGGEST
                    ))
        
        # 模式验证（正则表达式）
        if "pattern" in schema and isinstance(value, str):
            pattern = self._get_compiled_regex(schema["pattern"])
            if not pattern.match(value):
                all_issues.append(ValidationIssue(
                    level=ValidationLevel.ERROR,
                    message=f"String '{value}' does not match pattern '{schema['pattern']}'",
                    path=path,
                    constraint="pattern"
                ))
        
        # 添加问题到结果
        for issue in all_issues:
            result.add_issue(issue)
        
        # 添加建议到结果
        for suggestion in all_suggestions:
            result.add_suggestion(suggestion)
        
        # 计算置信度
        result.confidence = 1.0 if result.is_valid else 0.5
        
        # 更新统计
        if not result.is_valid:
            self.stats["validation_errors"] += 1
        if all_suggestions:
            self.stats["repair_suggestions"] += len(all_suggestions)
        
        # 缓存结果
        if self.enable_caching:
            value_hash = self._get_value_hash(value)
            context.cache_validation(path, value_hash, result)
        
        return result
    
    def get_stats(self) -> Dict[str, int]:
        """获取统计信息"""
        return self.stats.copy()
    
    def reset_stats(self):
        """重置统计信息"""
        for key in self.stats:
            self.stats[key] = 0
    
    def _get_value_hash(self, value: Any) -> str:
        """计算值的哈希
        
        Args:
            value: 要计算哈希的值
            
        Returns:
            str: 值的哈希字符串
        """
        try:
            # 使用 JSON 序列化确保一致性
            value_str = json.dumps(value, sort_keys=True, default=str)
            return hashlib.md5(value_str.encode()).hexdigest()[:16]
        except Exception:
            # 如果序列化失败，使用字符串表示
            return hashlib.md5(str(value).encode()).hexdigest()[:16]
    
    def _get_schema_for_path(self, path: str, context: ValidationContext) -> Dict[str, Any]:
        """获取指定路径的 Schema 定义
        
        Args:
            path: JSON 路径
            context: 验证上下文
            
        Returns:
            Dict[str, Any]: 路径对应的 Schema
        """
        # 检查缓存
        if path in context.schema_cache:
            return context.schema_cache[path]
        
        # 解析路径并导航到对应的 Schema
        schema = self.schema
        if not path:
            return schema
            
        path_parts = path.split('.')
        
        for part in path_parts:
            if isinstance(schema, dict):
                if "properties" in schema and part in schema["properties"]:
                    schema = schema["properties"][part]
                elif "additionalProperties" in schema:
                    if isinstance(schema["additionalProperties"], dict):
                        schema = schema["additionalProperties"]
                    else:
                        # additionalProperties: false 或 true
                        schema = {}
                else:
                    schema = {}
            elif "items" in schema:
                schema = schema["items"]
            else:
                schema = {}
        
        # 缓存结果
        context.schema_cache[path] = schema
        return schema
    
    def _validate_type(self, value: Any, expected_type: str, path: str) -> List[ValidationIssue]:
        """验证类型
        
        Args:
            value: 要验证的值
            expected_type: 期望的类型
            path: JSON 路径
            
        Returns:
            List[ValidationIssue]: 验证问题列表
        """
        issues = []
        actual_type = type(value).__name__
        
        # 类型映射
        type_mapping = {
            "string": str,
            "number": (int, float),
            "integer": int,
            "boolean": bool,
            "array": list,
            "object": dict,
            "null": type(None)
        }
        
        expected_python_type = type_mapping.get(expected_type)
        if expected_python_type and not isinstance(value, expected_python_type):
            issues.append(ValidationIssue(
                level=ValidationLevel.ERROR,
                message=f"Type mismatch: expected {expected_type}, got {actual_type}",
                path=path,
                expected_type=expected_type,
                actual_type=actual_type,
                constraint="type"
            ))
        
        return issues
    
    def _generate_type_suggestions(self, value: Any, expected_type: str, path: str) -> List[RepairSuggestion]:
        """生成类型转换建议
        
        Args:
            value: 当前值
            expected_type: 期望类型
            path: JSON 路径
            
        Returns:
            List[RepairSuggestion]: 修复建议列表
        """
        suggestions = []
        
        try:
            if expected_type == "integer" and isinstance(value, str):
                # 尝试转换为整数
                converted = int(value)
                suggestions.append(RepairSuggestion(
                    action="convert",
                    original_value=value,
                    suggested_value=converted,
                    confidence=0.9,
                    reason=f"Convert string '{value}' to integer {converted}",
                    strategy=RepairStrategy.AUTO_SAFE
                ))
            elif expected_type == "number" and isinstance(value, str):
                # 尝试转换为数字
                converted = float(value)
                suggestions.append(RepairSuggestion(
                    action="convert",
                    original_value=value,
                    suggested_value=converted,
                    confidence=0.9,
                    reason=f"Convert string '{value}' to number {converted}",
                    strategy=RepairStrategy.AUTO_SAFE
                ))
            elif expected_type == "string" and not isinstance(value, str):
                # 转换为字符串
                converted = str(value)
                suggestions.append(RepairSuggestion(
                    action="convert",
                    original_value=value,
                    suggested_value=converted,
                    confidence=0.8,
                    reason=f"Convert {type(value).__name__} to string '{converted}'",
                    strategy=RepairStrategy.AUTO_SAFE
                ))
        except (ValueError, TypeError):
            # 转换失败，不提供建议
            pass
        
        return suggestions
    
    def _find_best_enum_match(self, value: str, enum_values: List[str]) -> Optional[str]:
        """找到最佳的枚举值匹配
        
        Args:
            value: 输入值
            enum_values: 枚举值列表
            
        Returns:
            Optional[str]: 最佳匹配的枚举值
        """
        if not isinstance(value, str) or not enum_values:
            return None
        
        best_match = None
        best_similarity = 0.0
        
        for enum_val in enum_values:
            if isinstance(enum_val, str):
                similarity = self._calculate_string_similarity(value.lower(), enum_val.lower())
                if similarity > best_similarity and similarity > 0.6:  # 相似度阈值
                    best_similarity = similarity
                    best_match = enum_val
        
        return best_match
    
    def _calculate_string_similarity(self, s1: str, s2: str) -> float:
        """计算字符串相似度（简单的编辑距离算法）
        
        Args:
            s1: 字符串1
            s2: 字符串2
            
        Returns:
            float: 相似度（0-1之间）
        """
        if s1 == s2:
            return 1.0
        
        if not s1 and not s2:
            return 1.0
        
        if not s1 or not s2:
            return 0.0
        
        # 简单的编辑距离计算
        len1, len2 = len(s1), len(s2)
        if len1 > len2:
            s1, s2 = s2, s1
            len1, len2 = len2, len1
        
        distances = list(range(len1 + 1))
        
        for i2, c2 in enumerate(s2):
            new_distances = [i2 + 1]
            for i1, c1 in enumerate(s1):
                if c1 == c2:
                    new_distances.append(distances[i1])
                else:
                    new_distances.append(1 + min(distances[i1], distances[i1 + 1], new_distances[-1]))
            distances = new_distances
        
        max_len = max(len1, len2)
        return 1.0 - (distances[-1] / max_len) if max_len > 0 else 0.0
    
    def _get_compiled_regex(self, pattern: str) -> re.Pattern:
        """获取编译后的正则表达式
        
        Args:
            pattern: 正则表达式模式
            
        Returns:
            re.Pattern: 编译后的正则表达式
        """
        if pattern not in self._regex_cache:
            try:
                self._regex_cache[pattern] = re.compile(pattern)
            except re.error:
                # 如果正则表达式无效，使用一个永远不匹配的模式
                self._regex_cache[pattern] = re.compile(r'(?!.*)')
        
        return self._regex_cache[pattern]


# 便捷函数
def validate_json_path(data: Dict[str, Any], path: str, schema: Dict[str, Any], 
                      enable_caching: bool = True) -> ValidationResult:
    """验证 JSON 路径的便捷函数
    
    Args:
        data: JSON 数据
        path: JSON 路径（如 'user.name'）
        schema: Schema 定义
        enable_caching: 是否启用缓存
        
    Returns:
        ValidationResult: 验证结果
    """
    # 创建一个包含完整 Schema 的验证器
    full_schema = {
        "type": "object",
        "properties": {}
    }
    
    # 如果传入的 schema 已经是完整的对象 schema，直接使用
    if "properties" in schema:
        full_schema = schema
    else:
        # 否则，将传入的 schema 作为指定路径的 schema
        path_parts = path.split('.')
        current_schema = full_schema
        
        for i, part in enumerate(path_parts):
            if i == len(path_parts) - 1:
                # 最后一个部分，设置实际的 schema
                current_schema["properties"][part] = schema
            else:
                # 中间部分，创建嵌套对象
                current_schema["properties"][part] = {
                    "type": "object",
                    "properties": {}
                }
                current_schema = current_schema["properties"][part]
    
    validator = SchemaValidator(full_schema, enable_caching=enable_caching)
    context = ValidationContext("session_id", 0)
    context.schema_cache[""] = full_schema
    
    try:
        # 获取路径对应的值
        value = _get_value_by_path(data, path)
        return validator.validate_path(path, value, context)
    except (KeyError, IndexError, TypeError):
        # 路径不存在，创建一个错误结果
        result = ValidationResult(
            is_valid=False,
            level=ValidationLevel.ERROR,
            path=path,
            value=None
        )
        result.add_issue(ValidationIssue(
            level=ValidationLevel.ERROR,
            message=f"Path '{path}' does not exist in data",
            path=path,
            constraint="existence"
        ))
        return result


def _get_value_by_path(data: Any, path: str) -> Any:
    """根据路径获取值
    
    Args:
        data: JSON 数据
        path: JSON 路径（如 'user.name' 或 'items[0].id'）
        
    Returns:
        Any: 路径对应的值
        
    Raises:
        KeyError: 路径不存在
        IndexError: 数组索引超出范围
        TypeError: 类型错误
    """
    if not path:
        return data
    
    current = data
    parts = path.split('.')
    
    for part in parts:
        if '[' in part and ']' in part:
            # 处理数组索引，如 'items[0]'
            key, index_part = part.split('[', 1)
            index = int(index_part.rstrip(']'))
            
            if key:
                current = current[key]
            current = current[index]
        else:
            # 普通属性访问
            current = current[part]
    
    return current


def create_schema_validator(schema: Dict[str, Any], enable_caching: bool = True, 
                          event_emitter=None) -> SchemaValidator:
    """创建 Schema 验证器的便捷函数
    
    Args:
        schema: Schema 定义
        enable_caching: 是否启用缓存
        event_emitter: 事件发射器（可选）
        
    Returns:
        SchemaValidator: 验证器实例
    """
    validator = SchemaValidator(schema, enable_caching=enable_caching)
    
    if event_emitter:
        # 集成事件系统
        validator._event_emitter = event_emitter
        
        # 重写 validate_path 方法以支持事件发射
        original_validate = validator.validate_path
        
        def validate_with_events(path: str, value: Any, context: ValidationContext) -> ValidationResult:
            # 发射验证开始事件
            event_emitter.emit('validation_start', {
                'path': path,
                'value': value,
                'timestamp': time.time()
            })
            
            try:
                result = original_validate(path, value, context)
                
                # 根据验证结果发射相应事件
                if not result.is_valid:
                    if any(issue.level == ValidationLevel.CRITICAL for issue in result.issues):
                        event_emitter.emit('validation_error', {
                            'path': path,
                            'issues': [issue.__dict__ for issue in result.issues],
                            'suggestions': [s.__dict__ for s in result.suggestions],
                            'confidence': result.confidence
                        })
                    else:
                        event_emitter.emit('validation_warning', {
                            'path': path,
                            'issues': [issue.__dict__ for issue in result.issues],
                            'suggestions': [s.__dict__ for s in result.suggestions],
                            'confidence': result.confidence
                        })
                
                # 如果有高置信度的修复建议，发射 DELTA 事件
                if result.suggestions:
                    high_confidence_suggestions = [
                        s for s in result.suggestions 
                        if s.confidence > 0.8 and s.strategy == RepairStrategy.AUTO_SAFE
                    ]
                    
                    if high_confidence_suggestions:
                        event_emitter.emit('validation_delta', {
                            'path': path,
                            'original_value': value,
                            'suggested_value': high_confidence_suggestions[0].suggested_value,
                            'confidence': high_confidence_suggestions[0].confidence,
                            'reason': high_confidence_suggestions[0].reason
                        })
                
                # 发射验证完成事件
                duration = 0
                if hasattr(event_emitter, '_last_event_time') and isinstance(event_emitter._last_event_time, (int, float)):
                    duration = time.time() - event_emitter._last_event_time
                
                event_emitter.emit('validation_complete', {
                    'path': path,
                    'is_valid': result.is_valid,
                    'confidence': result.confidence,
                    'duration': duration
                })
                
                return result
                
            except Exception as e:
                # 发射验证错误事件
                event_emitter.emit('validation_error', {
                    'path': path,
                    'error': str(e),
                    'error_type': type(e).__name__
                })
                raise
        
        validator.validate_path = validate_with_events
    
    return validator
    
    def _generate_repair_suggestions(self, value: Any, schema: Dict[str, Any], 
                                   issues: List[ValidationIssue], path: str) -> List[RepairSuggestion]:
        """生成修复建议
        
        Args:
            value: 原始值
            schema: Schema 定义
            issues: 验证问题列表
            path: JSON 路径
            
        Returns:
            List[RepairSuggestion]: 修复建议列表
        """
        suggestions = []
        
        for issue in issues:
            if issue.constraint == "type":
                suggestions.extend(self._suggest_type_conversion(value, issue.expected_type, path))
            elif issue.constraint == "enum":
                suggestions.extend(self._suggest_enum_correction(value, schema.get("enum", []), path))
            elif issue.constraint == "minimum":
                suggestions.extend(self._suggest_range_correction(value, schema, "minimum", path))
            elif issue.constraint == "maximum":
                suggestions.extend(self._suggest_range_correction(value, schema, "maximum", path))
            elif issue.constraint == "minLength":
                suggestions.extend(self._suggest_length_correction(value, schema, "minLength", path))
            elif issue.constraint == "maxLength":
                suggestions.extend(self._suggest_length_correction(value, schema, "maxLength", path))
            elif issue.constraint == "pattern":
                suggestions.extend(self._suggest_pattern_correction(value, schema.get("pattern", ""), path))
            elif issue.constraint == "required":
                suggestions.extend(self._suggest_default_value(schema, path))
        
        return suggestions
    
    def _suggest_type_conversion(self, value: Any, expected_type: str, path: str) -> List[RepairSuggestion]:
        """建议类型转换
        
        Args:
            value: 原始值
            expected_type: 期望类型
            path: JSON 路径
            
        Returns:
            List[RepairSuggestion]: 修复建议列表
        """
        suggestions = []
        
        try:
            if expected_type == "string":
                suggested_value = str(value)
                confidence = 0.9 if isinstance(value, (int, float, bool)) else 0.7
                suggestions.append(RepairSuggestion(
                    action="convert",
                    original_value=value,
                    suggested_value=suggested_value,
                    confidence=confidence,
                    reason=f"Convert {type(value).__name__} to string",
                    strategy=RepairStrategy.AUTO_SAFE
                ))
            
            elif expected_type == "number" and isinstance(value, str):
                # 尝试转换为数字
                if value.replace('.', '').replace('-', '').isdigit():
                    suggested_value = float(value) if '.' in value else int(value)
                    suggestions.append(RepairSuggestion(
                        action="convert",
                        original_value=value,
                        suggested_value=suggested_value,
                        confidence=0.8,
                        reason="Convert string to number",
                        strategy=RepairStrategy.AUTO_SAFE
                    ))
            
            elif expected_type == "integer" and isinstance(value, float):
                if value.is_integer():
                    suggestions.append(RepairSuggestion(
                        action="convert",
                        original_value=value,
                        suggested_value=int(value),
                        confidence=0.9,
                        reason="Convert float to integer",
                        strategy=RepairStrategy.AUTO_SAFE
                    ))
            
            elif expected_type == "boolean":
                if isinstance(value, str):
                    if value.lower() in ['true', '1', 'yes', 'on']:
                        suggestions.append(RepairSuggestion(
                            action="convert",
                            original_value=value,
                            suggested_value=True,
                            confidence=0.8,
                            reason="Convert string to boolean",
                            strategy=RepairStrategy.AUTO_SAFE
                        ))
                    elif value.lower() in ['false', '0', 'no', 'off']:
                        suggestions.append(RepairSuggestion(
                            action="convert",
                            original_value=value,
                            suggested_value=False,
                            confidence=0.8,
                            reason="Convert string to boolean",
                            strategy=RepairStrategy.AUTO_SAFE
                        ))
                elif isinstance(value, (int, float)):
                    suggestions.append(RepairSuggestion(
                        action="convert",
                        original_value=value,
                        suggested_value=bool(value),
                        confidence=0.7,
                        reason="Convert number to boolean",
                        strategy=RepairStrategy.AUTO_SAFE
                    ))
        
        except Exception:
            pass
        
        return suggestions
    
    def _suggest_enum_correction(self, value: Any, enum_values: List[Any], path: str) -> List[RepairSuggestion]:
        """建议枚举值修正
        
        Args:
            value: 原始值
            enum_values: 允许的枚举值
            path: JSON 路径
            
        Returns:
            List[RepairSuggestion]: 修复建议列表
        """
        suggestions = []
        
        if not enum_values:
            return suggestions
        
        # 字符串相似度匹配
        if isinstance(value, str):
            for enum_val in enum_values:
                if isinstance(enum_val, str):
                    # 简单的相似度计算（可以使用更复杂的算法）
                    similarity = self._calculate_string_similarity(value.lower(), enum_val.lower())
                    if similarity > 0.6:
                        suggestions.append(RepairSuggestion(
                            action="correct",
                            original_value=value,
                            suggested_value=enum_val,
                            confidence=similarity,
                            reason=f"Similar to allowed value '{enum_val}'",
                            strategy=RepairStrategy.SUGGEST
                        ))
        
        # 如果没有找到相似的，建议第一个枚举值
        if not suggestions:
            suggestions.append(RepairSuggestion(
                action="default",
                original_value=value,
                suggested_value=enum_values[0],
                confidence=0.3,
                reason=f"Use default enum value",
                strategy=RepairStrategy.SUGGEST
            ))
        
        return suggestions
    
    def _suggest_range_correction(self, value: Union[int, float], schema: Dict[str, Any], 
                                constraint: str, path: str) -> List[RepairSuggestion]:
        """建议范围修正
        
        Args:
            value: 原始值
            schema: Schema 定义
            constraint: 约束类型
            path: JSON 路径
            
        Returns:
            List[RepairSuggestion]: 修复建议列表
        """
        suggestions = []
        
        if constraint == "minimum" and "minimum" in schema:
            suggestions.append(RepairSuggestion(
                action="clamp",
                original_value=value,
                suggested_value=schema["minimum"],
                confidence=0.8,
                reason=f"Clamp to minimum value {schema['minimum']}",
                strategy=RepairStrategy.AUTO_SAFE
            ))
        
        elif constraint == "maximum" and "maximum" in schema:
            suggestions.append(RepairSuggestion(
                action="clamp",
                original_value=value,
                suggested_value=schema["maximum"],
                confidence=0.8,
                reason=f"Clamp to maximum value {schema['maximum']}",
                strategy=RepairStrategy.AUTO_SAFE
            ))
        
        return suggestions
    
    def _suggest_length_correction(self, value: str, schema: Dict[str, Any], 
                                 constraint: str, path: str) -> List[RepairSuggestion]:
        """建议长度修正
        
        Args:
            value: 原始字符串
            schema: Schema 定义
            constraint: 约束类型
            path: JSON 路径
            
        Returns:
            List[RepairSuggestion]: 修复建议列表
        """
        suggestions = []
        
        if constraint == "minLength" and "minLength" in schema:
            min_length = schema["minLength"]
            if len(value) < min_length:
                # 建议填充
                padding = " " * (min_length - len(value))
                suggestions.append(RepairSuggestion(
                    action="pad",
                    original_value=value,
                    suggested_value=value + padding,
                    confidence=0.6,
                    reason=f"Pad to minimum length {min_length}",
                    strategy=RepairStrategy.SUGGEST
                ))
        
        elif constraint == "maxLength" and "maxLength" in schema:
            max_length = schema["maxLength"]
            if len(value) > max_length:
                # 建议截断
                suggestions.append(RepairSuggestion(
                    action="truncate",
                    original_value=value,
                    suggested_value=value[:max_length],
                    confidence=0.7,
                    reason=f"Truncate to maximum length {max_length}",
                    strategy=RepairStrategy.AUTO_SAFE
                ))
        
        return suggestions
    
    def _suggest_pattern_correction(self, value: str, pattern: str, path: str) -> List[RepairSuggestion]:
        """建议模式修正
        
        Args:
            value: 原始字符串
            pattern: 正则表达式模式
            path: JSON 路径
            
        Returns:
            List[RepairSuggestion]: 修复建议列表
        """
        suggestions = []
        
        # 简单的模式修正（可以扩展更复杂的逻辑）
        if pattern:
            # 例如：电子邮件格式修正
            if "@" in pattern and "@" not in value and "." in value:
                # 可能是缺少 @ 符号
                parts = value.split(".")
                if len(parts) >= 2:
                    suggested_value = f"{parts[0]}@{'.'.join(parts[1:])}"
                    suggestions.append(RepairSuggestion(
                        action="format",
                        original_value=value,
                        suggested_value=suggested_value,
                        confidence=0.5,
                        reason="Add missing @ symbol for email format",
                        strategy=RepairStrategy.SUGGEST
                    ))
        
        return suggestions
    
    def _suggest_default_value(self, schema: Dict[str, Any], path: str) -> List[RepairSuggestion]:
        """建议默认值
        
        Args:
            schema: Schema 定义
            path: JSON 路径
            
        Returns:
            List[RepairSuggestion]: 修复建议列表
        """
        suggestions = []
        
        # 检查是否有默认值定义
        if "default" in schema:
            suggestions.append(RepairSuggestion(
                action="default",
                original_value=None,
                suggested_value=schema["default"],
                confidence=0.9,
                reason="Use schema default value",
                strategy=RepairStrategy.AUTO_SAFE
            ))
        else:
            # 根据类型提供默认值
            schema_type = schema.get("type")
            if schema_type == "string":
                default_value = ""
            elif schema_type == "number":
                default_value = 0
            elif schema_type == "integer":
                default_value = 0
            elif schema_type == "boolean":
                default_value = False
            elif schema_type == "array":
                default_value = []
            elif schema_type == "object":
                default_value = {}
            else:
                default_value = None
            
            if default_value is not None:
                suggestions.append(RepairSuggestion(
                    action="default",
                    original_value=None,
                    suggested_value=default_value,
                    confidence=0.7,
                    reason=f"Use type default for {schema_type}",
                    strategy=RepairStrategy.SUGGEST
                ))
        
        return suggestions
    
    def _calculate_string_similarity(self, str1: str, str2: str) -> float:
        """计算字符串相似度（简单实现）
        
        Args:
            str1: 字符串1
            str2: 字符串2
            
        Returns:
            float: 相似度 (0.0-1.0)
        """
        if not str1 or not str2:
            return 0.0
        
        # 简单的编辑距离算法
        len1, len2 = len(str1), len(str2)
        if len1 == 0:
            return 0.0 if len2 > 0 else 1.0
        if len2 == 0:
            return 0.0
        
        # 创建距离矩阵
        matrix = [[0] * (len2 + 1) for _ in range(len1 + 1)]
        
        # 初始化
        for i in range(len1 + 1):
            matrix[i][0] = i
        for j in range(len2 + 1):
            matrix[0][j] = j
        
        # 计算编辑距离
        for i in range(1, len1 + 1):
            for j in range(1, len2 + 1):
                cost = 0 if str1[i-1] == str2[j-1] else 1
                matrix[i][j] = min(
                    matrix[i-1][j] + 1,      # 删除
                    matrix[i][j-1] + 1,      # 插入
                    matrix[i-1][j-1] + cost  # 替换
                )
        
        # 转换为相似度
        max_len = max(len1, len2)
        distance = matrix[len1][len2]
        return 1.0 - (distance / max_len)
    
    def _calculate_confidence(self, result: ValidationResult) -> float:
        """计算验证结果的置信度
        
        Args:
            result: 验证结果
            
        Returns:
            float: 置信度 (0.0-1.0)
        """
        if result.is_valid:
            return 1.0
        
        # 基于问题严重程度和修复建议质量计算置信度
        error_count = sum(1 for issue in result.issues if issue.level == ValidationLevel.ERROR)
        critical_count = sum(1 for issue in result.issues if issue.level == ValidationLevel.CRITICAL)
        
        # 基础置信度
        base_confidence = 0.5
        
        # 严重错误降低置信度
        if critical_count > 0:
            base_confidence *= 0.2
        elif error_count > 0:
            base_confidence *= 0.6
        
        # 有修复建议提高置信度
        if result.suggestions:
            avg_suggestion_confidence = sum(s.confidence for s in result.suggestions) / len(result.suggestions)
            base_confidence = min(1.0, base_confidence + avg_suggestion_confidence * 0.3)
        
        return base_confidence
    
    def get_stats(self) -> Dict[str, Any]:
        """获取验证统计信息
        
        Returns:
            Dict[str, Any]: 统计信息
        """
        total = self.stats["total_validations"]
        return {
            **self.stats,
            "cache_hit_rate": (self.stats["cache_hits"] / total * 100) if total > 0 else 0,
            "error_rate": (self.stats["validation_errors"] / total * 100) if total > 0 else 0,
            "suggestion_rate": (self.stats["repair_suggestions"] / total * 100) if total > 0 else 0
        }
    
    def reset_stats(self):
        """重置统计信息"""
        self.stats = {
            "total_validations": 0,
            "cache_hits": 0,
            "validation_errors": 0,
            "repair_suggestions": 0,
            "auto_repairs": 0
        }
    
    def _validate_enum(self, value: Any, enum_values: List[Any], path: str) -> List[ValidationIssue]:
        """验证枚举值
        
        Args:
            value: 要验证的值
            enum_values: 允许的枚举值列表
            path: JSON 路径
            
        Returns:
            List[ValidationIssue]: 验证问题列表
        """
        issues = []
        
        if value not in enum_values:
            issues.append(ValidationIssue(
                level=ValidationLevel.ERROR,
                message=f"Value '{value}' is not in allowed enum values: {enum_values}",
                path=path,
                constraint="enum",
                suggestion=f"Use one of: {', '.join(map(str, enum_values))}"
            ))
        
        return issues
    
    def _validate_numeric_range(self, value: Union[int, float], schema: Dict[str, Any], path: str) -> List[ValidationIssue]:
        """验证数值范围
        
        Args:
            value: 要验证的数值
            schema: Schema 定义
            path: JSON 路径
            
        Returns:
            List[ValidationIssue]: 验证问题列表
        """
        issues = []
        
        if "minimum" in schema and value < schema["minimum"]:
            issues.append(ValidationIssue(
                level=ValidationLevel.ERROR,
                message=f"Value {value} is less than minimum {schema['minimum']}",
                path=path,
                constraint="minimum"
            ))
        
        if "maximum" in schema and value > schema["maximum"]:
            issues.append(ValidationIssue(
                level=ValidationLevel.ERROR,
                message=f"Value {value} is greater than maximum {schema['maximum']}",
                path=path,
                constraint="maximum"
            ))
        
        if "exclusiveMinimum" in schema and value <= schema["exclusiveMinimum"]:
            issues.append(ValidationIssue(
                level=ValidationLevel.ERROR,
                message=f"Value {value} is not greater than exclusive minimum {schema['exclusiveMinimum']}",
                path=path,
                constraint="exclusiveMinimum"
            ))
        
        if "exclusiveMaximum" in schema and value >= schema["exclusiveMaximum"]:
            issues.append(ValidationIssue(
                level=ValidationLevel.ERROR,
                message=f"Value {value} is not less than exclusive maximum {schema['exclusiveMaximum']}",
                path=path,
                constraint="exclusiveMaximum"
            ))
        
        return issues
    
    def _validate_string_constraints(self, value: str, schema: Dict[str, Any], path: str) -> List[ValidationIssue]:
        """验证字符串约束
        
        Args:
            value: 要验证的字符串
            schema: Schema 定义
            path: JSON 路径
            
        Returns:
            List[ValidationIssue]: 验证问题列表
        """
        issues = []
        
        # 长度验证
        if "minLength" in schema and len(value) < schema["minLength"]:
            issues.append(ValidationIssue(
                level=ValidationLevel.ERROR,
                message=f"String length {len(value)} is less than minimum {schema['minLength']}",
                path=path,
                constraint="minLength"
            ))
        
        if "maxLength" in schema and len(value) > schema["maxLength"]:
            issues.append(ValidationIssue(
                level=ValidationLevel.WARN,
                message=f"String length {len(value)} exceeds maximum {schema['maxLength']}",
                path=path,
                constraint="maxLength",
                suggestion=f"Truncate to {schema['maxLength']} characters"
            ))
        
        # 正则表达式验证
        if "pattern" in schema:
            pattern = schema["pattern"]
            if pattern not in self._regex_cache:
                try:
                    self._regex_cache[pattern] = re.compile(pattern)
                except re.error as e:
                    issues.append(ValidationIssue(
                        level=ValidationLevel.ERROR,
                        message=f"Invalid regex pattern: {e}",
                        path=path,
                        constraint="pattern"
                    ))
                    return issues
            
            regex = self._regex_cache[pattern]
            if not regex.match(value):
                issues.append(ValidationIssue(
                    level=ValidationLevel.ERROR,
                    message=f"String '{value}' does not match pattern '{pattern}'",
                    path=path,
                    constraint="pattern"
                ))
        
        return issues
    
    def _validate_array_constraints(self, value: List[Any], schema: Dict[str, Any], path: str) -> List[ValidationIssue]:
        """验证数组约束
        
        Args:
            value: 要验证的数组
            schema: Schema 定义
            path: JSON 路径
            
        Returns:
            List[ValidationIssue]: 验证问题列表
        """
        issues = []
        
        # 长度验证
        if "minItems" in schema and len(value) < schema["minItems"]:
            issues.append(ValidationIssue(
                level=ValidationLevel.ERROR,
                message=f"Array length {len(value)} is less than minimum {schema['minItems']}",
                path=path,
                constraint="minItems"
            ))
        
        if "maxItems" in schema and len(value) > schema["maxItems"]:
            issues.append(ValidationIssue(
                level=ValidationLevel.WARN,
                message=f"Array length {len(value)} exceeds maximum {schema['maxItems']}",
                path=path,
                constraint="maxItems"
            ))
        
        # 唯一性验证
        if schema.get("uniqueItems", False):
            seen = set()
            duplicates = []
            for i, item in enumerate(value):
                item_str = json.dumps(item, sort_keys=True, default=str)
                if item_str in seen:
                    duplicates.append(i)
                seen.add(item_str)
            
            if duplicates:
                issues.append(ValidationIssue(
                    level=ValidationLevel.ERROR,
                    message=f"Array contains duplicate items at indices: {duplicates}",
                    path=path,
                    constraint="uniqueItems"
                ))
        
        return issues
    
    def _validate_object_constraints(self, value: Dict[str, Any], schema: Dict[str, Any], path: str) -> List[ValidationIssue]:
        """验证对象约束
        
        Args:
            value: 要验证的对象
            schema: Schema 定义
            path: JSON 路径
            
        Returns:
            List[ValidationIssue]: 验证问题列表
        """
        issues = []
        
        # 必填字段验证
        if "required" in schema:
            for required_field in schema["required"]:
                if required_field not in value:
                    issues.append(ValidationIssue(
                        level=ValidationLevel.ERROR,
                        message=f"Required field '{required_field}' is missing",
                        path=f"{path}.{required_field}" if path else required_field,
                        constraint="required"
                    ))
        
        # 属性数量验证
        if "minProperties" in schema and len(value) < schema["minProperties"]:
            issues.append(ValidationIssue(
                level=ValidationLevel.ERROR,
                message=f"Object has {len(value)} properties, minimum required: {schema['minProperties']}",
                path=path,
                constraint="minProperties"
            ))
        
        if "maxProperties" in schema and len(value) > schema["maxProperties"]:
            issues.append(ValidationIssue(
                level=ValidationLevel.WARN,
                message=f"Object has {len(value)} properties, maximum allowed: {schema['maxProperties']}",
                path=path,
                constraint="maxProperties"
            ))
        
        return issues