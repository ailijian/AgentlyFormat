"""性能基准测试数据集

提供全面的性能测试数据，包括不同规模和复杂度的JSON数据集、
流式解析数据、Schema验证数据、路径构建数据、差分引擎数据、
模型适配器数据和API性能测试数据。

每个数据集都包含详细的元数据信息和数据生成器函数，
确保数据具有代表性和可重复性。
"""

import json
import random
import string
import time
import uuid
from typing import Dict, List, Any, Generator, Tuple, Optional
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import itertools


class DatasetSize(Enum):
    """数据集规模枚举"""
    SMALL = "small"
    MEDIUM = "medium"
    LARGE = "large"
    XLARGE = "xlarge"


class ComplexityLevel(Enum):
    """复杂度级别枚举"""
    SIMPLE = "simple"
    MODERATE = "moderate"
    COMPLEX = "complex"
    EXTREME = "extreme"


@dataclass
class DatasetMetadata:
    """数据集元数据"""
    name: str
    description: str
    size: DatasetSize
    complexity: ComplexityLevel
    expected_memory_mb: float
    expected_parse_time_ms: float
    expected_completion_time_ms: float
    record_count: int
    avg_record_size_bytes: int
    max_nesting_depth: int
    schema_complexity_score: float
    created_at: datetime = field(default_factory=datetime.now)
    tags: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "name": self.name,
            "description": self.description,
            "size": self.size.value,
            "complexity": self.complexity.value,
            "expected_memory_mb": self.expected_memory_mb,
            "expected_parse_time_ms": self.expected_parse_time_ms,
            "expected_completion_time_ms": self.expected_completion_time_ms,
            "record_count": self.record_count,
            "avg_record_size_bytes": self.avg_record_size_bytes,
            "max_nesting_depth": self.max_nesting_depth,
            "schema_complexity_score": self.schema_complexity_score,
            "created_at": self.created_at.isoformat(),
            "tags": self.tags
        }


@dataclass
class BenchmarkDataset:
    """基准测试数据集"""
    metadata: DatasetMetadata
    data: Any
    generator_func: Optional[callable] = None
    
    def generate_fresh_data(self) -> Any:
        """生成新的数据实例"""
        if self.generator_func:
            return self.generator_func()
        return self.data


