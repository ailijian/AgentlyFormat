"""JSON补全器模块

基于Agently框架的StreamingJSONCompleter优化实现，
用于智能补全不完整的JSON字符串。

Phase 1 优化：
- 双阶段补全器（词法→语法）
- RepairTrace 修复追踪
- 策略自适应
- 增强置信度计算
"""

import json
import re
import ast
from typing import Optional, List, Tuple, Dict, Any, Union
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import copy


class CompletionStrategy(Enum):
    """补全策略枚举"""
    CONSERVATIVE = "conservative"  # 保守策略，只补全明显缺失的部分
    SMART = "smart"              # 智能策略，基于上下文推断
    AGGRESSIVE = "aggressive"     # 激进策略，尽可能补全


class RepairSeverity(Enum):
    """修复严重程度"""
    MINOR = "minor"        # 轻微修复（空白、逗号等）
    MODERATE = "moderate"  # 中等修复（引号、括号等）
    MAJOR = "major"        # 重大修复（结构性变更）
    CRITICAL = "critical"  # 关键修复（可能改变语义）


class RepairPhase(Enum):
    """修复阶段"""
    LEXICAL = "lexical"    # 词法阶段
    SYNTACTIC = "syntactic" # 语法阶段


@dataclass
class RepairStep:
    """修复步骤"""
    phase: RepairPhase
    operation: str
    before: str
    after: str
    position: int
    severity: RepairSeverity
    confidence: float
    description: str
    applied: bool = True
    
    # 兼容字段
    before_snippet: str = ""
    after_snippet: str = ""
    rollback_reason: Optional[str] = None
    
    def __post_init__(self):
        """初始化后处理，确保字段兼容性"""
        # 兼容新字段名
        if self.before and not self.before_snippet:
            self.before_snippet = self.before
        if self.after and not self.after_snippet:
            self.after_snippet = self.after
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "phase": self.phase.value,
            "operation": self.operation,
            "before": self.before,
            "after": self.after,
            "position": self.position,
            "severity": self.severity.value,
            "confidence": self.confidence,
            "description": self.description,
            "applied": self.applied,
            "before_snippet": self.before_snippet,
            "after_snippet": self.after_snippet,
            "rollback_reason": self.rollback_reason
        }


@dataclass
class RepairTrace:
    """修复追踪记录"""
    original_text: str = ""
    target_text: str = ""
    steps: List[RepairStep] = field(default_factory=list)
    overall_severity: RepairSeverity = RepairSeverity.MINOR
    overall_confidence: float = 1.0
    lexical_changes: int = 0
    syntactic_changes: int = 0
    total_changes: int = 0
    strategy_used: CompletionStrategy = CompletionStrategy.CONSERVATIVE
    can_rollback: bool = True
    
    def add_step(self, step: RepairStep):
        """添加修复步骤"""
        self.steps.append(step)
        self.total_changes += 1
        
        if step.phase == RepairPhase.LEXICAL:
            self.lexical_changes += 1
        else:
            self.syntactic_changes += 1
        
        # 更新整体严重程度
        if step.severity.value > self.overall_severity.value:
            self.overall_severity = step.severity
        
        # 更新整体置信度（取最低值）
        self.overall_confidence = min(self.overall_confidence, step.confidence)
    
    def get_lexical_repair_ratio(self) -> float:
        """获取词法修复比例
        
        Returns:
            float: 词法修复步骤占比
        """
        if not self.steps:
            return 0.0
        lexical_steps = sum(1 for step in self.steps if step.phase == RepairPhase.LEXICAL)
        return lexical_steps / len(self.steps)
    
    def get_applied_steps_count(self) -> int:
        """获取已应用步骤数量
        
        Returns:
            int: 已应用步骤数量
        """
        return sum(1 for step in self.steps if step.applied)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "original_text": self.original_text,
            "target_text": self.target_text,
            "steps": [step.to_dict() for step in self.steps],
            "overall_severity": self.overall_severity.value,
            "overall_confidence": self.overall_confidence,
            "lexical_changes": self.lexical_changes,
            "syntactic_changes": self.syntactic_changes,
            "total_changes": self.total_changes,
            "strategy_used": self.strategy_used.value,
            "can_rollback": self.can_rollback,
            "lexical_repair_ratio": self.get_lexical_repair_ratio(),
            "applied_steps_count": self.get_applied_steps_count()
        }


