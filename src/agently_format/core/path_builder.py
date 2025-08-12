"""数据路径构建器模块

基于Agently框架的DataPathBuilder优化实现，
用于构建和管理JSON数据的访问路径。
"""

import re
from typing import Any, Dict, List, Optional, Union, Tuple
from enum import Enum
from dataclasses import dataclass


class PathStyle(Enum):
    """路径风格枚举"""
    DOT = "dot"          # user.profile.name
    SLASH = "slash"      # user/profile/name
    BRACKET = "bracket"  # user[profile][name]
    MIXED = "mixed"      # user.profile[0].name


@dataclass
class PathSegment:
    """路径段"""
    key: str
    is_array_index: bool = False
    array_index: Optional[int] = None
    is_wildcard: bool = False
    
    def __str__(self) -> str:
        if self.is_array_index and self.array_index is not None:
            return f"[{self.array_index}]"
        elif self.is_wildcard:
            return "[*]"
        else:
            return self.key


@dataclass
class ParsedPath:
    """解析后的路径"""
    segments: List[PathSegment]
    original_path: str
    style: PathStyle
    is_valid: bool = True
    errors: List[str] = None
    
    def __post_init__(self):
        if self.errors is None:
            self.errors = []
    
    def to_dot_notation(self) -> str:
        """转换为点号表示法"""
        parts = []
        for segment in self.segments:
            if segment.is_array_index:
                if segment.array_index is not None:
                    parts.append(f"[{segment.array_index}]")
                else:
                    parts.append("[*]")
            else:
                if parts:  # 不是第一个元素
                    parts.append(f".{segment.key}")
                else:
                    parts.append(segment.key)
        return "".join(parts)
    
    def to_slash_notation(self) -> str:
        """转换为斜杠表示法"""
        parts = []
        for segment in self.segments:
            if segment.is_array_index:
                if segment.array_index is not None:
                    parts.append(f"[{segment.array_index}]")
                else:
                    parts.append("[*]")
            else:
                parts.append(segment.key)
        return "/".join(parts)
    
    def to_bracket_notation(self) -> str:
        """转换为括号表示法"""
        if not self.segments:
            return ""
        
        result = self.segments[0].key
        for segment in self.segments[1:]:
            if segment.is_array_index:
                if segment.array_index is not None:
                    result += f"[{segment.array_index}]"
                else:
                    result += "[*]"
            else:
                result += f"['{segment.key}']"
        return result


