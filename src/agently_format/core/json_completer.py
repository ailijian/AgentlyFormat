"""JSON补全器模块

基于Agently框架的StreamingJSONCompleter优化实现，
用于智能补全不完整的JSON字符串。
"""

import json
import re
from typing import Optional, List, Tuple, Dict, Any
from enum import Enum
from dataclasses import dataclass


class CompletionStrategy(Enum):
    """补全策略枚举"""
    CONSERVATIVE = "conservative"  # 保守策略，只补全明显缺失的部分
    SMART = "smart"              # 智能策略，基于上下文推断
    AGGRESSIVE = "aggressive"     # 激进策略，尽可能补全


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
    
    def __post_init__(self):
        """初始化后处理"""
        # changes_made与completion_applied保持一致
        self.changes_made = self.completion_applied
        
        # 计算置信度
        if self.is_valid:
            if self.completion_applied:
                # 基于补全的复杂度计算置信度
                completion_ratio = (self.completed_length - self.original_length) / max(self.original_length, 1)
                self.confidence = max(0.1, 1.0 - min(completion_ratio, 0.9))
            else:
                # 原始JSON有效，置信度最高
                self.confidence = 1.0
        else:
            self.confidence = 0.0


class JSONCompleter:
    """JSON补全器
    
    智能检测和补全不完整的JSON字符串，支持多种补全策略。
    """
    
    def __init__(self, strategy: CompletionStrategy = CompletionStrategy.SMART, max_depth: int = 10):
        """初始化JSON补全器
        
        Args:
            strategy: 补全策略
            max_depth: 最大深度限制
        """
        self.strategy = strategy
        self.max_depth = max_depth
        self.completion_stats = {
            "total_completions": 0,
            "successful_completions": 0,
            "failed_completions": 0
        }
    
    def complete(self, json_str: str, strategy: Optional[CompletionStrategy] = None, max_depth: Optional[int] = None) -> CompletionResult:
        """补全JSON字符串
        
        Args:
            json_str: 待补全的JSON字符串
            strategy: 补全策略（可选，覆盖实例策略）
            max_depth: 最大深度限制（可选）
            
        Returns:
            CompletionResult: 补全结果
        """
        # 使用传入的策略或实例策略
        current_strategy = strategy if strategy is not None else self.strategy
        current_max_depth = max_depth if max_depth is not None else self.max_depth
        
        self.completion_stats["total_completions"] += 1
        
        original_length = len(json_str)
        errors = []
        completion_details = {
            "strategy": current_strategy.value,
            "max_depth": current_max_depth,
            "brackets_added": 0,
            "quotes_added": 0,
            "commas_removed": 0,
            "whitespace_cleaned": False
        }
        
        try:
            # 首先尝试解析原始JSON
            try:
                json.loads(json_str)
                # 如果已经是有效JSON，直接返回
                return CompletionResult(
                    completed_json=json_str,
                    is_valid=True,
                    completion_applied=False,
                    original_length=original_length,
                    completed_length=original_length,
                    completion_details=completion_details,
                    errors=[]
                )
            except json.JSONDecodeError:
                pass
            
            # 清理和预处理
            cleaned_json = self._preprocess_json(json_str)
            completion_details["whitespace_cleaned"] = cleaned_json != json_str
            
            # 执行补全
            completed_json = self._complete_json(cleaned_json, completion_details)
            
            # 验证补全结果
            try:
                json.loads(completed_json)
                is_valid = True
                self.completion_stats["successful_completions"] += 1
            except json.JSONDecodeError as e:
                is_valid = False
                errors.append(f"Completion validation failed: {str(e)}")
                self.completion_stats["failed_completions"] += 1
            
            return CompletionResult(
                completed_json=completed_json,
                is_valid=is_valid,
                completion_applied=completed_json != json_str,
                original_length=original_length,
                completed_length=len(completed_json),
                completion_details=completion_details,
                errors=errors
            )
            
        except Exception as e:
            self.completion_stats["failed_completions"] += 1
            errors.append(f"Completion error: {str(e)}")
            
            return CompletionResult(
                completed_json=json_str,
                is_valid=False,
                completion_applied=False,
                original_length=original_length,
                completed_length=original_length,
                completion_details=completion_details,
                errors=errors
            )
    
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
    
    def reset_stats(self):
        """重置统计信息"""
        self.completion_stats = {
            "total_completions": 0,
            "successful_completions": 0,
            "failed_completions": 0
        }


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