class JSONDatasetGenerator:
    """JSON数据集生成器"""
    
    @staticmethod
    def _generate_random_string(length: int = 10) -> str:
        """生成随机字符串"""
        return ''.join(random.choices(string.ascii_letters + string.digits, k=length))
    
    @staticmethod
    def _generate_random_email() -> str:
        """生成随机邮箱"""
        domains = ["gmail.com", "yahoo.com", "outlook.com", "company.com"]
        username = JSONDatasetGenerator._generate_random_string(8)
        domain = random.choice(domains)
        return f"{username}@{domain}"
    
    @staticmethod
    def _generate_user_profile(complexity: ComplexityLevel) -> Dict[str, Any]:
        """生成用户档案数据"""
        base_profile = {
            "id": str(uuid.uuid4()),
            "username": JSONDatasetGenerator._generate_random_string(12),
            "email": JSONDatasetGenerator._generate_random_email(),
            "created_at": datetime.now().isoformat(),
            "is_active": random.choice([True, False])
        }
        
        if complexity in [ComplexityLevel.MODERATE, ComplexityLevel.COMPLEX, ComplexityLevel.EXTREME]:
            base_profile.update({
                "profile": {
                    "first_name": JSONDatasetGenerator._generate_random_string(6),
                    "last_name": JSONDatasetGenerator._generate_random_string(8),
                    "age": random.randint(18, 80),
                    "location": {
                        "country": random.choice(["US", "CN", "UK", "DE", "JP"]),
                        "city": JSONDatasetGenerator._generate_random_string(10),
                        "coordinates": {
                            "lat": round(random.uniform(-90, 90), 6),
                            "lng": round(random.uniform(-180, 180), 6)
                        }
                    }
                },
                "preferences": {
                    "theme": random.choice(["light", "dark", "auto"]),
                    "language": random.choice(["en", "zh", "ja", "de", "fr"]),
                    "notifications": {
                        "email": random.choice([True, False]),
                        "push": random.choice([True, False]),
                        "sms": random.choice([True, False])
                    }
                }
            })
        
        if complexity in [ComplexityLevel.COMPLEX, ComplexityLevel.EXTREME]:
            base_profile.update({
                "activity_history": [
                    {
                        "action": random.choice(["login", "logout", "view", "edit", "delete"]),
                        "timestamp": (datetime.now() - timedelta(days=random.randint(0, 30))).isoformat(),
                        "ip_address": f"{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}",
                        "user_agent": JSONDatasetGenerator._generate_random_string(50)
                    } for _ in range(random.randint(5, 20))
                ],
                "permissions": {
                    "roles": [JSONDatasetGenerator._generate_random_string(8) for _ in range(random.randint(1, 5))],
                    "scopes": [JSONDatasetGenerator._generate_random_string(12) for _ in range(random.randint(3, 10))]
                }
            })
        
        if complexity == ComplexityLevel.EXTREME:
            base_profile.update({
                "metadata": {
                    "tags": [JSONDatasetGenerator._generate_random_string(6) for _ in range(random.randint(10, 30))],
                    "custom_fields": {
                        f"field_{i}": {
                            "type": random.choice(["string", "number", "boolean", "array", "object"]),
                            "value": JSONDatasetGenerator._generate_random_string(20),
                            "metadata": {
                                "created_by": JSONDatasetGenerator._generate_random_string(10),
                                "created_at": datetime.now().isoformat(),
                                "validation_rules": [JSONDatasetGenerator._generate_random_string(15) for _ in range(3)]
                            }
                        } for i in range(random.randint(5, 15))
                    }
                },
                "analytics": {
                    "page_views": random.randint(100, 10000),
                    "session_duration_avg": random.randint(60, 3600),
                    "conversion_events": [
                        {
                            "event_type": random.choice(["purchase", "signup", "download", "share"]),
                            "value": round(random.uniform(1, 1000), 2),
                            "timestamp": (datetime.now() - timedelta(hours=random.randint(0, 720))).isoformat(),
                            "properties": {
                                f"prop_{j}": JSONDatasetGenerator._generate_random_string(10) for j in range(random.randint(3, 8))
                            }
                        } for _ in range(random.randint(10, 50))
                    ]
                }
            })
        
        return base_profile
    
    @classmethod
    def generate_small_dataset(cls) -> BenchmarkDataset:
        """生成小规模数据集 (100条记录)"""
        def generator():
            return {
                "users": [cls._generate_user_profile(ComplexityLevel.SIMPLE) for _ in range(100)],
                "metadata": {
                    "total_count": 100,
                    "generated_at": datetime.now().isoformat(),
                    "version": "1.0"
                }
            }
        
        metadata = DatasetMetadata(
            name="small_json_dataset",
            description="小规模JSON数据集，包含100个简单用户档案",
            size=DatasetSize.SMALL,
            complexity=ComplexityLevel.SIMPLE,
            expected_memory_mb=0.5,
            expected_parse_time_ms=10.0,
            expected_completion_time_ms=5.0,
            record_count=100,
            avg_record_size_bytes=200,
            max_nesting_depth=3,
            schema_complexity_score=2.5,
            tags=["users", "simple", "baseline"]
        )
        
        return BenchmarkDataset(
            metadata=metadata,
            data=generator(),
            generator_func=generator
        )
    
    @classmethod
    def generate_medium_dataset(cls) -> BenchmarkDataset:
        """生成中等规模数据集 (1000条记录)"""
        def generator():
            return {
                "users": [cls._generate_user_profile(ComplexityLevel.MODERATE) for _ in range(1000)],
                "categories": [
                    {
                        "id": i,
                        "name": cls._generate_random_string(15),
                        "description": cls._generate_random_string(100),
                        "subcategories": [
                            {
                                "id": f"{i}_{j}",
                                "name": cls._generate_random_string(12),
                                "items_count": random.randint(10, 100)
                            } for j in range(random.randint(3, 8))
                        ]
                    } for i in range(50)
                ],
                "metadata": {
                    "total_count": 1000,
                    "generated_at": datetime.now().isoformat(),
                    "version": "1.0",
                    "statistics": {
                        "active_users": random.randint(800, 950),
                        "avg_session_time": random.randint(300, 1800),
                        "total_categories": 50
                    }
                }
            }
        
        metadata = DatasetMetadata(
            name="medium_json_dataset",
            description="中等规模JSON数据集，包含1000个中等复杂度用户档案和分类数据",
            size=DatasetSize.MEDIUM,
            complexity=ComplexityLevel.MODERATE,
            expected_memory_mb=5.0,
            expected_parse_time_ms=50.0,
            expected_completion_time_ms=25.0,
            record_count=1000,
            avg_record_size_bytes=800,
            max_nesting_depth=5,
            schema_complexity_score=5.5,
            tags=["users", "categories", "moderate", "nested"]
        )
        
        return BenchmarkDataset(
            metadata=metadata,
            data=generator(),
            generator_func=generator
        )
    
    @classmethod
    def generate_large_dataset(cls) -> BenchmarkDataset:
        """生成大规模数据集 (10000条记录)"""
        def generator():
            return {
                "users": [cls._generate_user_profile(ComplexityLevel.COMPLEX) for _ in range(10000)],
                "products": [
                    {
                        "id": str(uuid.uuid4()),
                        "name": cls._generate_random_string(20),
                        "description": cls._generate_random_string(200),
                        "price": round(random.uniform(10, 1000), 2),
                        "category_id": random.randint(1, 100),
                        "attributes": {
                            f"attr_{k}": cls._generate_random_string(15) for k in range(random.randint(5, 15))
                        },
                        "reviews": [
                            {
                                "user_id": str(uuid.uuid4()),
                                "rating": random.randint(1, 5),
                                "comment": cls._generate_random_string(150),
                                "timestamp": (datetime.now() - timedelta(days=random.randint(0, 365))).isoformat(),
                                "helpful_votes": random.randint(0, 100)
                            } for _ in range(random.randint(0, 20))
                        ]
                    } for _ in range(2000)
                ],
                "orders": [
                    {
                        "id": str(uuid.uuid4()),
                        "user_id": str(uuid.uuid4()),
                        "items": [
                            {
                                "product_id": str(uuid.uuid4()),
                                "quantity": random.randint(1, 5),
                                "price": round(random.uniform(10, 500), 2)
                            } for _ in range(random.randint(1, 10))
                        ],
                        "total_amount": round(random.uniform(50, 2000), 2),
                        "status": random.choice(["pending", "processing", "shipped", "delivered", "cancelled"]),
                        "created_at": (datetime.now() - timedelta(days=random.randint(0, 90))).isoformat(),
                        "shipping_address": {
                            "street": cls._generate_random_string(30),
                            "city": cls._generate_random_string(15),
                            "state": cls._generate_random_string(10),
                            "zip_code": cls._generate_random_string(8),
                            "country": random.choice(["US", "CN", "UK", "DE", "JP"])
                        }
                    } for _ in range(5000)
                ],
                "metadata": {
                    "total_users": 10000,
                    "total_products": 2000,
                    "total_orders": 5000,
                    "generated_at": datetime.now().isoformat(),
                    "version": "1.0",
                    "performance_hints": {
                        "recommended_chunk_size": 1000,
                        "parallel_processing": True,
                        "memory_optimization": True
                    }
                }
            }
        
        metadata = DatasetMetadata(
            name="large_json_dataset",
            description="大规模JSON数据集，包含10000个复杂用户档案、产品和订单数据",
            size=DatasetSize.LARGE,
            complexity=ComplexityLevel.COMPLEX,
            expected_memory_mb=50.0,
            expected_parse_time_ms=500.0,
            expected_completion_time_ms=250.0,
            record_count=17000,
            avg_record_size_bytes=1500,
            max_nesting_depth=7,
            schema_complexity_score=8.5,
            tags=["users", "products", "orders", "complex", "ecommerce"]
        )
        
        return BenchmarkDataset(
            metadata=metadata,
            data=generator(),
            generator_func=generator
        )
    
    @classmethod
    def generate_xlarge_dataset(cls) -> BenchmarkDataset:
        """生成超大规模数据集 (100000条记录)"""
        def generator():
            return {
                "users": [cls._generate_user_profile(ComplexityLevel.EXTREME) for _ in range(100000)],
                "events": [
                    {
                        "id": str(uuid.uuid4()),
                        "user_id": str(uuid.uuid4()),
                        "event_type": random.choice(["page_view", "click", "purchase", "signup", "logout"]),
                        "timestamp": (datetime.now() - timedelta(seconds=random.randint(0, 86400*30))).isoformat(),
                        "properties": {
                            f"prop_{m}": cls._generate_random_string(20) for m in range(random.randint(10, 30))
                        },
                        "session_data": {
                            "session_id": str(uuid.uuid4()),
                            "duration": random.randint(60, 7200),
                            "page_count": random.randint(1, 50),
                            "referrer": cls._generate_random_string(50),
                            "user_agent": cls._generate_random_string(100),
                            "device_info": {
                                "type": random.choice(["desktop", "mobile", "tablet"]),
                                "os": random.choice(["Windows", "macOS", "Linux", "iOS", "Android"]),
                                "browser": random.choice(["Chrome", "Firefox", "Safari", "Edge"]),
                                "screen_resolution": f"{random.choice([1920, 1366, 1440, 2560])}x{random.choice([1080, 768, 900, 1440])}"
                            }
                        }
                    } for _ in range(500000)
                ],
                "metadata": {
                    "total_users": 100000,
                    "total_events": 500000,
                    "generated_at": datetime.now().isoformat(),
                    "version": "1.0",
                    "data_quality": {
                        "completeness_score": 0.95,
                        "accuracy_score": 0.98,
                        "consistency_score": 0.92
                    },
                    "performance_requirements": {
                        "max_memory_mb": 500,
                        "max_parse_time_ms": 5000,
                        "streaming_required": True,
                        "parallel_processing_recommended": True
                    }
                }
            }
        
        metadata = DatasetMetadata(
            name="xlarge_json_dataset",
            description="超大规模JSON数据集，包含100000个极复杂用户档案和500000个事件记录",
            size=DatasetSize.XLARGE,
            complexity=ComplexityLevel.EXTREME,
            expected_memory_mb=500.0,
            expected_parse_time_ms=5000.0,
            expected_completion_time_ms=2500.0,
            record_count=600000,
            avg_record_size_bytes=2500,
            max_nesting_depth=10,
            schema_complexity_score=10.0,
            tags=["users", "events", "extreme", "analytics", "big_data"]
        )
        
        return BenchmarkDataset(
            metadata=metadata,
            data=generator(),
            generator_func=generator
        )


