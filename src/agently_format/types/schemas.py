"""JSON模式和验证规则定义

定义JSON数据结构的模式、字段类型和验证规则。
"""

from enum import Enum
from typing import Any, Dict, List, Optional, Union, Callable
from dataclasses import dataclass, field
import re


class FieldType(Enum):
    """字段类型枚举"""
    STRING = "string"
    INTEGER = "integer"
    NUMBER = "number"
    BOOLEAN = "boolean"
    ARRAY = "array"
    OBJECT = "object"
    NULL = "null"
    ANY = "any"


@dataclass
class ValidationRule:
    """验证规则"""
    rule_type: str
    rule_value: Any
    error_message: Optional[str] = None
    
    def validate(self, value: Any) -> tuple[bool, Optional[str]]:
        """执行验证
        
        Returns:
            tuple: (is_valid, error_message)
        """
        try:
            if self.rule_type == "required" and self.rule_value:
                if value is None or value == "":
                    return False, self.error_message or "Field is required"
            
            elif self.rule_type == "min_length" and isinstance(value, str):
                if len(value) < self.rule_value:
                    return False, self.error_message or f"Minimum length is {self.rule_value}"
            
            elif self.rule_type == "max_length" and isinstance(value, str):
                if len(value) > self.rule_value:
                    return False, self.error_message or f"Maximum length is {self.rule_value}"
            
            elif self.rule_type == "pattern" and isinstance(value, str):
                if not re.match(self.rule_value, value):
                    return False, self.error_message or f"Value does not match pattern {self.rule_value}"
            
            elif self.rule_type == "minimum" and isinstance(value, (int, float)):
                if value < self.rule_value:
                    return False, self.error_message or f"Minimum value is {self.rule_value}"
            
            elif self.rule_type == "maximum" and isinstance(value, (int, float)):
                if value > self.rule_value:
                    return False, self.error_message or f"Maximum value is {self.rule_value}"
            
            elif self.rule_type == "enum":
                if value not in self.rule_value:
                    return False, self.error_message or f"Value must be one of {self.rule_value}"
            
            elif self.rule_type == "custom" and callable(self.rule_value):
                result = self.rule_value(value)
                if isinstance(result, bool):
                    return result, self.error_message if not result else None
                elif isinstance(result, tuple):
                    return result
            
            return True, None
            
        except Exception as e:
            return False, f"Validation error: {str(e)}"