@dataclass
class CompletionResult:
    """补全结果"""
    completed_json: str
    is_valid: bool
    completion_applied: bool
    original_length: int
    completed_length: int
    completion_details: Dict[str, Any]
    errors: List[str]
    changes_made: bool = False
    confidence: float = 0.0
    repair_trace: Optional[RepairTrace] = None
    strategy_used: CompletionStrategy = CompletionStrategy.CONSERVATIVE
    schema_suggestions_applied: int = 0
    historical_success_rate: float = 0.0
    
    def __post_init__(self):
        """初始化后处理"""
        # changes_made与completion_applied保持一致
        self.changes_made = self.completion_applied
        
        # 计算增强置信度
        self.confidence = self._calculate_enhanced_confidence()
    
    def _calculate_enhanced_confidence(self) -> float:
        """计算增强置信度
        
        组成包括：
        - 词法修复比例
        - AST 变更规模
        - 是否命中 schema 建议
        - 历史修复成功率
        
        Returns:
            float: 置信度 (0.0-1.0)
        """
        if not self.is_valid:
            return 0.0
        
        if not self.completion_applied:
            return 1.0  # 原始JSON有效，置信度最高
        
        confidence_factors = []
        
        # 1. 基于补全复杂度的基础置信度
        if self.original_length > 0:
            completion_ratio = (self.completed_length - self.original_length) / self.original_length
            base_confidence = max(0.1, 1.0 - min(completion_ratio, 0.9))
            confidence_factors.append(base_confidence)
        
        # 2. 基于修复追踪的置信度
        if self.repair_trace:
            # 词法修复比例（词法修复置信度更高）
            if self.repair_trace.total_changes > 0:
                lexical_ratio = self.repair_trace.lexical_changes / self.repair_trace.total_changes
                lexical_confidence = 0.7 + 0.3 * lexical_ratio  # 词法修复基础置信度0.7
                confidence_factors.append(lexical_confidence)
            
            # 整体修复置信度
            confidence_factors.append(self.repair_trace.overall_confidence)
            
            # 严重程度影响
            severity_confidence = {
                RepairSeverity.MINOR: 0.95,
                RepairSeverity.MODERATE: 0.8,
                RepairSeverity.MAJOR: 0.6,
                RepairSeverity.CRITICAL: 0.4
            }.get(self.repair_trace.overall_severity, 0.5)
            confidence_factors.append(severity_confidence)
        
        # 3. Schema 建议命中率
        if self.schema_suggestions_applied > 0:
            schema_confidence = min(1.0, 0.8 + 0.2 * self.schema_suggestions_applied / 5)
            confidence_factors.append(schema_confidence)
        
        # 4. 历史成功率
        if self.historical_success_rate > 0:
            confidence_factors.append(self.historical_success_rate)
        
        # 计算加权平均置信度
        if confidence_factors:
            return sum(confidence_factors) / len(confidence_factors)
        else:
            return 0.5  # 默认中等置信度
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "completed_json": self.completed_json,
            "is_valid": self.is_valid,
            "completion_applied": self.completion_applied,
            "original_length": self.original_length,
            "completed_length": self.completed_length,
            "completion_details": self.completion_details,
            "errors": self.errors,
            "changes_made": self.changes_made,
            "confidence": self.confidence,
            "repair_trace": self.repair_trace.to_dict() if self.repair_trace else None,
            "strategy_used": self.strategy_used.value,
            "schema_suggestions_applied": self.schema_suggestions_applied,
            "historical_success_rate": self.historical_success_rate
        }