class StreamingDataGenerator:
    """流式解析测试数据生成器"""
    
    @staticmethod
    def generate_chunked_json_stream(data: Dict[str, Any], chunk_sizes: List[int] = None) -> List[str]:
        """将JSON数据分块为流式数据
        
        Args:
            data: 要分块的JSON数据
            chunk_sizes: 自定义分块大小列表，如果为None则使用随机大小
            
        Returns:
            List[str]: 分块后的字符串列表
        """
        json_str = json.dumps(data, ensure_ascii=False)
        
        if chunk_sizes is None:
            # 生成随机分块大小
            chunk_sizes = []
            remaining = len(json_str)
            while remaining > 0:
                max_chunk = min(500, remaining)
                min_chunk = min(50, remaining)
                chunk_size = random.randint(min_chunk, max_chunk)
                chunk_sizes.append(chunk_size)
                remaining -= chunk_size
        
        chunks = []
        start = 0
        for chunk_size in chunk_sizes:
            end = min(start + chunk_size, len(json_str))
            chunks.append(json_str[start:end])
            start = end
            if start >= len(json_str):
                break
        
        return chunks
    
    @staticmethod
    def generate_incomplete_json_chunks() -> List[Tuple[str, bool]]:
        """生成不完整的JSON块用于测试补全功能
        
        Returns:
            List[Tuple[str, bool]]: (json_chunk, is_complete) 元组列表
        """
        test_cases = [
            # 缺少结束括号
            ('{"name": "test", "value": 123', False),
            ('{"users": [{"id": 1, "name": "Alice"}, {"id": 2', False),
            ('[{"a": 1}, {"b": 2', False),
            
            # 缺少引号
            ('{"name: "test", "value": 123}', False),
            ('{"name": "test, "value": 123}', False),
            ('{name: "test", "value": 123}', False),
            
            # 多余的逗号
            ('{"name": "test", "value": 123,}', False),
            ('[{"a": 1}, {"b": 2},]', False),
            
            # 完整的JSON（用于对比）
            ('{"name": "test", "value": 123}', True),
            ('[{"a": 1}, {"b": 2}]', True),
            
            # 复杂嵌套不完整
            ('{"data": {"users": [{"profile": {"name": "test"', False),
            ('{"config": {"settings": {"theme": "dark", "lang":', False),
        ]
        
        return test_cases
    
    @classmethod
    def generate_streaming_benchmark_data(cls) -> BenchmarkDataset:
        """生成流式解析基准测试数据"""
        def generator():
            base_data = JSONDatasetGenerator.generate_medium_dataset().data
            
            return {
                "chunked_streams": {
                    "small_chunks": cls.generate_chunked_json_stream(base_data, [50] * 20),
                    "medium_chunks": cls.generate_chunked_json_stream(base_data, [200] * 10),
                    "large_chunks": cls.generate_chunked_json_stream(base_data, [1000] * 5),
                    "variable_chunks": cls.generate_chunked_json_stream(base_data)
                },
                "incomplete_chunks": cls.generate_incomplete_json_chunks(),
                "edge_cases": {
                    "empty_chunks": ["", " ", "\n", "\t"],
                    "single_char_chunks": list(json.dumps(base_data)[:100]),
                    "malformed_chunks": [
                        '{"invalid": json}',
                        '[1, 2, 3, invalid]',
                        '{"unclosed": "string',
                        'null, undefined, NaN'
                    ]
                },
                "metadata": {
                    "total_chunk_variations": 4,
                    "incomplete_test_cases": len(cls.generate_incomplete_json_chunks()),
                    "edge_case_count": 8,
                    "generated_at": datetime.now().isoformat()
                }
            }
        
        metadata = DatasetMetadata(
            name="streaming_benchmark_data",
            description="流式解析性能测试数据，包含多种分块策略和边缘情况",
            size=DatasetSize.MEDIUM,
            complexity=ComplexityLevel.COMPLEX,
            expected_memory_mb=10.0,
            expected_parse_time_ms=200.0,
            expected_completion_time_ms=150.0,
            record_count=1000,
            avg_record_size_bytes=800,
            max_nesting_depth=5,
            schema_complexity_score=7.0,
            tags=["streaming", "chunked", "incomplete", "edge_cases"]
        )
        
        return BenchmarkDataset(
            metadata=metadata,
            data=generator(),
            generator_func=generator
        )


