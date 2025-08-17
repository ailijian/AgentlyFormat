"""豆包模型适配器

实现字节跳动豆包API的适配器。
"""

import json
import copy
from typing import Any, Dict, List, Optional, AsyncGenerator, Union, Awaitable
import aiohttp

from .model_adapter import BaseModelAdapter, ModelResponse
from ..types.models import ModelType
from ..core.streaming_parser import parse_json_stream_with_fields, FieldFilter


class DoubaoAdapter(BaseModelAdapter):
    """豆包适配器"""
    
    def __init__(self, config):
        """初始化豆包适配器
        
        Args:
            config: 模型配置
        """
        # 设置默认base_url
        if not config.base_url:
            config.base_url = "https://ark.cn-beijing.volces.com/api/v3"
        
        super().__init__(config)
        
        # 添加必要属性以保持向后兼容
        self.model_name = config.model_name
        self.api_key = config.api_key
        self.base_url = config.base_url
    
    def chat_completion(
        self,
        messages: List[Dict[str, str]],
        stream: bool = False,
        include_fields: Optional[List[str]] = None,
        exclude_fields: Optional[List[str]] = None,
        field_filter: Optional[FieldFilter] = None,
        **kwargs
    ) -> Union[Awaitable[ModelResponse], AsyncGenerator[str, None]]:
        """聊天补全接口
        
        Args:
            messages: 消息列表
            stream: 是否流式输出
            include_fields: 包含的字段列表（仅在JSON格式输出时有效）
            exclude_fields: 排除的字段列表（仅在JSON格式输出时有效）
            field_filter: 自定义字段过滤器
            **kwargs: 其他参数
            
        Returns:
            Union[Awaitable[ModelResponse], AsyncGenerator[str, None]]: 响应或流式生成器
        """

        
        if stream:
            # 对于流式调用，直接返回async generator
            return self._stream_chat_completion(
                messages, 
                include_fields=include_fields,
                exclude_fields=exclude_fields,
                field_filter=field_filter,
                **kwargs
            )
        else:
            # 对于非流式调用，返回awaitable
            return self._non_stream_chat_completion(messages, **kwargs)
    
    async def _non_stream_chat_completion(
        self,
        messages: List[Dict[str, str]],
        **kwargs
    ) -> ModelResponse:
        """非流式聊天补全
        
        Args:
            messages: 消息列表
            **kwargs: 其他参数
            
        Returns:
            ModelResponse: 响应
        """
        payload = self._build_request_payload(messages, stream=False, **kwargs)
        response_data = await self._make_request("/chat/completions", payload, stream=False)
        return self._parse_response(response_data)
    
    async def _stream_chat_completion(
        self,
        messages: List[Dict[str, str]],
        include_fields: Optional[List[str]] = None,
        exclude_fields: Optional[List[str]] = None,
        field_filter: Optional[FieldFilter] = None,
        **kwargs
    ) -> AsyncGenerator[str, None]:
        """流式聊天补全 - 支持字段过滤的智能输出
        
        Args:
            messages: 消息列表
            include_fields: 包含的字段列表
            exclude_fields: 排除的字段列表
            field_filter: 自定义字段过滤器
            **kwargs: 其他参数
            
        Yields:
            str: 流式响应内容
        """

        
        payload = self._build_request_payload(messages, **kwargs)
        payload["stream"] = True
        headers = self._get_auth_headers()
        
        # 检查是否需要字段过滤
        needs_field_filtering = (
            include_fields is not None or 
            exclude_fields is not None or 
            field_filter is not None
        )
        

        
        if needs_field_filtering:
            # 使用字段过滤的流式解析
            async for content in self._stream_with_field_filtering(
                payload, headers, include_fields, exclude_fields, field_filter
            ):
                yield content
        else:
            # 原始的纯文本流式输出
            async for line in self._stream_request("/chat/completions", payload, headers):
                content = self._parse_stream_chunk(line)
                if content:
                     yield content
    
    async def _stream_with_field_filtering(
        self,
        payload: Dict[str, Any],
        headers: Dict[str, str],
        include_fields: Optional[List[str]] = None,
        exclude_fields: Optional[List[str]] = None,
        field_filter: Optional[FieldFilter] = None
    ) -> AsyncGenerator[str, None]:
        """使用字段过滤的流式请求处理 - 纯净字段内容流式输出
        
        Args:
            payload: 请求载荷
            headers: 请求头
            include_fields: 包含的字段列表
            exclude_fields: 排除的字段列表
            field_filter: 自定义字段过滤器
            
        Yields:
            str: 过滤后的字段内容
        """
        try:
            # 构建字段过滤器
            if field_filter is None:
                if include_fields or exclude_fields:
                    field_filter = FieldFilter(
                        enabled=True,
                        include_paths=include_fields or [],
                        exclude_paths=exclude_fields or [],
                        mode="include" if include_fields else "exclude",
                        exact_match=False
                    )
                else:
                    field_filter = FieldFilter(enabled=False)
            
            # 如果没有启用字段过滤，直接流式输出
            if not field_filter.enabled:
                async for line in self._stream_request("/chat/completions", payload, headers):
                    content = self._parse_stream_chunk(line)
                    if content:
                        yield content
                return
            
            # 真正的流式字段过滤实现
            from ..core.streaming_parser import StreamingParser
            import asyncio
            
            # 创建流式解析器
            parser = StreamingParser(field_filter=field_filter)
            
            # 累积缓冲区，用于处理不完整的JSON片段
            buffer = ""
            json_started = False
            json_content = ""
            brace_count = 0
            in_string = False
            escape_next = False
            
            async for line in self._stream_request("/chat/completions", payload, headers):
                content = self._parse_stream_chunk(line)
                if not content:
                    continue
                
                buffer += content
                
                # 检测JSON代码块的开始
                if not json_started and '```' in buffer:
                    # 查找JSON代码块开始
                    json_start_patterns = ['```json', '```']
                    for pattern in json_start_patterns:
                        if pattern in buffer:
                            start_idx = buffer.find(pattern)
                            if start_idx != -1:
                                json_started = True
                                # 移除代码块标记之前的内容
                                buffer = buffer[start_idx + len(pattern):].lstrip()
                                break
                
                if json_started:
                    # 逐字符处理，检测完整的JSON对象
                    for char in buffer:
                        if char == '`' and json_content.count('`') >= 2:
                            # JSON代码块结束
                            break
                        
                        json_content += char
                        
                        if not escape_next:
                            if char == '"' and not escape_next:
                                in_string = not in_string
                            elif not in_string:
                                if char == '{':
                                    brace_count += 1
                                elif char == '}':
                                    brace_count -= 1
                                    
                                    # 检查是否有完整的JSON对象
                                    if brace_count == 0 and json_content.strip():
                                        try:
                                            # 尝试解析JSON
                                            data = json.loads(json_content.strip())
                                            
                                            # 提取字段值并流式输出
                                            field_values = self._extract_field_values(data, include_fields, exclude_fields)
                                            
                                            for i, value in enumerate(field_values):
                                                if i > 0:
                                                    yield "\n"  # 字段间换行
                                                
                                                value_str = str(value)
                                                # 真正的流式输出每个字符
                                                for char in value_str:
                                                    yield char
                                                    await asyncio.sleep(0.005)  # 减少延迟
                                            
                                            return  # 完成输出后退出
                                            
                                        except json.JSONDecodeError:
                                            # JSON不完整，继续累积
                                            pass
                            
                            if char == '\\':
                                escape_next = True
                        else:
                            escape_next = False
                    
                    buffer = ""  # 清空缓冲区
            
            # 如果没有找到完整的JSON，尝试从累积的内容中提取
            if json_content:
                try:
                    data = json.loads(json_content.strip())
                    field_values = self._extract_field_values(data, include_fields, exclude_fields)
                    
                    for i, value in enumerate(field_values):
                        if i > 0:
                            yield "\n"
                        
                        value_str = str(value)
                        for char in value_str:
                            yield char
                            await asyncio.sleep(0.005)
                            
                except json.JSONDecodeError:
                    # 最后尝试从文本中提取字段
                    field_values = self._extract_fields_from_text(json_content, include_fields, exclude_fields)
                    for i, value in enumerate(field_values):
                        if i > 0:
                            yield "\n"
                        for char in str(value):
                            yield char
                            await asyncio.sleep(0.005)
                    
        except Exception as e:
            # 处理失败时的降级方案
            yield f"Error in field filtering: {str(e)}"
    

    
    def _build_field_path(self, json_data: str, field_name: str) -> str:
        """根据JSON数据和字段名构建字段路径
        
        Args:
            json_data: JSON数据字符串
            field_name: 字段名
            
        Returns:
            str: 字段路径
        """
        # 简单实现：检查是否在数组中
        import re
        
        # 查找数组索引模式
        array_pattern = r'\[\s*(\d+)\s*\]'
        array_matches = re.findall(array_pattern, json_data)
        
        if array_matches:
            # 在数组中，构建带索引的路径
            last_index = array_matches[-1]
            return f"languages[{last_index}].{field_name}"
        else:
            # 不在数组中，直接返回字段名
            return field_name
    
    def _flatten_json_paths(self, data: Any, prefix: str = "") -> Dict[str, Any]:
        """将JSON数据扁平化为路径-值对
        
        Args:
            data: JSON数据
            prefix: 路径前缀
            
        Returns:
            Dict[str, Any]: 路径到值的映射
        """
        result = {}
        
        if isinstance(data, dict):
            for key, value in data.items():
                new_prefix = f"{prefix}.{key}" if prefix else key
                if isinstance(value, (dict, list)):
                    result.update(self._flatten_json_paths(value, new_prefix))
                else:
                    result[new_prefix] = value
        elif isinstance(data, list):
            for i, item in enumerate(data):
                new_prefix = f"{prefix}[{i}]"
                if isinstance(item, (dict, list)):
                    result.update(self._flatten_json_paths(item, new_prefix))
                else:
                    result[new_prefix] = item
        else:
            result[prefix] = data
        
        return result
    

    
    def _reconstruct_json_from_paths(self, path_data: Dict[str, Any]) -> Any:
        """根据路径和值重构JSON结构
        
        Args:
            path_data: 路径到值的映射，如 {'languages[0].name': 'Python', 'languages[0].description': '...'}
            
        Returns:
            Any: 重构的JSON数据
        """
        result = {}
        
        for path, value in path_data.items():
            # 解析路径，如 "languages[0].name" -> ["languages", 0, "name"]
            parts = []
            current = ""
            i = 0
            
            while i < len(path):
                char = path[i]
                if char == '[':
                    if current:
                        parts.append(current)
                        current = ""
                    # 查找匹配的]
                    j = i + 1
                    while j < len(path) and path[j] != ']':
                        j += 1
                    if j < len(path):
                        index_str = path[i+1:j]
                        try:
                            parts.append(int(index_str))
                        except ValueError:
                            parts.append(index_str)
                        i = j + 1
                    else:
                        i += 1
                elif char == '.':
                    if current:
                        parts.append(current)
                        current = ""
                    i += 1
                else:
                    current += char
                    i += 1
            
            if current:
                parts.append(current)
            
            # 根据路径构建嵌套结构
            current_obj = result
            for i, part in enumerate(parts[:-1]):
                if isinstance(part, int):
                    # 数组索引
                    if not isinstance(current_obj, list):
                        current_obj = []
                    while len(current_obj) <= part:
                        current_obj.append({})
                    if not isinstance(current_obj[part], (dict, list)):
                        current_obj[part] = {}
                    current_obj = current_obj[part]
                else:
                    # 对象键
                    if part not in current_obj:
                        # 检查下一个部分是否为数组索引
                        if i + 1 < len(parts) - 1 and isinstance(parts[i + 1], int):
                            current_obj[part] = []
                        else:
                            current_obj[part] = {}
                    current_obj = current_obj[part]
            
            # 设置最终值
            final_part = parts[-1]
            if isinstance(final_part, int):
                if not isinstance(current_obj, list):
                    current_obj = []
                while len(current_obj) <= final_part:
                    current_obj.append(None)
                current_obj[final_part] = value
            else:
                current_obj[final_part] = value
        
        return result
    

    
    def _extract_json_from_text(self, text: str) -> Optional[str]:
        """从文本中提取JSON代码块
        
        Args:
            text: 输入文本
            
        Returns:
            Optional[str]: 提取的JSON字符串，如果没有找到则返回None
        """
        import re
        
        # 尝试匹配```json代码块
        json_pattern = r'```(?:json)?\s*([\s\S]*?)```'
        matches = re.findall(json_pattern, text, re.IGNORECASE)
        
        for match in matches:
            try:
                # 验证是否为有效JSON
                json.loads(match.strip())
                return match.strip()
            except json.JSONDecodeError:
                continue
        
        # 如果没有找到代码块，尝试直接解析整个文本
        try:
            json.loads(text.strip())
            return text.strip()
        except json.JSONDecodeError:
            pass
        
        return None
    
    def _extract_field_values(self, data: Any, include_fields: Optional[List[str]], exclude_fields: Optional[List[str]]) -> List[Any]:
        """从JSON数据中提取指定字段的值
        
        Args:
            data: JSON数据
            include_fields: 包含的字段列表
            exclude_fields: 排除的字段列表
            
        Returns:
            List[Any]: 提取的字段值列表
        """
        field_values = []
        
        def extract_recursive(obj, path=""):
            if isinstance(obj, dict):
                for key, value in obj.items():
                    current_path = f"{path}.{key}" if path else key
                    
                    # 检查字段是否匹配
                    should_include = False
                    
                    if include_fields:
                        # 包含模式：检查字段名是否在包含列表中
                        for include_field in include_fields:
                            if key == include_field or current_path.endswith(f".{include_field}"):
                                should_include = True
                                break
                    elif exclude_fields:
                        # 排除模式：检查字段名是否不在排除列表中
                        should_include = True
                        for exclude_field in exclude_fields:
                            if key == exclude_field or current_path.endswith(f".{exclude_field}"):
                                should_include = False
                                break
                    else:
                        should_include = True
                    
                    # 如果字段匹配，添加到结果中
                    if should_include and not isinstance(value, (dict, list)):
                        field_values.append(value)
                    
                    # 递归处理嵌套结构
                    if isinstance(value, (dict, list)):
                        extract_recursive(value, current_path)
                        
            elif isinstance(obj, list):
                for i, item in enumerate(obj):
                    current_path = f"{path}[{i}]" if path else f"[{i}]"
                    extract_recursive(item, current_path)
        
        extract_recursive(data)
        return field_values
    
    def _extract_fields_from_text(self, text: str, include_fields: Optional[List[str]], exclude_fields: Optional[List[str]]) -> List[str]:
        """从普通文本中提取字段（基于关键词匹配）
        
        Args:
            text: 输入文本
            include_fields: 包含的字段列表
            exclude_fields: 排除的字段列表
            
        Returns:
            List[str]: 提取的内容列表
        """
        if not include_fields and not exclude_fields:
            return [text]
        
        # 简单的关键词匹配实现
        lines = text.split('\n')
        matched_lines = []
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            should_include = False
            
            if include_fields:
                for field in include_fields:
                    if field.lower() in line.lower():
                        should_include = True
                        break
            elif exclude_fields:
                should_include = True
                for field in exclude_fields:
                    if field.lower() in line.lower():
                        should_include = False
                        break
            
            if should_include:
                matched_lines.append(line)
        
        return matched_lines if matched_lines else [text]
    

    

    
    def _is_json_content(self, content: str) -> bool:
        """判断内容是否为JSON格式
        
        Args:
            content: 待判断的内容
            
        Returns:
            bool: 是否为JSON格式
        """
        content = content.strip()
        if not content:
            return False
        
        # 简单的JSON格式检测
        try:
            # 尝试解析为JSON
            json.loads(content)
            return True
        except json.JSONDecodeError:
            # 检查是否包含JSON结构特征
            return (
                (content.startswith('{') and content.endswith('}')) or
                (content.startswith('[') and content.endswith(']')) or
                '"' in content and (':' in content or ',' in content)
            )
    
    def _build_request_payload(self, messages: List[Dict[str, str]], **kwargs) -> Dict[str, Any]:
        """构建豆包请求载荷
        
        Args:
            messages: 消息列表
            **kwargs: 其他参数
            
        Returns:
            Dict[str, Any]: 请求载荷
        """
        payload = {
            "model": self.config.model_name,
            "messages": messages,
            **self.config.request_params
        }
        
        # 添加额外参数
        for key, value in kwargs.items():
            if key not in ["stream"]:
                payload[key] = value
        
        # 处理流式参数
        if kwargs.get("stream", False):
            payload["stream"] = True
        
        return payload
    
    def _parse_response(self, response_data: Dict[str, Any]) -> ModelResponse:
        """解析豆包响应数据
        
        Args:
            response_data: 响应数据
            
        Returns:
            ModelResponse: 解析后的响应
        """
        choice = response_data["choices"][0]
        message = choice["message"]
        
        return ModelResponse(
            content=message["content"],
            usage=response_data.get("usage"),
            model=response_data.get("model"),
            finish_reason=choice.get("finish_reason"),
            metadata={
                "id": response_data.get("id"),
                "created": response_data.get("created"),
                "req_id": response_data.get("req_id")
            }
        )
    
    def _parse_stream_chunk(self, line: str) -> Optional[str]:
        """解析流式响应的单个数据块
        
        Args:
            line: 原始响应行数据
            
        Returns:
            Optional[str]: 解析出的内容增量，如果没有内容则返回None
        """
        if not line.strip():
            return None
        
        if line.startswith("data: "):
            data_content = line[6:].strip()
            
            if data_content == "[DONE]":
                return None
            
            try:
                data = json.loads(data_content)
                
                if "choices" in data and len(data["choices"]) > 0:
                    choice = data["choices"][0]
                    
                    if "delta" in choice and "content" in choice["delta"]:
                        content = choice["delta"]["content"]
                        return content if content else None
                
                return None
            except json.JSONDecodeError:
                # 忽略JSON解析错误，可能是不完整的数据块
                return None
        
        return None
    
    def _get_auth_headers(self) -> Dict[str, str]:
        """获取豆包认证头
        
        Returns:
            Dict[str, str]: 认证头
        """
        return {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json"
        }
    
    def get_model_info(self) -> Dict[str, Any]:
        """获取模型信息
        
        Returns:
            Dict[str, Any]: 模型信息
        """
        model_info = {
            "provider": "Doubao",
            "model_name": self.config.model_name,
            "model_type": self.config.model_type.value,
            "supports_streaming": True,
            "supports_function_calling": True,
            "max_tokens": self._get_max_tokens(),
            "context_window": self._get_context_window()
        }
        
        return model_info
    
    def _get_max_tokens(self) -> int:
        """获取最大输出token数
        
        Returns:
            int: 最大token数
        """
        # 豆包模型的默认限制
        model_limits = {
            "doubao-lite-4k": 4096,
            "doubao-lite-32k": 32768,
            "doubao-lite-128k": 128000,
            "doubao-pro-4k": 4096,
            "doubao-pro-32k": 32768,
            "doubao-pro-128k": 128000
        }
        
        return model_limits.get(self.config.model_name, 4096)
    
    def _get_context_window(self) -> int:
        """获取上下文窗口大小
        
        Returns:
            int: 上下文窗口大小
        """
        context_windows = {
            "doubao-lite-4k": 4096,
            "doubao-lite-32k": 32768,
            "doubao-lite-128k": 128000,
            "doubao-pro-4k": 4096,
            "doubao-pro-32k": 32768,
            "doubao-pro-128k": 128000
        }
        
        return context_windows.get(self.config.model_name, 4096)
    
    async def validate_api_key(self) -> bool:
        """验证API密钥
        
        Returns:
            bool: 是否有效
        """
        try:
            # 发送简单的测试请求
            test_messages = [
                {"role": "user", "content": "你好"}
            ]
            
            payload = self._build_request_payload(
                test_messages,
                max_tokens=1
            )
            
            await self._make_request("/chat/completions", payload)
            return True
            
        except Exception:
            return False
    
    def _format_messages_for_doubao(self, messages: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """格式化消息以适配豆包API
        
        Args:
            messages: 原始消息列表
            
        Returns:
            List[Dict[str, str]]: 格式化后的消息列表
        """
        formatted_messages = []
        
        for message in messages:
            # 确保消息格式正确
            formatted_message = {
                "role": message.get("role", "user"),
                "content": message.get("content", "")
            }
            
            # 豆包可能需要特殊处理某些角色
            if formatted_message["role"] not in ["system", "user", "assistant"]:
                formatted_message["role"] = "user"
            
            formatted_messages.append(formatted_message)
        
        return formatted_messages


# 注册适配器
from .model_adapter import ModelAdapter
ModelAdapter.register_adapter(ModelType.DOUBAO, DoubaoAdapter)