@dataclass
class FieldSchema:
    """字段模式定义"""
    name: str
    field_type: FieldType
    description: Optional[str] = None
    required: bool = False
    default_value: Any = None
    
    # 验证规则
    validation_rules: List[ValidationRule] = field(default_factory=list)
    
    # 数组相关
    items_schema: Optional['FieldSchema'] = None
    min_items: Optional[int] = None
    max_items: Optional[int] = None
    
    # 对象相关
    properties: Optional[Dict[str, 'FieldSchema']] = None
    additional_properties: bool = True
    
    # 字符串相关
    min_length: Optional[int] = None
    max_length: Optional[int] = None
    pattern: Optional[str] = None
    
    # 数值相关
    minimum: Optional[Union[int, float]] = None
    maximum: Optional[Union[int, float]] = None
    multiple_of: Optional[Union[int, float]] = None
    
    # 枚举值
    enum_values: Optional[List[Any]] = None
    
    # 自定义验证函数
    custom_validator: Optional[Callable[[Any], Union[bool, tuple[bool, str]]]] = None
    
    def __post_init__(self):
        """初始化后处理"""
        if self.properties is None and self.field_type == FieldType.OBJECT:
            self.properties = {}
        
        # 自动添加基本验证规则
        if self.required:
            self.validation_rules.append(
                ValidationRule("required", True, "Field is required")
            )
        
        if self.min_length is not None:
            self.validation_rules.append(
                ValidationRule("min_length", self.min_length)
            )
        
        if self.max_length is not None:
            self.validation_rules.append(
                ValidationRule("max_length", self.max_length)
            )
        
        if self.pattern is not None:
            self.validation_rules.append(
                ValidationRule("pattern", self.pattern)
            )
        
        if self.minimum is not None:
            self.validation_rules.append(
                ValidationRule("minimum", self.minimum)
            )
        
        if self.maximum is not None:
            self.validation_rules.append(
                ValidationRule("maximum", self.maximum)
            )
        
        if self.enum_values is not None:
            self.validation_rules.append(
                ValidationRule("enum", self.enum_values)
            )
        
        if self.custom_validator is not None:
            self.validation_rules.append(
                ValidationRule("custom", self.custom_validator)
            )
    
    def validate(self, value: Any) -> tuple[bool, List[str]]:
        """验证字段值
        
        Returns:
            tuple: (is_valid, error_messages)
        """
        errors = []
        
        # 类型验证
        if not self._validate_type(value):
            errors.append(f"Expected type {self.field_type.value}, got {type(value).__name__}")
            return False, errors
        
        # 执行所有验证规则
        for rule in self.validation_rules:
            is_valid, error_msg = rule.validate(value)
            if not is_valid and error_msg:
                errors.append(error_msg)
        
        # 数组特殊验证
        if self.field_type == FieldType.ARRAY and isinstance(value, list):
            if self.min_items is not None and len(value) < self.min_items:
                errors.append(f"Array must have at least {self.min_items} items")
            
            if self.max_items is not None and len(value) > self.max_items:
                errors.append(f"Array must have at most {self.max_items} items")
            
            # 验证数组项
            if self.items_schema:
                for i, item in enumerate(value):
                    item_valid, item_errors = self.items_schema.validate(item)
                    if not item_valid:
                        for error in item_errors:
                            errors.append(f"Item {i}: {error}")
        
        # 对象特殊验证
        elif self.field_type == FieldType.OBJECT and isinstance(value, dict):
            if self.properties:
                # 验证必需属性
                for prop_name, prop_schema in self.properties.items():
                    if prop_schema.required and prop_name not in value:
                        errors.append(f"Required property '{prop_name}' is missing")
                    elif prop_name in value:
                        prop_valid, prop_errors = prop_schema.validate(value[prop_name])
                        if not prop_valid:
                            for error in prop_errors:
                                errors.append(f"Property '{prop_name}': {error}")
                
                # 检查额外属性
                if not self.additional_properties:
                    extra_props = set(value.keys()) - set(self.properties.keys())
                    if extra_props:
                        errors.append(f"Additional properties not allowed: {list(extra_props)}")
        
        return len(errors) == 0, errors
    
    def _validate_type(self, value: Any) -> bool:
        """验证值的类型"""
        if self.field_type == FieldType.ANY:
            return True
        elif self.field_type == FieldType.NULL:
            return value is None
        elif self.field_type == FieldType.STRING:
            return isinstance(value, str)
        elif self.field_type == FieldType.INTEGER:
            return isinstance(value, int) and not isinstance(value, bool)
        elif self.field_type == FieldType.NUMBER:
            return isinstance(value, (int, float)) and not isinstance(value, bool)
        elif self.field_type == FieldType.BOOLEAN:
            return isinstance(value, bool)
        elif self.field_type == FieldType.ARRAY:
            return isinstance(value, list)
        elif self.field_type == FieldType.OBJECT:
            return isinstance(value, dict)
        return False
    
    def to_json_schema(self) -> Dict[str, Any]:
        """转换为标准JSON Schema格式"""
        schema = {
            "type": self.field_type.value
        }
        
        if self.description:
            schema["description"] = self.description
        
        if self.default_value is not None:
            schema["default"] = self.default_value
        
        # 字符串相关
        if self.min_length is not None:
            schema["minLength"] = self.min_length
        if self.max_length is not None:
            schema["maxLength"] = self.max_length
        if self.pattern is not None:
            schema["pattern"] = self.pattern
        
        # 数值相关
        if self.minimum is not None:
            schema["minimum"] = self.minimum
        if self.maximum is not None:
            schema["maximum"] = self.maximum
        if self.multiple_of is not None:
            schema["multipleOf"] = self.multiple_of
        
        # 数组相关
        if self.field_type == FieldType.ARRAY:
            if self.min_items is not None:
                schema["minItems"] = self.min_items
            if self.max_items is not None:
                schema["maxItems"] = self.max_items
            if self.items_schema:
                schema["items"] = self.items_schema.to_json_schema()
        
        # 对象相关
        if self.field_type == FieldType.OBJECT and self.properties:
            schema["properties"] = {
                name: prop.to_json_schema() 
                for name, prop in self.properties.items()
            }
            required_props = [
                name for name, prop in self.properties.items() 
                if prop.required
            ]
            if required_props:
                schema["required"] = required_props
            schema["additionalProperties"] = self.additional_properties
        
        # 枚举值
        if self.enum_values is not None:
            schema["enum"] = self.enum_values
        
        return schema