class SchemaValidationDataGenerator:
    """Schema验证测试数据生成器"""
    
    @staticmethod
    def generate_schema_test_cases() -> Dict[str, Any]:
        """生成Schema验证测试用例"""
        return {
            "valid_schemas": {
                "simple_object": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "age": {"type": "integer", "minimum": 0}
                    },
                    "required": ["name"]
                },
                "nested_object": {
                    "type": "object",
                    "properties": {
                        "user": {
                            "type": "object",
                            "properties": {
                                "profile": {
                                    "type": "object",
                                    "properties": {
                                        "name": {"type": "string"},
                                        "contacts": {
                                            "type": "array",
                                            "items": {"type": "string"}
                                        }
                                    }
                                }
                            }
                        }
                    }
                },
                "array_schema": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "id": {"type": "integer"},
                            "data": {"type": "string"}
                        }
                    }
                }
            },
            "test_data": {
                "valid_simple": {"name": "Alice", "age": 30},
                "invalid_simple": {"name": 123, "age": -5},
                "valid_nested": {
                    "user": {
                        "profile": {
                            "name": "Bob",
                            "contacts": ["email@test.com", "phone123"]
                        }
                    }
                },
                "invalid_nested": {
                    "user": {
                        "profile": {
                            "name": 456,
                            "contacts": "not_an_array"
                        }
                    }
                },
                "valid_array": [
                    {"id": 1, "data": "test1"},
                    {"id": 2, "data": "test2"}
                ],
                "invalid_array": [
                    {"id": "not_int", "data": "test1"},
                    {"id": 2, "data": 123}
                ]
            }
        }
    
    @classmethod
    def generate_schema_benchmark_data(cls) -> BenchmarkDataset:
        """生成Schema验证基准测试数据"""
        def generator():
            return {
                "schema_validation_cases": cls.generate_schema_test_cases(),
                "performance_schemas": {
                    "deep_nesting": {
                        "type": "object",
                        "properties": {
                            f"level_{i}": {
                                "type": "object",
                                "properties": {
                                    "data": {"type": "string"},
                                    "nested": {"$ref": f"#/properties/level_{i+1}"} if i < 9 else {"type": "null"}
                                }
                            } for i in range(10)
                        }
                    },
                    "large_array": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                f"field_{j}": {"type": "string"} for j in range(50)
                            }
                        },
                        "minItems": 1000,
                        "maxItems": 10000
                    }
                },
                "metadata": {
                    "schema_count": 5,
                    "test_case_count": 6,
                    "max_nesting_depth": 10,
                    "generated_at": datetime.now().isoformat()
                }
            }
        
        metadata = DatasetMetadata(
            name="schema_validation_benchmark",
            description="Schema验证性能测试数据，包含多种复杂度的Schema和测试用例",
            size=DatasetSize.MEDIUM,
            complexity=ComplexityLevel.COMPLEX,
            expected_memory_mb=5.0,
            expected_parse_time_ms=100.0,
            expected_completion_time_ms=80.0,
            record_count=1000,
            avg_record_size_bytes=500,
            max_nesting_depth=10,
            schema_complexity_score=8.0,
            tags=["schema", "validation", "nesting", "performance"]
        )
        
        return BenchmarkDataset(
            metadata=metadata,
            data=generator(),
            generator_func=generator
        )