@dataclass
class StrategyHistory:
    """策略历史记录"""
    strategy: CompletionStrategy
    success_count: int = 0
    failure_count: int = 0
    total_attempts: int = 0
    last_used: Optional[datetime] = None
    avg_confidence: float = 0.0
    failure_types: Dict[str, int] = field(default_factory=dict)
    
    @property
    def success_rate(self) -> float:
        """成功率"""
        return self.success_count / max(self.total_attempts, 1)
    
    def record_attempt(self, success: bool, confidence: float = 0.0, failure_type: str = None):
        """记录尝试结果"""
        self.total_attempts += 1
        self.last_used = datetime.now()
        
        if success:
            self.success_count += 1
            # 更新平均置信度
            self.avg_confidence = (self.avg_confidence * (self.success_count - 1) + confidence) / self.success_count
        else:
            self.failure_count += 1
            if failure_type:
                self.failure_types[failure_type] = self.failure_types.get(failure_type, 0) + 1


class JSONCompleter:
    """JSON补全器
    
    智能检测和补全不完整的JSON字符串，支持多种补全策略。
    
    Phase 1 优化特性：
    - 双阶段补全（词法→语法）
    - RepairTrace 修复追踪
    - 策略自适应
    - 增强置信度计算
    """
    
    def __init__(self, strategy: CompletionStrategy = CompletionStrategy.SMART, max_depth: int = 10):
        """初始化JSON补全器
        
        Args:
            strategy: 补全策略
            max_depth: 最大深度限制
        """
        self.strategy = strategy
        self.max_depth = max_depth
        
        # 基础统计
        self.completion_stats = {
            "total_completions": 0,
            "successful_completions": 0,
            "failed_completions": 0,
            "lexical_repairs": 0,
            "syntactic_repairs": 0,
            "strategy_switches": 0
        }
        
        # 策略历史记录
        self.strategy_history = {
            strategy: StrategyHistory(strategy) for strategy in CompletionStrategy
        }
        
        # 自适应配置
        self.adaptive_enabled = True
        self.confidence_threshold = 0.7  # 低于此阈值考虑切换策略
        self.failure_threshold = 3  # 连续失败次数阈值
        self.recent_failures = 0
        self.last_strategy_switch = None
        self.min_switch_interval = timedelta(minutes=1)  # 最小策略切换间隔
    
    def complete(self, json_str: str, strategy: Optional[CompletionStrategy] = None, max_depth: Optional[int] = None) -> CompletionResult:
        """补全JSON字符串
        
        Args:
            json_str: 待补全的JSON字符串
            strategy: 补全策略（可选，覆盖实例策略）
            max_depth: 最大深度限制（可选）
            
        Returns:
            CompletionResult: 补全结果
        """
        # 策略自适应选择
        current_strategy = self._select_adaptive_strategy(strategy)
        current_max_depth = max_depth if max_depth is not None else self.max_depth
        
        self.completion_stats["total_completions"] += 1
        
        original_length = len(json_str)
        
        # 初始化修复追踪
        repair_trace = RepairTrace()
        repair_trace.strategy_used = current_strategy
        
        try:
            # 首先尝试解析原始JSON
            try:
                json.loads(json_str)
                # 如果已经是有效JSON，直接返回
                result = CompletionResult(
                    completed_json=json_str,
                    is_valid=True,
                    completion_applied=False,
                    original_length=original_length,
                    completed_length=original_length,
                    completion_details={"strategy": current_strategy.value},
                    errors=[],
                    repair_trace=repair_trace,
                    strategy_used=current_strategy
                )
                self._record_strategy_result(current_strategy, True, result.confidence)
                return result
            except json.JSONDecodeError:
                pass
            
            # Phase 1: 词法阶段修复
            lexical_result = self._lexical_repair_phase(json_str, repair_trace)
            
            # Phase 2: 语法阶段修复
            syntactic_result = self._syntactic_repair_phase(lexical_result, repair_trace, current_strategy, current_max_depth)
            
            # 验证补全结果
            is_valid, validation_error = self._validate_json(syntactic_result)
            
            # 更新修复追踪
            repair_trace.target_text = syntactic_result
            repair_trace.overall_confidence = self._calculate_repair_confidence(repair_trace)
            
            if is_valid:
                self.completion_stats["successful_completions"] += 1
                self.recent_failures = 0
            else:
                self.completion_stats["failed_completions"] += 1
                self.recent_failures += 1
                
                # 记录失败步骤
                failure_step = RepairStep(
                    phase=RepairPhase.SYNTACTIC,
                    operation="validation",
                    before=syntactic_result[:50],
                    after="",
                    position=-1,
                    severity=RepairSeverity.CRITICAL,
                    confidence=0.0,
                    description=f"JSON validation failed: {validation_error}",
                    applied=False
                )
                repair_trace.add_step(failure_step)
            
            # 创建结果
            result = CompletionResult(
                completed_json=syntactic_result,
                is_valid=is_valid,
                completion_applied=syntactic_result != json_str,
                original_length=original_length,
                completed_length=len(syntactic_result),
                completion_details={"strategy": current_strategy.value},
                errors=[] if is_valid else [f"Validation failed"],
                repair_trace=repair_trace,
                strategy_used=current_strategy
            )
            
            # 记录策略使用结果
            self._record_strategy_result(current_strategy, is_valid, result.confidence)
            
            return result
            
        except Exception as e:
            self.completion_stats["failed_completions"] += 1
            self.recent_failures += 1
            
            # 记录异常步骤
            error_step = RepairStep(
                phase=RepairPhase.LEXICAL,
                operation="exception",
                before=json_str[:50],
                after="",
                position=-1,
                severity=RepairSeverity.CRITICAL,
                confidence=0.0,
                description=f"Completion error: {str(e)}",
                applied=False
            )
            repair_trace.add_step(error_step)
            
            result = CompletionResult(
                completed_json=json_str,
                is_valid=False,
                completion_applied=False,
                original_length=original_length,
                completed_length=original_length,
                completion_details={"strategy": current_strategy.value},
                errors=[f"Completion error: {str(e)}"],
                repair_trace=repair_trace,
                strategy_used=current_strategy
            )
            
            # 记录策略失败
            self._record_strategy_result(current_strategy, False, 0.0, str(e))
            
            return result
    
    def _preprocess_json(self, json_str: str) -> str:
        """预处理JSON字符串
        
        Args:
            json_str: 原始JSON字符串
            
        Returns:
            str: 清理后的JSON字符串
        """
        # 移除前后空白
        cleaned = json_str.strip()
        
        # 移除可能的注释（简单处理）
        lines = cleaned.split('\n')
        cleaned_lines = []
        for line in lines:
            # 移除行注释
            if '//' in line:
                line = line[:line.index('//')]
            cleaned_lines.append(line)
        
        cleaned = '\n'.join(cleaned_lines)
        
        # 移除多余的空白字符
        cleaned = re.sub(r'\s+', ' ', cleaned)
        cleaned = re.sub(r'\s*([{}\[\],:])', r'\1', cleaned)
        cleaned = re.sub(r'([{}\[\],:])\s*', r'\1', cleaned)
        
        return cleaned.strip()
    
    def _complete_json(self, json_str: str, completion_details: Dict[str, Any]) -> str:
        """执行JSON补全
        
        Args:
            json_str: 待补全的JSON字符串
            completion_details: 补全详情记录
            
        Returns:
            str: 补全后的JSON字符串
        """
        if not json_str:
            return "{}"
        
        # 使用栈来跟踪括号状态
        stack = []
        in_string = False
        escape_next = False
        result = []
        
        i = 0
        while i < len(json_str):
            char = json_str[i]
            
            if escape_next:
                result.append(char)
                escape_next = False
                i += 1
                continue
            
            if char == '\\' and in_string:
                escape_next = True
                result.append(char)
                i += 1
                continue
            
            if char == '"' and not escape_next:
                in_string = not in_string
                result.append(char)
                i += 1
                continue
            
            if in_string:
                result.append(char)
                i += 1
                continue
            
            # 处理括号
            if char in '{[':
                stack.append(char)
                result.append(char)
            elif char in '}]':
                if stack:
                    expected = '}' if stack[-1] == '{' else ']'
                    if char == expected:
                        stack.pop()
                    result.append(char)
                else:
                    # 多余的闭合括号，根据策略处理
                    if self.strategy != CompletionStrategy.AGGRESSIVE:
                        result.append(char)
            else:
                result.append(char)
            
            i += 1
        
        # 处理未闭合的字符串
        if in_string:
            result.append('"')
            completion_details["quotes_added"] += 1
        
        # 处理未闭合的括号
        while stack:
            bracket = stack.pop()
            if bracket == '{':
                result.append('}')
                completion_details["brackets_added"] += 1
            elif bracket == '[':
                result.append(']')
                completion_details["brackets_added"] += 1
        
        completed = ''.join(result)
        
        # 后处理：修复常见问题
        completed = self._post_process_json(completed, completion_details)
        
        return completed
    
    def _post_process_json(self, json_str: str, completion_details: Dict[str, Any]) -> str:
        """后处理JSON字符串
        
        Args:
            json_str: 待后处理的JSON字符串
            completion_details: 补全详情记录
            
        Returns:
            str: 后处理后的JSON字符串
        """
        # 移除多余的逗号
        # 处理对象中的尾随逗号
        json_str = re.sub(r',\s*}', '}', json_str)
        # 处理数组中的尾随逗号
        json_str = re.sub(r',\s*]', ']', json_str)
        
        # 计算移除的逗号数量
        original_commas = json_str.count(',')
        
        # 修复缺失的逗号（简单启发式）
        if self.strategy in [CompletionStrategy.SMART, CompletionStrategy.AGGRESSIVE]:
            json_str = self._fix_missing_commas(json_str)
        
        completion_details["commas_removed"] = original_commas - json_str.count(',')
        
        # 修复缺失的引号
        if self.strategy == CompletionStrategy.AGGRESSIVE:
            json_str = self._fix_missing_quotes(json_str)
        
        return json_str
    
    def _fix_missing_commas(self, json_str: str) -> str:
        """修复缺失的逗号
        
        Args:
            json_str: JSON字符串
            
        Returns:
            str: 修复后的JSON字符串
        """
        # 在对象属性之间添加逗号
        # 匹配 "key":value "key2" 模式
        json_str = re.sub(
            r'("[^"]*"\s*:\s*(?:"[^"]*"|[^,}\]]+))\s+("[^"]*"\s*:)',
            r'\1,\2',
            json_str
        )
        
        # 在数组元素之间添加逗号
        # 匹配 value value 模式
        json_str = re.sub(
            r'((?:"[^"]*"|[^,\]\s]+))\s+((?:"[^"]*"|[^,\]\s]+))',
            r'\1,\2',
            json_str
        )
        
        return json_str
    
    def _fix_missing_quotes(self, json_str: str) -> str:
        """修复缺失的引号
        
        Args:
            json_str: JSON字符串
            
        Returns:
            str: 修复后的JSON字符串
        """
        # 为对象键添加引号
        json_str = re.sub(
            r'([{,]\s*)([a-zA-Z_][a-zA-Z0-9_]*)\s*:',
            r'\1"\2":',
            json_str
        )
        
        return json_str
    
    def is_likely_incomplete(self, json_str: str) -> Tuple[bool, List[str]]:
        """检测JSON字符串是否可能不完整
        
        Args:
            json_str: JSON字符串
            
        Returns:
            Tuple[bool, List[str]]: (是否不完整, 不完整的原因列表)
        """
        reasons = []
        
        if not json_str.strip():
            reasons.append("Empty string")
            return True, reasons
        
        # 检查括号平衡
        bracket_stack = []
        in_string = False
        escape_next = False
        
        for char in json_str:
            if escape_next:
                escape_next = False
                continue
            
            if char == '\\' and in_string:
                escape_next = True
                continue
            
            if char == '"' and not escape_next:
                in_string = not in_string
                continue
            
            if in_string:
                continue
            
            if char in '{[':
                bracket_stack.append(char)
            elif char in '}]':
                if not bracket_stack:
                    reasons.append(f"Unmatched closing bracket: {char}")
                else:
                    expected = '}' if bracket_stack[-1] == '{' else ']'
                    if char == expected:
                        bracket_stack.pop()
                    else:
                        reasons.append(f"Mismatched bracket: expected {expected}, got {char}")
        
        if in_string:
            reasons.append("Unclosed string")
        
        if bracket_stack:
            reasons.append(f"Unclosed brackets: {bracket_stack}")
        
        # 检查是否以不完整的方式结束
        stripped = json_str.strip()
        if stripped.endswith(','):
            reasons.append("Ends with comma")
        elif stripped.endswith(':'):
            reasons.append("Ends with colon")
        
        return len(reasons) > 0, reasons
    
    def get_completion_stats(self) -> Dict[str, Any]:
        """获取补全统计信息
        
        Returns:
            Dict[str, Any]: 统计信息
        """
        total = self.completion_stats["total_completions"]
        success_rate = (
            self.completion_stats["successful_completions"] / total * 100
            if total > 0 else 0
        )
        
        return {
            **self.completion_stats,
            "success_rate": round(success_rate, 2)
        }
    
    def _select_adaptive_strategy(self, requested_strategy: Optional[CompletionStrategy]) -> CompletionStrategy:
        """自适应策略选择
        
        Args:
            requested_strategy: 请求的策略
            
        Returns:
            CompletionStrategy: 选择的策略
        """
        if requested_strategy is not None:
            return requested_strategy
        
        if not self.adaptive_enabled:
            return self.strategy
        
        # 检查是否需要切换策略
        if self.recent_failures >= self.failure_threshold:
            # 连续失败，尝试切换策略
            current_time = datetime.now()
            if (self.last_strategy_switch is None or 
                current_time - self.last_strategy_switch >= self.min_switch_interval):
                
                # 选择成功率最高的策略
                best_strategy = max(
                    self.strategy_history.values(),
                    key=lambda h: h.success_rate if h.total_attempts > 0 else 0
                ).strategy
                
                if best_strategy != self.strategy:
                    self.strategy = best_strategy
                    self.last_strategy_switch = current_time
                    self.completion_stats["strategy_switches"] += 1
                    self.recent_failures = 0
        
        return self.strategy
    
    def _record_strategy_result(self, strategy: CompletionStrategy, success: bool, confidence: float, failure_type: str = None):
        """记录策略使用结果
        
        Args:
            strategy: 使用的策略
            success: 是否成功
            confidence: 置信度
            failure_type: 失败类型
        """
        self.strategy_history[strategy].record_attempt(success, confidence, failure_type)
    
    def _lexical_repair_phase(self, json_str: str, repair_trace: RepairTrace) -> str:
        """词法阶段修复
        
        Args:
            json_str: 输入JSON字符串
            repair_trace: 修复追踪
            
        Returns:
            str: 词法修复后的JSON字符串
        """
        result = json_str
        
        # 清理空白字符
        cleaned = self._preprocess_json(result)
        if cleaned != result:
            step = RepairStep(
                phase=RepairPhase.LEXICAL,
                operation="whitespace_cleanup",
                before=result[:50],
                after=cleaned[:50],
                position=0,
                severity=RepairSeverity.MINOR,
                confidence=0.95,
                description="清理多余空白字符"
            )
            repair_trace.add_step(step)
            result = cleaned
            self.completion_stats["lexical_repairs"] += 1
        
        return result
    
    def _syntactic_repair_phase(self, json_str: str, repair_trace: RepairTrace, strategy: CompletionStrategy, max_depth: int) -> str:
        """语法阶段修复
        
        Args:
            json_str: 词法修复后的JSON字符串
            repair_trace: 修复追踪
            strategy: 补全策略
            max_depth: 最大深度
            
        Returns:
            str: 语法修复后的JSON字符串
        """
        completion_details = {
            "brackets_added": 0,
            "quotes_added": 0,
            "commas_removed": 0
        }
        
        result = self._complete_json(json_str, completion_details)
        
        # 记录语法修复步骤
        if result != json_str:
            step = RepairStep(
                phase=RepairPhase.SYNTACTIC,
                operation="structure_completion",
                before=json_str[:50],
                after=result[:50],
                position=0,
                severity=RepairSeverity.MODERATE,
                confidence=0.8,
                description=f"结构补全: 添加{completion_details['brackets_added']}个括号, {completion_details['quotes_added']}个引号"
            )
            repair_trace.add_step(step)
            self.completion_stats["syntactic_repairs"] += 1
        
        return result
     
    def _validate_json(self, json_str: str) -> Tuple[bool, Optional[str]]:
        """验证JSON字符串
        
        Args:
            json_str: JSON字符串
            
        Returns:
            Tuple[bool, Optional[str]]: (是否有效, 错误信息)
        """
        try:
            json.loads(json_str)
            return True, None
        except json.JSONDecodeError as e:
            return False, str(e)
        except Exception as e:
            return False, f"Unexpected error: {str(e)}"
    
    def _calculate_repair_confidence(self, repair_trace: RepairTrace) -> float:
        """计算修复置信度
        
        Args:
            repair_trace: 修复追踪
            
        Returns:
            float: 修复置信度
        """
        if not repair_trace.steps:
            return 1.0
        
        # 基于步骤置信度和严重程度计算总体置信度
        total_confidence = 0.0
        severity_penalty = {
            RepairSeverity.MINOR: 0.05,
            RepairSeverity.MODERATE: 0.15,
            RepairSeverity.MAJOR: 0.3,
            RepairSeverity.CRITICAL: 0.5
        }
        
        applied_steps = [step for step in repair_trace.steps if step.applied]
        if not applied_steps:
            return 1.0
        
        for step in applied_steps:
            step_confidence = step.confidence
            penalty = severity_penalty.get(step.severity, 0.2)
            total_confidence += step_confidence * (1 - penalty)
        
        return min(total_confidence / len(applied_steps), 1.0)
    
    def _get_historical_success_rate(self, strategy: CompletionStrategy) -> float:
        """获取策略历史成功率
        
        Args:
            strategy: 策略
            
        Returns:
            float: 历史成功率
        """
        return self.strategy_history[strategy].success_rate
    
    def reset_stats(self):
        """重置统计信息"""
        self.completion_stats = {
            "total_completions": 0,
            "successful_completions": 0,
            "failed_completions": 0,
            "lexical_repairs": 0,
            "syntactic_repairs": 0,
            "strategy_switches": 0
        }
        
        # 重置策略历史
        for history in self.strategy_history.values():
            history.success_count = 0
            history.failure_count = 0
            history.total_attempts = 0
            history.last_used = None
            history.avg_confidence = 0.0
            history.failure_types.clear()
        
        self.recent_failures = 0
        self.last_strategy_switch = None


# 便捷函数
def complete_json(
    json_str: str,
    strategy: CompletionStrategy = CompletionStrategy.SMART
) -> CompletionResult:
    """补全JSON字符串的便捷函数
    
    Args:
        json_str: 待补全的JSON字符串
        strategy: 补全策略
        
    Returns:
        CompletionResult: 补全结果
    """
    completer = JSONCompleter(strategy)
    return completer.complete(json_str)


def is_json_incomplete(json_str: str) -> bool:
    """检查JSON是否不完整的便捷函数
    
    Args:
        json_str: JSON字符串
        
    Returns:
        bool: 是否不完整
    """
    completer = JSONCompleter()
    is_incomplete, _ = completer.is_likely_incomplete(json_str)
    return is_incomplete