@dataclass
class JSONSchema:
    """JSON模式定义"""
    name: str
    version: str = "1.0"
    description: Optional[str] = None
    root_schema: Optional[FieldSchema] = None
    strict_mode: bool = False
    
    def __post_init__(self):
        """初始化后处理"""
        if self.root_schema is None:
            self.root_schema = FieldSchema(
                name="root",
                field_type=FieldType.OBJECT,
                required=True
            )
    
    def validate(self, data: Any) -> tuple[bool, List[str]]:
        """验证数据
        
        Returns:
            tuple: (is_valid, error_messages)
        """
        if self.root_schema is None:
            return True, []
        
        return self.root_schema.validate(data)
    
    def to_json_schema(self) -> Dict[str, Any]:
        """转换为标准JSON Schema格式"""
        schema = {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "title": self.name,
            "version": self.version
        }
        
        if self.description:
            schema["description"] = self.description
        
        if self.root_schema:
            schema.update(self.root_schema.to_json_schema())
        
        return schema
    
    def add_field(self, path: str, field_schema: FieldSchema):
        """添加字段到模式中
        
        Args:
            path: 字段路径，如 'user.name' 或 'items[].id'
            field_schema: 字段模式
        """
        if self.root_schema is None:
            self.root_schema = FieldSchema(
                name="root",
                field_type=FieldType.OBJECT,
                properties={}
            )
        
        self._add_field_recursive(self.root_schema, path.split('.'), field_schema)
    
    def _add_field_recursive(self, current_schema: FieldSchema, path_parts: List[str], field_schema: FieldSchema):
        """递归添加字段"""
        if len(path_parts) == 1:
            # 到达目标位置
            field_name = path_parts[0]
            if current_schema.properties is None:
                current_schema.properties = {}
            current_schema.properties[field_name] = field_schema
        else:
            # 继续向下
            field_name = path_parts[0]
            remaining_path = path_parts[1:]
            
            if current_schema.properties is None:
                current_schema.properties = {}
            
            if field_name not in current_schema.properties:
                # 创建中间对象
                current_schema.properties[field_name] = FieldSchema(
                    name=field_name,
                    field_type=FieldType.OBJECT,
                    properties={}
                )
            
            self._add_field_recursive(
                current_schema.properties[field_name],
                remaining_path,
                field_schema
            )


# 便捷函数
def create_string_field(
    name: str,
    required: bool = False,
    min_length: Optional[int] = None,
    max_length: Optional[int] = None,
    pattern: Optional[str] = None,
    enum_values: Optional[List[str]] = None,
    description: Optional[str] = None
) -> FieldSchema:
    """创建字符串字段"""
    return FieldSchema(
        name=name,
        field_type=FieldType.STRING,
        required=required,
        min_length=min_length,
        max_length=max_length,
        pattern=pattern,
        enum_values=enum_values,
        description=description
    )


def create_number_field(
    name: str,
    required: bool = False,
    minimum: Optional[Union[int, float]] = None,
    maximum: Optional[Union[int, float]] = None,
    multiple_of: Optional[Union[int, float]] = None,
    description: Optional[str] = None
) -> FieldSchema:
    """创建数值字段"""
    return FieldSchema(
        name=name,
        field_type=FieldType.NUMBER,
        required=required,
        minimum=minimum,
        maximum=maximum,
        multiple_of=multiple_of,
        description=description
    )


def create_array_field(
    name: str,
    items_schema: FieldSchema,
    required: bool = False,
    min_items: Optional[int] = None,
    max_items: Optional[int] = None,
    description: Optional[str] = None
) -> FieldSchema:
    """创建数组字段"""
    return FieldSchema(
        name=name,
        field_type=FieldType.ARRAY,
        required=required,
        items_schema=items_schema,
        min_items=min_items,
        max_items=max_items,
        description=description
    )


def create_object_field(
    name: str,
    properties: Dict[str, FieldSchema],
    required: bool = False,
    additional_properties: bool = True,
    description: Optional[str] = None
) -> FieldSchema:
    """创建对象字段"""
    return FieldSchema(
        name=name,
        field_type=FieldType.OBJECT,
        required=required,
        properties=properties,
        additional_properties=additional_properties,
        description=description
    )