class PathBuildingDataGenerator:
    """路径构建测试数据生成器"""
    
    @staticmethod
    def generate_path_test_cases() -> Dict[str, Any]:
        """生成路径构建测试用例"""
        return {
            "path_styles": {
                "dot_notation": [
                    "user.name",
                    "user.profile.age",
                    "users[0].name",
                    "data.items[*].value",
                    "config.settings.theme.colors.primary"
                ],
                "slash_notation": [
                    "user/name",
                    "user/profile/age",
                    "users/0/name",
                    "data/items/*/value",
                    "config/settings/theme/colors/primary"
                ],
                "bracket_notation": [
                    "user['name']",
                    "user['profile']['age']",
                    "users[0]['name']",
                    "data['items'][*]['value']",
                    "config['settings']['theme']['colors']['primary']"
                ],
                "mixed_notation": [
                    "user.profile['full_name']",
                    "users[0].contacts['email']",
                    "data.items[*].metadata['tags'][0]"
                ]
            },
            "complex_paths": {
                "deep_nesting": "level1.level2.level3.level4.level5.level6.level7.level8.level9.level10.data",
                "array_heavy": "matrix[0][1][2][3][4].value",
                "mixed_complex": "users[*].profile.contacts['emails'][0].address",
                "special_chars": "data['field-with-dashes']['field_with_underscores']['field with spaces']",
                "numeric_keys": "data['123']['456']['789'].value"
            },
            "edge_cases": {
                "empty_path": "",
                "root_only": "$",
                "single_key": "data",
                "array_only": "[0]",
                "wildcard_only": "[*]",
                "escaped_quotes": "data['field\\'with\\'quotes']",
                "unicode_keys": "数据.用户.姓名"
            }
        }
    
    @classmethod
    def generate_path_benchmark_data(cls) -> BenchmarkDataset:
        """生成路径构建基准测试数据"""
        def generator():
            return {
                "path_test_cases": cls.generate_path_test_cases(),
                "performance_paths": {
                    "bulk_conversion": [
                        f"level{i}.sublevel{j}.item{k}" 
                        for i in range(10) 
                        for j in range(10) 
                        for k in range(10)
                    ],
                    "deep_paths": [
                        ".".join([f"level{i}" for i in range(depth)])
                        for depth in range(1, 21)
                    ],
                    "array_paths": [
                        f"data[{i}].items[{j}].values[{k}]"
                        for i in range(5)
                        for j in range(5)
                        for k in range(5)
                    ]
                },
                "validation_data": {
                    "sample_json": {
                        "users": [
                            {
                                "id": 1,
                                "profile": {
                                    "name": "Alice",
                                    "contacts": {
                                        "emails": [
                                            {"address": "alice@test.com", "primary": True}
                                        ]
                                    }
                                }
                            }
                        ],
                        "config": {
                            "settings": {
                                "theme": {
                                    "colors": {
                                        "primary": "#007bff"
                                    }
                                }
                            }
                        }
                    }
                },
                "metadata": {
                    "path_style_count": 4,
                    "test_case_count": len(cls.generate_path_test_cases()["path_styles"]["dot_notation"]),
                    "performance_path_count": 1000,
                    "generated_at": datetime.now().isoformat()
                }
            }
        
        metadata = DatasetMetadata(
            name="path_building_benchmark",
            description="路径构建性能测试数据，包含多种路径风格和复杂路径",
            size=DatasetSize.MEDIUM,
            complexity=ComplexityLevel.MODERATE,
            expected_memory_mb=3.0,
            expected_parse_time_ms=50.0,
            expected_completion_time_ms=30.0,
            record_count=1000,
            avg_record_size_bytes=200,
            max_nesting_depth=20,
            schema_complexity_score=6.0,
            tags=["paths", "notation", "conversion", "deep_nesting"]
        )
        
        return BenchmarkDataset(
            metadata=metadata,
            data=generator(),
            generator_func=generator
        )


class DiffEngineDataGenerator:
    """差分引擎测试数据生成器"""
    
    @staticmethod
    def generate_diff_test_cases() -> Dict[str, Any]:
        """生成差分测试用例"""
        base_object = {
            "id": 1,
            "name": "Original",
            "data": {
                "values": [1, 2, 3],
                "metadata": {
                    "created": "2024-01-01",
                    "tags": ["tag1", "tag2"]
                }
            }
        }
        
        return {
            "simple_changes": {
                "original": base_object,
                "modified": {
                    **base_object,
                    "name": "Modified",
                    "data": {
                        **base_object["data"],
                        "values": [1, 2, 3, 4]
                    }
                }
            },
            "complex_changes": {
                "original": base_object,
                "modified": {
                    "id": 1,
                    "name": "Completely Changed",
                    "data": {
                        "values": [5, 6, 7, 8, 9],
                        "metadata": {
                            "created": "2024-01-01",
                            "updated": "2024-01-15",
                            "tags": ["tag3", "tag4", "tag5"]
                        },
                        "new_field": "added"
                    },
                    "extra": "field"
                }
            },
            "array_changes": {
                "original": {"items": [1, 2, 3, 4, 5]},
                "modified": {"items": [1, 3, 4, 6, 7, 8]}
            },
            "nested_array_changes": {
                "original": {
                    "users": [
                        {"id": 1, "name": "Alice"},
                        {"id": 2, "name": "Bob"}
                    ]
                },
                "modified": {
                    "users": [
                        {"id": 1, "name": "Alice Updated"},
                        {"id": 3, "name": "Charlie"}
                    ]
                }
            }
        }
    
    @classmethod
    def generate_diff_benchmark_data(cls) -> BenchmarkDataset:
        """生成差分引擎基准测试数据"""
        def generator():
            return {
                "diff_test_cases": cls.generate_diff_test_cases(),
                "performance_diffs": {
                    "large_object_changes": {
                        "original": {
                            f"section_{i}": {
                                f"item_{j}": {
                                    "value": random.randint(1, 1000),
                                    "metadata": {
                                        "timestamp": datetime.now().isoformat(),
                                        "tags": [f"tag_{k}" for k in range(5)]
                                    }
                                } for j in range(20)
                            } for i in range(50)
                        }
                    },
                    "incremental_changes": [
                        {
                            "step": i,
                            "changes": {
                                f"field_{j}": f"value_{i}_{j}" for j in range(i + 1)
                            }
                        } for i in range(100)
                    ]
                },
                "edge_cases": {
                    "empty_to_full": {
                        "original": {},
                        "modified": {"data": "filled"}
                    },
                    "full_to_empty": {
                        "original": {"data": "filled"},
                        "modified": {}
                    },
                    "type_changes": {
                        "original": {"value": "string"},
                        "modified": {"value": 123}
                    },
                    "null_handling": {
                        "original": {"value": None},
                        "modified": {"value": "not_null"}
                    }
                },
                "metadata": {
                    "test_case_count": 4,
                    "performance_object_size": 1000,
                    "incremental_steps": 100,
                    "generated_at": datetime.now().isoformat()
                }
            }
        
        metadata = DatasetMetadata(
            name="diff_engine_benchmark",
            description="差分引擎性能测试数据，包含多种变更类型和复杂度",
            size=DatasetSize.LARGE,
            complexity=ComplexityLevel.COMPLEX,
            expected_memory_mb=20.0,
            expected_parse_time_ms=300.0,
            expected_completion_time_ms=200.0,
            record_count=1000,
            avg_record_size_bytes=1000,
            max_nesting_depth=5,
            schema_complexity_score=7.5,
            tags=["diff", "changes", "incremental", "performance"]
        )
        
        return BenchmarkDataset(
            metadata=metadata,
            data=generator(),
            generator_func=generator
        )