class PathBuilder:
    """数据路径构建器
    
    提供多种路径风格的构建、解析和转换功能。
    """
    
    def __init__(self, default_style: PathStyle = PathStyle.MIXED):
        """初始化路径构建器
        
        Args:
            default_style: 默认路径风格
        """
        self.default_style = default_style
        self.path_cache = {}  # 路径解析缓存
    
    def build_path(self, *segments: Union[str, int], style: Optional[PathStyle] = None) -> str:
        """构建路径
        
        Args:
            *segments: 路径段
            style: 路径风格，默认使用初始化时设置的风格
            
        Returns:
            str: 构建的路径字符串
        """
        if not segments:
            return ""
        
        target_style = style or self.default_style
        path_segments = []
        
        for segment in segments:
            if isinstance(segment, int):
                path_segments.append(PathSegment(
                    key=str(segment),
                    is_array_index=True,
                    array_index=segment
                ))
            elif isinstance(segment, str):
                if segment == "*":
                    path_segments.append(PathSegment(
                        key="*",
                        is_array_index=True,
                        is_wildcard=True
                    ))
                else:
                    path_segments.append(PathSegment(key=segment))
            else:
                raise ValueError(f"Invalid segment type: {type(segment)}")
        
        parsed_path = ParsedPath(
            segments=path_segments,
            original_path="",
            style=target_style
        )
        
        if target_style == PathStyle.DOT:
            return parsed_path.to_dot_notation()
        elif target_style == PathStyle.SLASH:
            return parsed_path.to_slash_notation()
        elif target_style == PathStyle.BRACKET:
            return parsed_path.to_bracket_notation()
        else:
            return parsed_path.to_dot_notation()  # 默认使用点号
    
    def parse_path(self, path: str) -> ParsedPath:
        """解析路径字符串
        
        Args:
            path: 路径字符串
            
        Returns:
            ParsedPath: 解析结果
        """
        # 检查缓存
        if path in self.path_cache:
            return self.path_cache[path]
        
        if not path:
            result = ParsedPath(
                segments=[],
                original_path=path,
                style=self.default_style,
                is_valid=True
            )
            self.path_cache[path] = result
            return result
        
        # 检测路径风格
        style = self._detect_path_style(path)
        
        try:
            if style == PathStyle.DOT:
                segments = self._parse_dot_path(path)
            elif style == PathStyle.SLASH:
                segments = self._parse_slash_path(path)
            elif style == PathStyle.BRACKET:
                segments = self._parse_bracket_path(path)
            else:  # MIXED
                segments = self._parse_mixed_path(path)
            
            result = ParsedPath(
                segments=segments,
                original_path=path,
                style=style,
                is_valid=True
            )
            
        except Exception as e:
            result = ParsedPath(
                segments=[],
                original_path=path,
                style=style,
                is_valid=False,
                errors=[str(e)]
            )
        
        self.path_cache[path] = result
        return result
    
    def build_paths(self, data: Any, include_arrays: bool = True, max_depth: Optional[int] = None, style: Optional[PathStyle] = None) -> List[str]:
        """从数据结构构建所有可能的路径
        
        Args:
            data: 数据结构
            include_arrays: 是否包含数组索引路径
            max_depth: 最大深度限制
            style: 路径风格
            
        Returns:
            List[str]: 路径列表
        """
        paths = []
        target_style = style or self.default_style
        self._build_paths_recursive(data, [], paths, include_arrays, max_depth or 10, 0, target_style)
        return paths
    
    def _build_paths_recursive(self, data: Any, current_path: List[str], paths: List[str], 
                              include_arrays: bool, max_depth: int, current_depth: int, style: PathStyle):
        """递归构建路径"""
        if current_depth >= max_depth:
            return
            
        if isinstance(data, dict):
            for key, value in data.items():
                new_path = current_path + [key]
                path_str = self._format_path(new_path, style)
                paths.append(path_str)
                
                if isinstance(value, (dict, list)):
                    self._build_paths_recursive(value, new_path, paths, include_arrays, max_depth, current_depth + 1, style)
                    
        elif isinstance(data, list) and include_arrays:
            for i, item in enumerate(data):
                # 为数组索引创建路径
                if current_path:
                    # 有父路径，添加数组索引
                    if style == PathStyle.DOT:
                        path_str = ".".join(current_path) + f"[{i}]"
                    elif style == PathStyle.SLASH:
                        path_str = "/".join(current_path) + f"[{i}]"
                    elif style == PathStyle.BRACKET:
                        path_str = current_path[0]
                        for part in current_path[1:]:
                            path_str += f"['{part}']"
                        path_str += f"[{i}]"
                    elif style == PathStyle.MIXED:
                        path_str = ".".join(current_path) + f"[{i}]"
                    else:
                        path_str = ".".join(current_path) + f"[{i}]"
                else:
                    # 根级数组
                    if style == PathStyle.DOT:
                        path_str = str(i)
                    elif style == PathStyle.SLASH:
                        path_str = str(i)
                    elif style == PathStyle.BRACKET:
                        path_str = f"[{i}]"
                    elif style == PathStyle.MIXED:
                        path_str = f"[{i}]"
                    else:
                        path_str = f"[{i}]"
                
                paths.append(path_str)
                
                # 递归处理数组元素，传递包含数组索引的路径
                if isinstance(item, (dict, list)):
                    # 创建新的路径，包含数组索引
                    if style == PathStyle.DOT:
                        # 对于DOT风格，数组索引使用方括号附加到最后一个路径段
                        if current_path:
                            new_array_path = current_path[:-1] + [current_path[-1] + f"[{i}]"]
                        else:
                            new_array_path = [f"[{i}]"]
                    elif style == PathStyle.SLASH:
                        # 对于SLASH风格，数组索引使用方括号附加到最后一个路径段
                        if current_path:
                            new_array_path = current_path[:-1] + [current_path[-1] + f"[{i}]"]
                        else:
                            new_array_path = [f"[{i}]"]
                    elif style == PathStyle.BRACKET:
                        new_array_path = current_path + [f"[{i}]"]
                    elif style == PathStyle.MIXED:
                        # 对于MIXED风格，数组索引使用方括号附加到最后一个路径段
                        if current_path:
                            new_array_path = current_path[:-1] + [current_path[-1] + f"[{i}]"]
                        else:
                            new_array_path = [f"[{i}]"]
                    else:
                        # 默认使用MIXED风格的逻辑
                        if current_path:
                            new_array_path = current_path[:-1] + [current_path[-1] + f"[{i}]"]
                        else:
                            new_array_path = [f"[{i}]"]
                    self._build_paths_recursive(item, new_array_path, paths, include_arrays, max_depth, current_depth + 1, style)
    
    def _format_path(self, path_parts: List[str], style: PathStyle, is_array_index: bool = False) -> str:
        """格式化路径
        
        Args:
            path_parts: 路径部分列表
            style: 路径风格
            is_array_index: 最后一个部分是否为数组索引
            
        Returns:
            str: 格式化后的路径
        """
        if not path_parts:
            return ""
        
        # 处理包含数组索引的路径部分
        result_parts = []
        for part in path_parts:
            if part.startswith('[') and part.endswith(']'):
                # 这是一个数组索引部分，直接添加
                if result_parts:
                    if style == PathStyle.DOT:
                        result_parts[-1] += part
                    elif style == PathStyle.SLASH:
                        result_parts[-1] += part
                    elif style == PathStyle.BRACKET:
                        result_parts[-1] += part
                    else:
                        result_parts[-1] += part
                else:
                    result_parts.append(part)
            else:
                result_parts.append(part)
        
        if style == PathStyle.SLASH:
            return "/".join(result_parts)
        elif style == PathStyle.BRACKET:
            if not result_parts:
                return ""
            result = result_parts[0]
            for part in result_parts[1:]:
                if part.startswith('[') and part.endswith(']'):
                    result += part
                else:
                    result += f"['{part}']"
            return result
        elif style == PathStyle.MIXED:
            return ".".join(result_parts)
        else:  # DOT style
            return ".".join(result_parts)
    
    def get_value_by_path(self, data: Any, path: str) -> Any:
        """根据路径获取值
        
        Args:
            data: 数据结构
            path: 路径字符串
            
        Returns:
            Any: 路径对应的值，如果路径不存在返回None
        """
        success, value = self.get_value_at_path(data, path)
        return value if success else None
    
    def validate_path(self, data: Any, path: str) -> bool:
        """验证路径是否存在
        
        Args:
            data: 数据结构
            path: 路径字符串
            
        Returns:
            bool: 路径是否有效
        """
        success, _ = self.get_value_at_path(data, path)
        return success
    
    def _detect_path_style(self, path: str) -> PathStyle:
        """检测路径风格
        
        Args:
            path: 路径字符串
            
        Returns:
            PathStyle: 检测到的路径风格
        """
        has_dots = '.' in path
        has_slashes = '/' in path
        has_brackets = '[' in path and ']' in path
        
        if has_brackets and (has_dots or has_slashes):
            return PathStyle.MIXED
        elif has_brackets:
            return PathStyle.BRACKET
        elif has_slashes:
            return PathStyle.SLASH
        elif has_dots:
            return PathStyle.DOT
        else:
            # 单个键，默认为点号风格
            return PathStyle.DOT
    
    def _parse_dot_path(self, path: str) -> List[PathSegment]:
        """解析点号路径
        
        Args:
            path: 点号路径字符串
            
        Returns:
            List[PathSegment]: 路径段列表
        """
        segments = []
        
        # 处理数组索引
        parts = re.split(r'(\[[^\]]*\])', path)
        
        for part in parts:
            if not part:
                continue
            
            if part.startswith('[') and part.endswith(']'):
                # 数组索引
                index_str = part[1:-1]
                if index_str == '*':
                    segments.append(PathSegment(
                        key="*",
                        is_array_index=True,
                        is_wildcard=True
                    ))
                else:
                    try:
                        index = int(index_str)
                        segments.append(PathSegment(
                            key=index_str,
                            is_array_index=True,
                            array_index=index
                        ))
                    except ValueError:
                        raise ValueError(f"Invalid array index: {index_str}")
            else:
                # 普通键，按点号分割
                keys = part.split('.')
                for key in keys:
                    if key:  # 忽略空字符串
                        segments.append(PathSegment(key=key))
        
        return segments
    
    def _parse_slash_path(self, path: str) -> List[PathSegment]:
        """解析斜杠路径
        
        Args:
            path: 斜杠路径字符串
            
        Returns:
            List[PathSegment]: 路径段列表
        """
        segments = []
        
        # 处理数组索引
        parts = re.split(r'(\[[^\]]*\])', path)
        
        for part in parts:
            if not part:
                continue
            
            if part.startswith('[') and part.endswith(']'):
                # 数组索引
                index_str = part[1:-1]
                if index_str == '*':
                    segments.append(PathSegment(
                        key="*",
                        is_array_index=True,
                        is_wildcard=True
                    ))
                else:
                    try:
                        index = int(index_str)
                        segments.append(PathSegment(
                            key=index_str,
                            is_array_index=True,
                            array_index=index
                        ))
                    except ValueError:
                        raise ValueError(f"Invalid array index: {index_str}")
            else:
                # 普通键，按斜杠分割
                keys = part.split('/')
                for key in keys:
                    if key:  # 忽略空字符串
                        segments.append(PathSegment(key=key))
        
        return segments
    
    def _parse_bracket_path(self, path: str) -> List[PathSegment]:
        """解析括号路径
        
        Args:
            path: 括号路径字符串
            
        Returns:
            List[PathSegment]: 路径段列表
        """
        segments = []
        
        # 使用正则表达式解析
        # 匹配 key['subkey'][0] 格式
        pattern = r"([a-zA-Z_][a-zA-Z0-9_]*)|\[([^\]]+)\]"
        matches = re.findall(pattern, path)
        
        for match in matches:
            key, bracket_content = match
            
            if key:
                # 普通键
                segments.append(PathSegment(key=key))
            elif bracket_content:
                # 括号内容
                if bracket_content == '*':
                    segments.append(PathSegment(
                        key="*",
                        is_array_index=True,
                        is_wildcard=True
                    ))
                elif bracket_content.isdigit():
                    # 数组索引
                    index = int(bracket_content)
                    segments.append(PathSegment(
                        key=bracket_content,
                        is_array_index=True,
                        array_index=index
                    ))
                elif (bracket_content.startswith("'") and bracket_content.endswith("'")) or \
                     (bracket_content.startswith('"') and bracket_content.endswith('"')):
                    # 字符串键
                    key = bracket_content[1:-1]
                    segments.append(PathSegment(key=key))
                else:
                    # 无引号的键
                    segments.append(PathSegment(key=bracket_content))
        
        return segments
    
    def _parse_mixed_path(self, path: str) -> List[PathSegment]:
        """解析混合风格路径
        
        Args:
            path: 混合风格路径字符串
            
        Returns:
            List[PathSegment]: 路径段列表
        """
        segments = []
        
        # 复杂的正则表达式来处理混合风格
        # 匹配: key, key.subkey, key[0], key['subkey'], etc.
        pattern = r"([a-zA-Z_][a-zA-Z0-9_]*(?:\.[a-zA-Z_][a-zA-Z0-9_]*)*)|\[([^\]]+)\]"
        
        i = 0
        while i < len(path):
            match = re.match(pattern, path[i:])
            if match:
                key_part, bracket_content = match.groups()
                
                if key_part:
                    # 处理点号分隔的键
                    keys = key_part.split('.')
                    for key in keys:
                        if key:
                            segments.append(PathSegment(key=key))
                elif bracket_content:
                    # 处理括号内容
                    if bracket_content == '*':
                        segments.append(PathSegment(
                            key="*",
                            is_array_index=True,
                            is_wildcard=True
                        ))
                    elif bracket_content.isdigit():
                        index = int(bracket_content)
                        segments.append(PathSegment(
                            key=bracket_content,
                            is_array_index=True,
                            array_index=index
                        ))
                    elif (bracket_content.startswith("'") and bracket_content.endswith("'")) or \
                         (bracket_content.startswith('"') and bracket_content.endswith('"')):
                        key = bracket_content[1:-1]
                        segments.append(PathSegment(key=key))
                    else:
                        segments.append(PathSegment(key=bracket_content))
                
                i += match.end()
            else:
                # 跳过无法匹配的字符
                i += 1
        
        return segments
    
    def convert_path(self, path: str, target_style: PathStyle) -> str:
        """转换路径风格
        
        Args:
            path: 原始路径
            target_style: 目标风格
            
        Returns:
            str: 转换后的路径
        """
        parsed = self.parse_path(path)
        
        if not parsed.is_valid:
            raise ValueError(f"Invalid path: {path}")
        
        if target_style == PathStyle.DOT:
            return parsed.to_dot_notation()
        elif target_style == PathStyle.SLASH:
            return parsed.to_slash_notation()
        elif target_style == PathStyle.BRACKET:
            return parsed.to_bracket_notation()
        else:
            return parsed.to_dot_notation()
    
    def extract_parsing_key_orders(self, data: Dict[str, Any]) -> List[str]:
        """从字典中提取解析键顺序
        
        Args:
            data: 字典数据
            
        Returns:
            List[str]: 键顺序列表
        """
        def extract_keys(obj: Any, prefix: str = "") -> List[str]:
            keys = []
            
            if isinstance(obj, dict):
                for key, value in obj.items():
                    current_path = f"{prefix}.{key}" if prefix else key
                    keys.append(current_path)
                    
                    # 递归处理嵌套对象
                    if isinstance(value, (dict, list)):
                        keys.extend(extract_keys(value, current_path))
            
            elif isinstance(obj, list):
                for i, item in enumerate(obj):
                    current_path = f"{prefix}[{i}]"
                    keys.append(current_path)
                    
                    # 递归处理数组项
                    if isinstance(item, (dict, list)):
                        keys.extend(extract_keys(item, current_path))
            
            return keys
        
        return extract_keys(data)
    
    def get_value_at_path(self, data: Any, path: str) -> Tuple[bool, Any]:
        """根据路径获取值
        
        Args:
            data: 数据对象
            path: 路径字符串
            
        Returns:
            Tuple[bool, Any]: (是否成功, 值)
        """
        try:
            parsed = self.parse_path(path)
            if not parsed.is_valid:
                return False, None
            
            current = data
            for segment in parsed.segments:
                if segment.is_array_index:
                    if not isinstance(current, list):
                        return False, None
                    
                    if segment.is_wildcard:
                        # 通配符，返回整个数组
                        return True, current
                    elif segment.array_index is not None:
                        if segment.array_index >= len(current) or segment.array_index < 0:
                            return False, None
                        current = current[segment.array_index]
                    else:
                        return False, None
                else:
                    if not isinstance(current, dict):
                        return False, None
                    
                    if segment.key not in current:
                        return False, None
                    
                    current = current[segment.key]
            
            return True, current
            
        except Exception:
            return False, None
    
    def set_value_at_path(self, data: Any, path: str, value: Any) -> bool:
        """根据路径设置值
        
        Args:
            data: 数据对象
            path: 路径字符串
            value: 要设置的值
            
        Returns:
            bool: 是否成功
        """
        try:
            parsed = self.parse_path(path)
            if not parsed.is_valid or not parsed.segments:
                return False
            
            current = data
            
            # 导航到父级
            for segment in parsed.segments[:-1]:
                if segment.is_array_index:
                    if not isinstance(current, list):
                        return False
                    
                    if segment.array_index is not None:
                        if segment.array_index >= len(current):
                            return False
                        current = current[segment.array_index]
                    else:
                        return False
                else:
                    if not isinstance(current, dict):
                        return False
                    
                    if segment.key not in current:
                        current[segment.key] = {}
                    
                    current = current[segment.key]
            
            # 设置最终值
            final_segment = parsed.segments[-1]
            if final_segment.is_array_index:
                if not isinstance(current, list):
                    return False
                
                if final_segment.array_index is not None:
                    if final_segment.array_index >= len(current):
                        return False
                    current[final_segment.array_index] = value
                else:
                    return False
            else:
                if not isinstance(current, dict):
                    return False
                
                current[final_segment.key] = value
            
            return True
            
        except Exception:
            return False
    
    def clear_cache(self):
        """清空路径解析缓存"""
        self.path_cache.clear()


# 便捷函数
def build_dot_path(*segments: Union[str, int]) -> str:
    """构建点号路径的便捷函数"""
    builder = PathBuilder(PathStyle.DOT)
    return builder.build_path(*segments)


def build_slash_path(*segments: Union[str, int]) -> str:
    """构建斜杠路径的便捷函数"""
    builder = PathBuilder(PathStyle.SLASH)
    return builder.build_path(*segments)


def convert_slash_to_dot(path: str) -> str:
    """将斜杠路径转换为点号路径的便捷函数"""
    builder = PathBuilder()
    return builder.convert_path(path, PathStyle.DOT)