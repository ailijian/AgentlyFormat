#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
增量 Schema 验证器使用示例

本示例展示如何使用 schemas.py 模块进行 JSON Schema 验证，
包括基础验证、修复建议、事件系统集成等功能。
"""

import json
import sys
import os
from typing import Dict, Any

# 添加项目路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from agently_format.core.schemas import (
    ValidationLevel,
    RepairStrategy,
    SchemaValidator,
    ValidationContext,
    validate_json_path,
    create_schema_validator
)
from agently_format.core.event_system import EventEmitter


def basic_validation_example():
    """基础验证示例"""
    print("=== 基础验证示例 ===")
    
    # 定义 Schema
    user_schema = {
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
            },
            "preferences": {
                "type": "object",
                "properties": {
                    "theme": {"type": "string", "default": "light"},
                    "notifications": {"type": "boolean", "default": True}
                }
            }
        },
        "required": ["name", "age"]
    }
    
    # 创建验证器
    validator = SchemaValidator(enable_caching=True)
    context = ValidationContext(schema=user_schema)
    
    # 测试数据
    test_cases = [
        ("name", "John Doe", "有效姓名"),
        ("name", "J", "姓名太短"),
        ("age", 25, "有效年龄"),
        ("age", "25", "年龄类型错误"),
        ("age", -5, "年龄超出范围"),
        ("email", "john@example.com", "有效邮箱"),
        ("email", "invalid-email", "无效邮箱"),
        ("status", "active", "有效状态"),
        ("status", "activ", "状态拼写错误")
    ]
    
    for path, value, description in test_cases:
        print(f"\n测试: {description}")
        print(f"路径: {path}, 值: {value}")
        
        result = validator.validate_path(path, value, context)
        
        if result.is_valid:
            print("✅ 验证通过")
        else:
            print("❌ 验证失败")
            print(f"置信度: {result.confidence:.2f}")
            
            # 显示问题
            for issue in result.issues:
                print(f"  问题: {issue.message} (约束: {issue.constraint})")
            
            # 显示修复建议
            for suggestion in result.suggestions:
                print(f"  建议: {suggestion.reason}")
                print(f"    原值: {suggestion.original_value}")
                print(f"    建议值: {suggestion.suggested_value}")
                print(f"    置信度: {suggestion.confidence:.2f}")
                print(f"    策略: {suggestion.strategy.value}")
    
    # 显示统计信息
    print("\n=== 验证统计 ===")
    stats = validator.get_stats()
    for key, value in stats.items():
        print(f"{key}: {value}")


def json_path_validation_example():
    """JSON 路径验证示例"""
    print("\n\n=== JSON 路径验证示例 ===")
    
    # 测试数据
    user_data = {
        "user": {
            "name": "Alice",
            "age": "30",  # 类型错误
            "contacts": [
                {"type": "email", "value": "alice@example.com"},
                {"type": "phone", "value": "123-456-7890"}
            ],
            "preferences": {
                "theme": "dark",
                "notifications": "yes"  # 类型错误
            }
        }
    }
    
    # Schema 定义
    schema = {
        "type": "object",
        "properties": {
            "user": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "age": {"type": "integer"},
                    "contacts": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "type": {"type": "string"},
                                "value": {"type": "string"}
                            }
                        }
                    },
                    "preferences": {
                        "type": "object",
                        "properties": {
                            "theme": {"type": "string"},
                            "notifications": {"type": "boolean"}
                        }
                    }
                }
            }
        }
    }
    
    # 验证不同路径
    paths_to_validate = [
        "user.name",
        "user.age",
        "user.contacts[0].type",
        "user.preferences.theme",
        "user.preferences.notifications",
        "user.nonexistent"  # 不存在的路径
    ]
    
    for path in paths_to_validate:
        print(f"\n验证路径: {path}")
        
        result = validate_json_path(user_data, path, schema)
        
        if result.is_valid:
            print("✅ 验证通过")
        else:
            print("❌ 验证失败")
            
            for issue in result.issues:
                print(f"  问题: {issue.message}")
            
            for suggestion in result.suggestions:
                print(f"  建议: {suggestion.reason}")
                print(f"    建议值: {suggestion.suggested_value}")


def event_integration_example():
    """事件系统集成示例"""
    print("\n\n=== 事件系统集成示例 ===")
    
    # 创建事件发射器
    event_emitter = EventEmitter()
    
    # 注册事件处理器
    def on_validation_start(data):
        print(f"🚀 开始验证路径: {data['path']}")
    
    def on_validation_error(data):
        print(f"❌ 验证错误: {data['path']}")
        print(f"   置信度: {data['confidence']:.2f}")
    
    def on_validation_warning(data):
        print(f"⚠️  验证警告: {data['path']}")
    
    def on_validation_delta(data):
        print(f"🔄 建议修复: {data['path']}")
        print(f"   原值: {data['original_value']}")
        print(f"   建议值: {data['suggested_value']}")
        print(f"   置信度: {data['confidence']:.2f}")
    
    def on_validation_complete(data):
        print(f"✅ 验证完成: {data['path']} (有效: {data['is_valid']})")
    
    # 注册事件监听器
    event_emitter.on('validation_start', on_validation_start)
    event_emitter.on('validation_error', on_validation_error)
    event_emitter.on('validation_warning', on_validation_warning)
    event_emitter.on('validation_delta', on_validation_delta)
    event_emitter.on('validation_complete', on_validation_complete)
    
    # 创建带事件的验证器
    schema = {
        "type": "object",
        "properties": {
            "count": {"type": "integer", "minimum": 0},
            "name": {"type": "string", "minLength": 2}
        }
    }
    
    validator = create_schema_validator(schema, event_emitter=event_emitter)
    context = ValidationContext(schema=schema)
    
    # 执行验证（会触发事件）
    test_cases = [
        ("count", "5", "字符串数字"),
        ("count", -1, "负数"),
        ("name", "A", "名称太短")
    ]
    
    for path, value, description in test_cases:
        print(f"\n--- {description} ---")
        result = validator.validate_path(path, value, context)


def advanced_repair_example():
    """高级修复建议示例"""
    print("\n\n=== 高级修复建议示例 ===")
    
    # 复杂 Schema
    product_schema = {
        "type": "object",
        "properties": {
            "name": {
                "type": "string",
                "minLength": 3,
                "maxLength": 100
            },
            "price": {
                "type": "number",
                "minimum": 0.01,
                "maximum": 10000.00
            },
            "category": {
                "type": "string",
                "enum": ["electronics", "clothing", "books", "home", "sports"]
            },
            "in_stock": {
                "type": "boolean"
            },
            "tags": {
                "type": "array",
                "items": {"type": "string"},
                "minItems": 1,
                "maxItems": 10
            }
        },
        "required": ["name", "price", "category"]
    }
    
    validator = SchemaValidator(enable_caching=True)
    context = ValidationContext(schema=product_schema)
    
    # 测试各种修复场景
    repair_test_cases = [
        ("price", "19.99", "字符串价格转数字"),
        ("price", -5.0, "负价格修正"),
        ("price", 15000.0, "超高价格修正"),
        ("category", "electronic", "类别拼写错误"),
        ("category", "unknown", "未知类别"),
        ("in_stock", "true", "字符串布尔值"),
        ("in_stock", 1, "数字布尔值"),
        ("name", "TV", "名称太短"),
        ("name", "A" * 150, "名称太长")
    ]
    
    for path, value, description in repair_test_cases:
        print(f"\n--- {description} ---")
        print(f"路径: {path}, 原值: {value}")
        
        result = validator.validate_path(path, value, context)
        
        if result.suggestions:
            print("修复建议:")
            for i, suggestion in enumerate(result.suggestions, 1):
                print(f"  {i}. {suggestion.reason}")
                print(f"     建议值: {suggestion.suggested_value}")
                print(f"     置信度: {suggestion.confidence:.2f}")
                print(f"     策略: {suggestion.strategy.value}")
                
                # 根据策略显示不同的处理方式
                if suggestion.strategy == RepairStrategy.AUTO_SAFE:
                    print(f"     🤖 可自动应用")
                elif suggestion.strategy == RepairStrategy.SUGGEST:
                    print(f"     💡 建议人工确认")
                elif suggestion.strategy == RepairStrategy.MANUAL:
                    print(f"     ✋ 需要手动处理")
        else:
            print("无修复建议")


def performance_example():
    """性能测试示例"""
    print("\n\n=== 性能测试示例 ===")
    
    import time
    
    # 创建大型 Schema
    large_schema = {
        "type": "object",
        "properties": {}
    }
    
    # 生成100个属性
    for i in range(100):
        large_schema["properties"][f"field_{i}"] = {
            "type": "string" if i % 2 == 0 else "integer",
            "minLength": 1 if i % 2 == 0 else None,
            "minimum": 0 if i % 2 == 1 else None
        }
    
    # 测试缓存性能
    validator_with_cache = SchemaValidator(enable_caching=True)
    validator_without_cache = SchemaValidator(enable_caching=False)
    context = ValidationContext(schema=large_schema)
    
    test_data = [(f"field_{i}", f"value_{i}" if i % 2 == 0 else i) for i in range(50)]
    
    # 测试带缓存的性能
    start_time = time.time()
    for _ in range(3):  # 重复3次以测试缓存效果
        for path, value in test_data:
            validator_with_cache.validate_path(path, value, context)
    cache_time = time.time() - start_time
    
    # 测试不带缓存的性能
    start_time = time.time()
    for _ in range(3):
        for path, value in test_data:
            validator_without_cache.validate_path(path, value, context)
    no_cache_time = time.time() - start_time
    
    print(f"带缓存验证时间: {cache_time:.4f}秒")
    print(f"不带缓存验证时间: {no_cache_time:.4f}秒")
    print(f"性能提升: {(no_cache_time / cache_time - 1) * 100:.1f}%")
    
    # 显示缓存统计
    cache_stats = validator_with_cache.get_stats()
    print(f"缓存命中率: {cache_stats['cache_hit_rate']:.1f}%")


def main():
    """主函数"""
    print("增量 Schema 验证器使用示例")
    print("=" * 50)
    
    try:
        # 运行各种示例
        basic_validation_example()
        json_path_validation_example()
        event_integration_example()
        advanced_repair_example()
        performance_example()
        
        print("\n\n🎉 所有示例运行完成！")
        
    except Exception as e:
        print(f"\n❌ 运行示例时出错: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()