class ModelAdapterDataGenerator:
    """模型适配器测试数据生成器"""
    
    @staticmethod
    def generate_model_test_data() -> Dict[str, Any]:
        """生成模型适配器测试数据"""
        return {
            "model_configs": {
                "openai": {
                    "model_name": "gpt-3.5-turbo",
                    "api_key": "test_key",
                    "base_url": "https://api.openai.com/v1",
                    "timeout": 30,
                    "headers": {"User-Agent": "AgentlyFormat/1.0"}
                },
                "anthropic": {
                    "model_name": "claude-3-sonnet",
                    "api_key": "test_key",
                    "base_url": "https://api.anthropic.com",
                    "timeout": 30,
                    "headers": {"anthropic-version": "2023-06-01"}
                },
                "local": {
                    "model_name": "llama2-7b",
                    "api_key": "",
                    "base_url": "http://localhost:8000",
                    "timeout": 60,
                    "headers": {}
                }
            },
            "test_messages": {
                "simple": [
                    {"role": "user", "content": "Hello, how are you?"}
                ],
                "complex": [
                    {"role": "system", "content": "You are a helpful assistant that responds in JSON format."},
                    {"role": "user", "content": "Generate a user profile with name, age, and preferences."},
                    {"role": "assistant", "content": '{"name": "Alice", "age": 30, "preferences": {"theme": "dark"}}'},
                    {"role": "user", "content": "Now add contact information."}
                ],
                "long_conversation": [
                    {"role": "user", "content": f"Message {i}: {JSONDatasetGenerator._generate_random_string(100)}"}
                    for i in range(50)
                ]
            },
            "response_formats": {
                "streaming_chunks": [
                    'data: {"choices": [{"delta": {"content": "Hello"}}]}\n\n',
                    'data: {"choices": [{"delta": {"content": " there"}}]}\n\n',
                    'data: {"choices": [{"delta": {"content": "!"}}]}\n\n',
                    'data: [DONE]\n\n'
                ],
                "complete_response": {
                    "choices": [
                        {
                            "message": {
                                "role": "assistant",
                                "content": "Hello there!"
                            },
                            "finish_reason": "stop"
                        }
                    ],
                    "usage": {
                        "prompt_tokens": 10,
                        "completion_tokens": 3,
                        "total_tokens": 13
                    }
                }
            }
        }
    
    @classmethod
    def generate_adapter_benchmark_data(cls) -> BenchmarkDataset:
        """生成模型适配器基准测试数据"""
        def generator():
            return {
                "adapter_test_data": cls.generate_model_test_data(),
                "performance_scenarios": {
                    "concurrent_requests": [
                        {
                            "request_id": i,
                            "messages": [
                                {"role": "user", "content": f"Request {i}: {JSONDatasetGenerator._generate_random_string(50)}"}
                            ],
                            "expected_response_time_ms": random.randint(100, 2000)
                        } for i in range(100)
                    ],
                    "large_context": {
                        "messages": [
                            {"role": "user", "content": JSONDatasetGenerator._generate_random_string(10000)}
                        ],
                        "expected_memory_mb": 50,
                        "expected_response_time_ms": 5000
                    },
                    "streaming_performance": {
                        "chunk_count": 1000,
                        "avg_chunk_size": 50,
                        "expected_total_time_ms": 10000,
                        "expected_first_chunk_time_ms": 200
                    }
                },
                "error_scenarios": {
                    "network_errors": [
                        {"type": "timeout", "after_ms": 30000},
                        {"type": "connection_error", "message": "Connection refused"},
                        {"type": "rate_limit", "retry_after": 60}
                    ],
                    "api_errors": [
                        {"status_code": 400, "error": "Bad Request"},
                        {"status_code": 401, "error": "Unauthorized"},
                        {"status_code": 429, "error": "Rate Limited"},
                        {"status_code": 500, "error": "Internal Server Error"}
                    ]
                },
                "metadata": {
                    "model_count": 3,
                    "test_scenario_count": 3,
                    "concurrent_request_count": 100,
                    "generated_at": datetime.now().isoformat()
                }
            }
        
        metadata = DatasetMetadata(
            name="model_adapter_benchmark",
            description="模型适配器性能测试数据，包含多种模型配置和测试场景",
            size=DatasetSize.MEDIUM,
            complexity=ComplexityLevel.MODERATE,
            expected_memory_mb=15.0,
            expected_parse_time_ms=100.0,
            expected_completion_time_ms=80.0,
            record_count=100,
            avg_record_size_bytes=800,
            max_nesting_depth=4,
            schema_complexity_score=5.5,
            tags=["adapters", "models", "concurrent", "streaming"]
        )
        
        return BenchmarkDataset(
            metadata=metadata,
            data=generator(),
            generator_func=generator
        )


class APIPerformanceDataGenerator:
    """API性能测试数据生成器"""
    
    @staticmethod
    def generate_api_test_scenarios() -> Dict[str, Any]:
        """生成API测试场景"""
        return {
            "endpoint_tests": {
                "parse_json": {
                    "method": "POST",
                    "path": "/api/v1/parse",
                    "payload": {
                        "json_data": '{"test": "data"}',
                        "options": {
                            "validate_schema": True,
                            "completion_strategy": "smart"
                        }
                    },
                    "expected_response_time_ms": 100
                },
                "stream_parse": {
                    "method": "POST",
                    "path": "/api/v1/stream/parse",
                    "payload": {
                        "stream_data": True,
                        "chunk_size": 1024
                    },
                    "expected_response_time_ms": 50
                },
                "build_path": {
                    "method": "POST",
                    "path": "/api/v1/path/build",
                    "payload": {
                        "segments": ["user", "profile", "name"],
                        "style": "dot"
                    },
                    "expected_response_time_ms": 10
                }
            },
            "load_test_scenarios": {
                "light_load": {
                    "concurrent_users": 10,
                    "requests_per_second": 50,
                    "duration_seconds": 60,
                    "expected_avg_response_time_ms": 100,
                    "expected_error_rate": 0.01
                },
                "medium_load": {
                    "concurrent_users": 50,
                    "requests_per_second": 200,
                    "duration_seconds": 300,
                    "expected_avg_response_time_ms": 200,
                    "expected_error_rate": 0.05
                },
                "heavy_load": {
                    "concurrent_users": 200,
                    "requests_per_second": 1000,
                    "duration_seconds": 600,
                    "expected_avg_response_time_ms": 500,
                    "expected_error_rate": 0.1
                }
            },
            "stress_test_scenarios": {
                "memory_stress": {
                    "large_payload_size_mb": 100,
                    "concurrent_requests": 20,
                    "expected_memory_usage_mb": 2000,
                    "expected_gc_frequency": 10
                },
                "cpu_stress": {
                    "complex_json_nesting_depth": 20,
                    "concurrent_parsing_tasks": 100,
                    "expected_cpu_usage_percent": 80,
                    "expected_response_time_ms": 1000
                },
                "network_stress": {
                    "slow_network_latency_ms": 1000,
                    "packet_loss_rate": 0.05,
                    "bandwidth_limit_mbps": 1,
                    "expected_timeout_rate": 0.2
                }
            }
        }
    
    @classmethod
    def generate_api_benchmark_data(cls) -> BenchmarkDataset:
        """生成API性能基准测试数据"""
        def generator():
            return {
                "api_test_scenarios": cls.generate_api_test_scenarios(),
                "websocket_scenarios": {
                    "real_time_parsing": {
                        "connection_count": 100,
                        "messages_per_second": 1000,
                        "avg_message_size_bytes": 1024,
                        "expected_latency_ms": 10,
                        "expected_throughput_mbps": 100
                    },
                    "streaming_completion": {
                        "concurrent_streams": 50,
                        "chunk_frequency_hz": 10,
                        "avg_chunk_size_bytes": 256,
                        "expected_completion_time_ms": 5000
                    }
                },
                "benchmark_payloads": {
                    "small_json": json.dumps({"test": "data", "value": 123}),
                    "medium_json": json.dumps(JSONDatasetGenerator.generate_medium_dataset().data),
                    "large_json": json.dumps({
                        "data": [JSONDatasetGenerator._generate_user_profile(ComplexityLevel.COMPLEX) for _ in range(1000)]
                    }),
                    "malformed_json": '{"incomplete": "json"',
                    "empty_json": "",
                    "invalid_json": "not json at all"
                },
                "performance_metrics": {
                    "response_time_percentiles": {
                        "p50": 100,
                        "p90": 200,
                        "p95": 300,
                        "p99": 500
                    },
                    "throughput_targets": {
                        "requests_per_second": 1000,
                        "data_processed_mb_per_second": 50,
                        "concurrent_connections": 500
                    },
                    "resource_limits": {
                        "max_memory_mb": 1000,
                        "max_cpu_percent": 80,
                        "max_disk_io_mbps": 100
                    }
                },
                "metadata": {
                    "endpoint_count": 3,
                    "load_scenario_count": 3,
                    "stress_scenario_count": 3,
                    "websocket_scenario_count": 2,
                    "generated_at": datetime.now().isoformat()
                }
            }
        
        metadata = DatasetMetadata(
            name="api_performance_benchmark",
            description="API性能测试数据，包含多种负载和压力测试场景",
            size=DatasetSize.LARGE,
            complexity=ComplexityLevel.COMPLEX,
            expected_memory_mb=100.0,
            expected_parse_time_ms=1000.0,
            expected_completion_time_ms=800.0,
            record_count=1000,
            avg_record_size_bytes=2000,
            max_nesting_depth=6,
            schema_complexity_score=8.0,
            tags=["api", "load_test", "stress_test", "websocket", "performance"]
        )
        
        return BenchmarkDataset(
            metadata=metadata,
            data=generator(),
            generator_func=generator
        )


# 主要数据集生成函数
def get_all_benchmark_datasets() -> Dict[str, BenchmarkDataset]:
    """获取所有基准测试数据集
    
    Returns:
        Dict[str, BenchmarkDataset]: 数据集名称到数据集对象的映射
    """
    datasets = {
        # JSON数据集
        "small_json": JSONDatasetGenerator.generate_small_dataset(),
        "medium_json": JSONDatasetGenerator.generate_medium_dataset(),
        "large_json": JSONDatasetGenerator.generate_large_dataset(),
        "xlarge_json": JSONDatasetGenerator.generate_xlarge_dataset(),
        
        # 流式解析数据
        "streaming_data": StreamingDataGenerator.generate_streaming_benchmark_data(),
        
        # Schema验证数据
        "schema_validation": SchemaValidationDataGenerator.generate_schema_benchmark_data(),
        
        # 路径构建数据
        "path_building": PathBuildingDataGenerator.generate_path_benchmark_data(),
        
        # 差分引擎数据
        "diff_engine": DiffEngineDataGenerator.generate_diff_benchmark_data(),
        
        # 模型适配器数据
        "model_adapter": ModelAdapterDataGenerator.generate_adapter_benchmark_data(),
        
        # API性能数据
        "api_performance": APIPerformanceDataGenerator.generate_api_benchmark_data()
    }
    
    return datasets


def get_dataset_by_size(size: DatasetSize) -> List[BenchmarkDataset]:
    """根据规模获取数据集
    
    Args:
        size: 数据集规模
        
    Returns:
        List[BenchmarkDataset]: 匹配规模的数据集列表
    """
    all_datasets = get_all_benchmark_datasets()
    return [dataset for dataset in all_datasets.values() if dataset.metadata.size == size]


def get_dataset_by_complexity(complexity: ComplexityLevel) -> List[BenchmarkDataset]:
    """根据复杂度获取数据集
    
    Args:
        complexity: 复杂度级别
        
    Returns:
        List[BenchmarkDataset]: 匹配复杂度的数据集列表
    """
    all_datasets = get_all_benchmark_datasets()
    return [dataset for dataset in all_datasets.values() if dataset.metadata.complexity == complexity]


def get_dataset_by_tags(tags: List[str]) -> List[BenchmarkDataset]:
    """根据标签获取数据集
    
    Args:
        tags: 标签列表
        
    Returns:
        List[BenchmarkDataset]: 包含任一标签的数据集列表
    """
    all_datasets = get_all_benchmark_datasets()
    return [
        dataset for dataset in all_datasets.values() 
        if any(tag in dataset.metadata.tags for tag in tags)
    ]


def generate_performance_report(datasets: List[BenchmarkDataset]) -> Dict[str, Any]:
    """生成性能报告
    
    Args:
        datasets: 数据集列表
        
    Returns:
        Dict[str, Any]: 性能报告
    """
    total_memory = sum(ds.metadata.expected_memory_mb for ds in datasets)
    total_records = sum(ds.metadata.record_count for ds in datasets)
    avg_parse_time = sum(ds.metadata.expected_parse_time_ms for ds in datasets) / len(datasets)
    avg_completion_time = sum(ds.metadata.expected_completion_time_ms for ds in datasets) / len(datasets)
    
    complexity_distribution = {}
    size_distribution = {}
    
    for dataset in datasets:
        complexity = dataset.metadata.complexity.value
        size = dataset.metadata.size.value
        
        complexity_distribution[complexity] = complexity_distribution.get(complexity, 0) + 1
        size_distribution[size] = size_distribution.get(size, 0) + 1
    
    return {
        "summary": {
            "total_datasets": len(datasets),
            "total_memory_mb": total_memory,
            "total_records": total_records,
            "avg_parse_time_ms": avg_parse_time,
            "avg_completion_time_ms": avg_completion_time
        },
        "distributions": {
            "complexity": complexity_distribution,
            "size": size_distribution
        },
        "recommendations": {
            "memory_optimization": total_memory > 100,
            "parallel_processing": total_records > 10000,
            "streaming_required": any(ds.metadata.size == DatasetSize.XLARGE for ds in datasets)
        },
        "generated_at": datetime.now().isoformat()
    }


# 便捷访问函数
def get_small_datasets() -> List[BenchmarkDataset]:
    """获取小规模数据集"""
    return get_dataset_by_size(DatasetSize.SMALL)


def get_medium_datasets() -> List[BenchmarkDataset]:
    """获取中等规模数据集"""
    return get_dataset_by_size(DatasetSize.MEDIUM)


def get_large_datasets() -> List[BenchmarkDataset]:
    """获取大规模数据集"""
    return get_dataset_by_size(DatasetSize.LARGE)


def get_xlarge_datasets() -> List[BenchmarkDataset]:
    """获取超大规模数据集"""
    return get_dataset_by_size(DatasetSize.XLARGE)


def get_simple_datasets() -> List[BenchmarkDataset]:
    """获取简单复杂度数据集"""
    return get_dataset_by_complexity(ComplexityLevel.SIMPLE)


def get_complex_datasets() -> List[BenchmarkDataset]:
    """获取复杂数据集"""
    return get_dataset_by_complexity(ComplexityLevel.COMPLEX)


def get_streaming_datasets() -> List[BenchmarkDataset]:
    """获取流式处理相关数据集"""
    return get_dataset_by_tags(["streaming", "chunked"])


def get_performance_datasets() -> List[BenchmarkDataset]:
    """获取性能测试相关数据集"""
    return get_dataset_by_tags(["performance", "load_test", "stress_test"])


# 数据集元数据汇总
DATASET_METADATA_SUMMARY = {
    "total_datasets": 9,
    "size_categories": {
        "small": 1,
        "medium": 4,
        "large": 3,
        "xlarge": 1
    },
    "complexity_levels": {
        "simple": 1,
        "moderate": 3,
        "complex": 4,
        "extreme": 1
    },
    "feature_coverage": {
        "json_parsing": True,
        "streaming_support": True,
        "schema_validation": True,
        "path_building": True,
        "diff_engine": True,
        "model_adapters": True,
        "api_performance": True
    },
    "performance_expectations": {
        "min_memory_mb": 0.5,
        "max_memory_mb": 500.0,
        "min_parse_time_ms": 5.0,
        "max_parse_time_ms": 5000.0,
        "total_test_records": 600000
    }
}


if __name__ == "__main__":
    """测试数据集生成"""
    print("AgentlyFormat 性能基准测试数据集")
    print("=" * 50)
    
    # 获取所有数据集
    datasets = get_all_benchmark_datasets()
    
    print(f"总数据集数量: {len(datasets)}")
    print("\n数据集详情:")
    
    for name, dataset in datasets.items():
        metadata = dataset.metadata
        print(f"\n{name}:")
        print(f"  描述: {metadata.description}")
        print(f"  规模: {metadata.size.value}")
        print(f"  复杂度: {metadata.complexity.value}")
        print(f"  记录数: {metadata.record_count:,}")
        print(f"  预期内存: {metadata.expected_memory_mb} MB")
        print(f"  预期解析时间: {metadata.expected_parse_time_ms} ms")
        print(f"  标签: {', '.join(metadata.tags)}")
    
    # 生成性能报告
    report = generate_performance_report(list(datasets.values()))
    print("\n性能报告:")
    print(f"  总内存需求: {report['summary']['total_memory_mb']} MB")
    print(f"  总记录数: {report['summary']['total_records']:,}")
    print(f"  平均解析时间: {report['summary']['avg_parse_time_ms']:.2f} ms")
    print(f"  平均补全时间: {report['summary']['avg_completion_time_ms']:.2f} ms")
    
    print("\n数据集生成完成!")