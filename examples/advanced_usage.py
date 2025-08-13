"""高级用法示例

演示AgentlyFormat的高级功能和复杂使用场景。
"""

import asyncio
import json
import time
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass

from agently_format.core.streaming_parser import StreamingParser
from agently_format.core.json_completer import JSONCompleter
from agently_format.core.path_builder import PathBuilder
from agently_format.core.event_system import EventEmitter
from agently_format.types import (
    ParseEvent, ParseEventType, CompletionStrategy,
    PathStyle, ModelConfig, ChatMessage
)
from agently_format.adapters.factory import ModelAdapterFactory


@dataclass
class ProcessingMetrics:
    """处理指标"""
    total_chunks: int = 0
    processed_chunks: int = 0
    total_events: int = 0
    processing_time: float = 0.0
    errors: List[str] = None
    
    def __post_init__(self):
        if self.errors is None:
            self.errors = []


class AdvancedJSONProcessor:
    """高级JSON处理器"""
    
    def __init__(self):
        self.event_emitter = EventEmitter()
        self.streaming_parser = StreamingParser(self.event_emitter)
        self.json_completer = JSONCompleter()
        self.path_builder = PathBuilder()
        self.model_factory = ModelAdapterFactory()
        
        # 处理指标
        self.metrics = ProcessingMetrics()
        
        # 事件监听器
        self._setup_event_listeners()
        
        # 数据缓存
        self.data_cache: Dict[str, Any] = {}
        self.path_cache: Dict[str, List[str]] = {}
    
    def _setup_event_listeners(self):
        """设置事件监听器"""
        self.event_emitter.on('parse_progress', self._on_parse_progress)
        self.event_emitter.on('parse_error', self._on_parse_error)
        self.event_emitter.on('parse_complete', self._on_parse_complete)
    
    def _on_parse_progress(self, event: ParseEvent):
        """解析进度事件处理"""
        self.metrics.total_events += 1
    
    def _on_parse_error(self, event: ParseEvent):
        """解析错误事件处理"""
        error_msg = event.data.get('error', 'Unknown error')
        self.metrics.errors.append(error_msg)
    
    def _on_parse_complete(self, event: ParseEvent):
        """解析完成事件处理"""
        session_id = event.session_id
        data = self.streaming_parser.get_current_data(session_id)
        if data:
            self.data_cache[session_id] = data
    
    async def process_with_ai_completion(
        self,
        incomplete_json: str,
        model_config: Optional[ModelConfig] = None,
        custom_prompt: Optional[str] = None
    ) -> Dict[str, Any]:
        """使用AI模型进行智能JSON补全"""
        print("🤖 使用AI模型进行智能JSON补全...")
        
        # 首先尝试传统补全
        traditional_result = await self.json_completer.complete(
            incomplete_json,
            strategy=CompletionStrategy.SMART
        )
        
        if traditional_result.is_valid and traditional_result.confidence > 0.8:
            print("✅ 传统补全成功，置信度高")
            return {
                "method": "traditional",
                "result": traditional_result.completed_json,
                "confidence": traditional_result.confidence
            }
        
        # 如果传统补全失败或置信度低，使用AI模型
        if model_config:
            try:
                adapter = self.model_factory.create_adapter(model_config)
                
                # 构建AI补全提示
                if custom_prompt:
                    prompt = custom_prompt
                else:
                    prompt = f"""
请帮助补全以下不完整的JSON数据。请确保：
1. 保持原有数据结构和值不变
2. 补全缺失的括号、引号和逗号
3. 确保最终结果是有效的JSON格式
4. 只返回补全后的JSON，不要添加其他说明

不完整的JSON:
{incomplete_json}

补全后的JSON:
"""
                
                messages = [ChatMessage(role="user", content=prompt)]
                
                response = await adapter.chat_completion(
                    messages=messages,
                    stream=False,
                    temperature=0.1,  # 低温度确保一致性
                    max_tokens=2000
                )
                
                # 提取JSON内容
                ai_completed = response.content.strip()
                
                # 尝试解析AI补全的结果
                try:
                    json.loads(ai_completed)
                    print("✅ AI补全成功")
                    return {
                        "method": "ai",
                        "result": ai_completed,
                        "confidence": 0.9,
                        "model": response.model
                    }
                except json.JSONDecodeError:
                    print("❌ AI补全结果无效")
                
                await adapter.close()
                
            except Exception as e:
                print(f"❌ AI补全失败: {e}")
        
        # 回退到传统补全
        print("🔄 回退到传统补全")
        return {
            "method": "fallback",
            "result": traditional_result.completed_json,
            "confidence": traditional_result.confidence
        }
    
    async def intelligent_path_analysis(
        self,
        data: Dict[str, Any],
        analysis_type: str = "comprehensive"
    ) -> Dict[str, Any]:
        """智能路径分析"""
        print(f"🔍 执行智能路径分析 ({analysis_type})...")
        
        # 构建所有路径
        all_paths = self.path_builder.build_paths(
            data,
            style=PathStyle.DOT,
            include_arrays=True
        )
        
        analysis_result = {
            "total_paths": len(all_paths),
            "analysis_type": analysis_type,
            "statistics": {},
            "recommendations": [],
            "patterns": []
        }
        
        if analysis_type == "comprehensive":
            # 深度分析
            analysis_result.update(await self._comprehensive_path_analysis(data, all_paths))
        elif analysis_type == "performance":
            # 性能分析
            analysis_result.update(await self._performance_path_analysis(data, all_paths))
        elif analysis_type == "structure":
            # 结构分析
            analysis_result.update(await self._structure_path_analysis(data, all_paths))
        
        return analysis_result
    
    async def _comprehensive_path_analysis(
        self,
        data: Dict[str, Any],
        paths: List[str]
    ) -> Dict[str, Any]:
        """综合路径分析"""
        # 统计不同类型的路径
        object_paths = [p for p in paths if not '[' in p]
        array_paths = [p for p in paths if '[' in p]
        
        # 分析嵌套深度
        max_depth = max(len(p.split('.')) for p in paths) if paths else 0
        avg_depth = sum(len(p.split('.')) for p in paths) / len(paths) if paths else 0
        
        # 分析数据类型分布
        type_distribution = {}
        for path in paths:
            try:
                value = self.path_builder.get_value_by_path(data, path)
                value_type = type(value).__name__
                type_distribution[value_type] = type_distribution.get(value_type, 0) + 1
            except:
                continue
        
        return {
            "statistics": {
                "object_paths": len(object_paths),
                "array_paths": len(array_paths),
                "max_depth": max_depth,
                "average_depth": round(avg_depth, 2),
                "type_distribution": type_distribution
            },
            "recommendations": [
                "考虑使用索引优化深层嵌套访问" if max_depth > 5 else "结构深度合理",
                "建议缓存频繁访问的路径" if len(paths) > 100 else "路径数量适中",
                "考虑数据扁平化" if len(array_paths) > len(object_paths) else "对象结构良好"
            ]
        }
    
    async def _performance_path_analysis(
        self,
        data: Dict[str, Any],
        paths: List[str]
    ) -> Dict[str, Any]:
        """性能路径分析"""
        # 测试路径访问性能
        start_time = time.time()
        
        access_times = []
        for path in paths[:50]:  # 测试前50个路径
            path_start = time.time()
            try:
                self.path_builder.get_value_by_path(data, path)
                access_times.append(time.time() - path_start)
            except:
                continue
        
        total_time = time.time() - start_time
        
        return {
            "statistics": {
                "total_access_time": round(total_time, 4),
                "average_access_time": round(sum(access_times) / len(access_times), 6) if access_times else 0,
                "fastest_access": round(min(access_times), 6) if access_times else 0,
                "slowest_access": round(max(access_times), 6) if access_times else 0
            },
            "recommendations": [
                "性能良好" if total_time < 0.1 else "考虑优化数据结构",
                "访问速度均匀" if len(set(round(t, 4) for t in access_times)) < 5 else "存在性能瓶颈"
            ]
        }
    
    async def _structure_path_analysis(
        self,
        data: Dict[str, Any],
        paths: List[str]
    ) -> Dict[str, Any]:
        """结构路径分析"""
        # 分析路径模式
        patterns = {}
        for path in paths:
            parts = path.split('.')
            if len(parts) >= 2:
                pattern = '.'.join(parts[:2])  # 取前两级作为模式
                patterns[pattern] = patterns.get(pattern, 0) + 1
        
        # 找出最常见的模式
        common_patterns = sorted(patterns.items(), key=lambda x: x[1], reverse=True)[:5]
        
        return {
            "patterns": [f"{pattern} (出现{count}次)" for pattern, count in common_patterns],
            "statistics": {
                "unique_patterns": len(patterns),
                "most_common_pattern": common_patterns[0][0] if common_patterns else None
            },
            "recommendations": [
                "结构模式清晰" if len(patterns) < 10 else "考虑重构复杂结构",
                "数据组织良好" if common_patterns and common_patterns[0][1] > 5 else "结构较为分散"
            ]
        }
    
    async def adaptive_streaming_processing(
        self,
        data_source: Callable[[], List[str]],
        session_id: str,
        adaptive_config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """自适应流式处理"""
        print(f"🔄 开始自适应流式处理 (会话: {session_id})...")
        
        # 创建解析会话
        self.streaming_parser.create_session(session_id)
        
        config = adaptive_config or {
            "chunk_size_adjustment": True,
            "error_recovery": True,
            "performance_monitoring": True,
            "dynamic_buffering": True
        }
        
        chunks = data_source()
        self.metrics.total_chunks = len(chunks)
        
        start_time = time.time()
        buffer = ""
        chunk_sizes = []
        processing_times = []
        
        for i, chunk in enumerate(chunks):
            chunk_start = time.time()
            
            # 动态缓冲
            if config.get("dynamic_buffering"):
                buffer += chunk
                
                # 根据性能调整处理策略
                if len(processing_times) > 5:
                    avg_time = sum(processing_times[-5:]) / 5
                    if avg_time > 0.1:  # 如果处理时间过长
                        # 增加缓冲区大小，减少处理频率
                        if len(buffer) < 1000:
                            continue
                
                process_chunk = buffer
                buffer = ""
            else:
                process_chunk = chunk
            
            try:
                # 处理块
                events = await self.streaming_parser.parse_chunk(
                    chunk=process_chunk,
                    session_id=session_id,
                    is_final=(i == len(chunks) - 1)
                )
                
                self.metrics.processed_chunks += 1
                
                # 记录性能指标
                chunk_time = time.time() - chunk_start
                processing_times.append(chunk_time)
                chunk_sizes.append(len(process_chunk))
                
                # 自适应调整
                if config.get("chunk_size_adjustment") and len(processing_times) > 3:
                    # 根据处理时间调整策略
                    recent_avg = sum(processing_times[-3:]) / 3
                    if recent_avg > 0.2:  # 处理时间过长
                        print(f"⚡ 检测到性能下降，调整处理策略")
                
                # 错误恢复
                state = self.streaming_parser.get_session_state(session_id)
                if state and state.errors and config.get("error_recovery"):
                    print(f"🔧 检测到错误，尝试恢复: {state.errors}")
                    # 可以在这里实现错误恢复逻辑
                
            except Exception as e:
                if config.get("error_recovery"):
                    print(f"🚨 处理异常，跳过当前块: {e}")
                    self.metrics.errors.append(str(e))
                    continue
                else:
                    raise
        
        # 处理剩余缓冲区
        if buffer and config.get("dynamic_buffering"):
            events = await self.streaming_parser.parse_chunk(
                chunk=buffer,
                session_id=session_id,
                is_final=True
            )
        
        self.metrics.processing_time = time.time() - start_time
        
        # 生成处理报告
        return {
            "session_id": session_id,
            "metrics": {
                "total_chunks": self.metrics.total_chunks,
                "processed_chunks": self.metrics.processed_chunks,
                "processing_time": round(self.metrics.processing_time, 3),
                "average_chunk_time": round(sum(processing_times) / len(processing_times), 4) if processing_times else 0,
                "throughput": round(self.metrics.processed_chunks / self.metrics.processing_time, 2) if self.metrics.processing_time > 0 else 0,
                "error_count": len(self.metrics.errors)
            },
            "performance": {
                "chunk_sizes": {
                    "min": min(chunk_sizes) if chunk_sizes else 0,
                    "max": max(chunk_sizes) if chunk_sizes else 0,
                    "average": round(sum(chunk_sizes) / len(chunk_sizes), 1) if chunk_sizes else 0
                },
                "processing_times": {
                    "min": round(min(processing_times), 4) if processing_times else 0,
                    "max": round(max(processing_times), 4) if processing_times else 0,
                    "average": round(sum(processing_times) / len(processing_times), 4) if processing_times else 0
                }
            },
            "final_data": self.streaming_parser.get_current_data(session_id),
            "errors": self.metrics.errors
        }


async def ai_completion_example():
    """AI智能补全示例"""
    print("=== AI智能补全示例 ===")
    
    processor = AdvancedJSONProcessor()
    
    # 复杂的不完整JSON
    incomplete_json = '''
    {
        "application": {
            "name": "DataAnalyzer",
            "version": "2.0.0",
            "features": [
                {
                    "name": "data_processing",
                    "enabled": true,
                    "config": {
                        "batch_size": 1000,
                        "timeout": 30,
                        "retry_count": 3,
                        "processors": [
                            {"type": "json", "priority": 1},
                            {"type": "csv", "priority": 2
    '''
    
    print(f"原始不完整JSON (长度: {len(incomplete_json)} 字符)")
    print(f"预览: {incomplete_json[:100]}...")
    
    # 模拟模型配置（实际使用时需要真实的API密钥）
    model_config = ModelConfig(
        model_type="openai",
        model_name="gpt-3.5-turbo",
        api_key="mock-api-key"  # 在实际使用中替换为真实密钥
    )
    
    try:
        result = await processor.process_with_ai_completion(
            incomplete_json=incomplete_json,
            model_config=model_config
        )
        
        print(f"\n补全结果:")
        print(f"  方法: {result['method']}")
        print(f"  置信度: {result['confidence']:.2f}")
        
        if result['method'] == 'ai':
            print(f"  使用模型: {result.get('model', 'Unknown')}")
        
        # 验证补全结果
        try:
            completed_data = json.loads(result['result'])
            print(f"  ✅ 补全成功，数据有效")
            print(f"  应用名称: {completed_data.get('application', {}).get('name', 'Unknown')}")
            print(f"  功能数量: {len(completed_data.get('application', {}).get('features', []))}")
        except json.JSONDecodeError:
            print(f"  ❌ 补全结果无效")
    
    except Exception as e:
        print(f"AI补全示例失败: {e}")
        print("提示: 需要有效的API密钥才能使用AI补全功能")


async def intelligent_analysis_example():
    """智能分析示例"""
    print("\n=== 智能分析示例 ===")
    
    processor = AdvancedJSONProcessor()
    
    # 复杂的测试数据
    complex_data = {
        "system": {
            "name": "DataPlatform",
            "version": "3.1.0",
            "components": [
                {
                    "id": "comp-001",
                    "name": "DataIngestion",
                    "type": "service",
                    "config": {
                        "sources": ["kafka", "rabbitmq", "http"],
                        "batch_size": 1000,
                        "timeout": 30,
                        "retry_policy": {
                            "max_retries": 3,
                            "backoff_factor": 2,
                            "retry_codes": [500, 502, 503]
                        }
                    },
                    "metrics": {
                        "throughput": [100, 150, 200, 180, 220],
                        "latency": [10, 15, 12, 18, 14],
                        "error_rate": [0.01, 0.02, 0.015, 0.025, 0.018]
                    }
                },
                {
                    "id": "comp-002",
                    "name": "DataProcessing",
                    "type": "worker",
                    "config": {
                        "workers": 10,
                        "queue_size": 5000,
                        "processing_timeout": 60
                    },
                    "metrics": {
                        "processed_items": [500, 600, 550, 700, 650],
                        "processing_time": [2.5, 3.1, 2.8, 3.5, 3.0],
                        "memory_usage": [512, 600, 580, 650, 620]
                    }
                }
            ],
            "global_config": {
                "logging": {
                    "level": "INFO",
                    "format": "json",
                    "outputs": ["console", "file", "elasticsearch"]
                },
                "monitoring": {
                    "enabled": True,
                    "interval": 60,
                    "metrics": ["cpu", "memory", "disk", "network"]
                }
            }
        }
    }
    
    print(f"分析复杂数据结构 (大小: {len(json.dumps(complex_data))} 字符)")
    
    # 执行不同类型的分析
    analysis_types = ["comprehensive", "performance", "structure"]
    
    for analysis_type in analysis_types:
        print(f"\n--- {analysis_type.upper()} 分析 ---")
        
        result = await processor.intelligent_path_analysis(
            data=complex_data,
            analysis_type=analysis_type
        )
        
        print(f"总路径数: {result['total_paths']}")
        
        if "statistics" in result:
            stats = result["statistics"]
            print(f"统计信息:")
            for key, value in stats.items():
                print(f"  {key}: {value}")
        
        if "recommendations" in result:
            print(f"建议:")
            for rec in result["recommendations"]:
                print(f"  • {rec}")
        
        if "patterns" in result and result["patterns"]:
            print(f"模式:")
            for pattern in result["patterns"][:3]:  # 显示前3个模式
                print(f"  • {pattern}")


async def adaptive_streaming_example():
    """自适应流式处理示例"""
    print("\n=== 自适应流式处理示例 ===")
    
    processor = AdvancedJSONProcessor()
    
    # 生成测试数据源
    def generate_variable_chunks():
        """生成可变大小的数据块"""
        base_data = {
            "events": [
                {
                    "id": i,
                    "timestamp": f"2024-01-15T{10 + i % 14:02d}:30:00Z",
                    "type": "user_action" if i % 3 == 0 else "system_event",
                    "data": {
                        "user_id": f"user-{i % 100}",
                        "action": f"action-{i % 10}",
                        "metadata": {
                            "source": "web" if i % 2 == 0 else "mobile",
                            "session_id": f"session-{i // 10}",
                            "properties": {
                                "page": f"page-{i % 5}",
                                "duration": i * 10 + 100,
                                "interactions": list(range(i % 5))
                            }
                        }
                    }
                }
                for i in range(50)  # 50个事件
            ]
        }
        
        json_str = json.dumps(base_data, ensure_ascii=False)
        
        # 创建可变大小的块
        chunks = []
        i = 0
        while i < len(json_str):
            # 随机块大小，模拟网络传输的不确定性
            chunk_size = 100 + (i % 200)  # 100-300字符
            chunk = json_str[i:i + chunk_size]
            chunks.append(chunk)
            i += chunk_size
        
        return chunks
    
    # 配置自适应处理
    adaptive_config = {
        "chunk_size_adjustment": True,
        "error_recovery": True,
        "performance_monitoring": True,
        "dynamic_buffering": True
    }
    
    print(f"配置自适应处理:")
    for key, value in adaptive_config.items():
        print(f"  {key}: {'✅' if value else '❌'}")
    
    # 执行自适应处理
    session_id = "adaptive-demo"
    
    result = await processor.adaptive_streaming_processing(
        data_source=generate_variable_chunks,
        session_id=session_id,
        adaptive_config=adaptive_config
    )
    
    print(f"\n处理结果:")
    print(f"会话ID: {result['session_id']}")
    
    metrics = result['metrics']
    print(f"\n处理指标:")
    print(f"  总块数: {metrics['total_chunks']}")
    print(f"  已处理: {metrics['processed_chunks']}")
    print(f"  处理时间: {metrics['processing_time']}秒")
    print(f"  吞吐量: {metrics['throughput']} 块/秒")
    print(f"  错误数: {metrics['error_count']}")
    
    performance = result['performance']
    print(f"\n性能分析:")
    print(f"  块大小范围: {performance['chunk_sizes']['min']}-{performance['chunk_sizes']['max']} 字符")
    print(f"  平均块大小: {performance['chunk_sizes']['average']} 字符")
    print(f"  处理时间范围: {performance['processing_times']['min']}-{performance['processing_times']['max']}秒")
    print(f"  平均处理时间: {performance['processing_times']['average']}秒")
    
    # 验证最终数据
    final_data = result['final_data']
    if final_data:
        print(f"\n数据验证:")
        print(f"  事件数量: {len(final_data.get('events', []))}")
        print(f"  数据完整性: ✅")
    
    if result['errors']:
        print(f"\n错误信息:")
        for error in result['errors'][:3]:  # 显示前3个错误
            print(f"  • {error}")


async def integration_workflow_example():
    """集成工作流示例"""
    print("\n=== 集成工作流示例 ===")
    
    processor = AdvancedJSONProcessor()
    
    # 模拟复杂的数据处理工作流
    workflow_data = {
        "pipeline": {
            "id": "data-pipeline-001",
            "name": "CustomerDataProcessing",
            "stages": [
                {
                    "stage_id": "ingestion",
                    "type": "data_source",
                    "config": {
                        "source_type": "api",
                        "endpoint": "https://api.example.com/customers",
                        "batch_size": 1000,
                        "rate_limit": 100
                    },
                    "output_schema": {
                        "customer_id": "string",
                        "name": "string",
                        "email": "string",
                        "created_at": "datetime"
                    }
                },
                {
                    "stage_id": "validation",
                    "type": "data_quality",
                    "config": {
                        "rules": [
                            {"field": "email", "type": "email_format"},
                            {"field": "customer_id", "type": "not_null"},
                            {"field": "name", "type": "min_length", "value": 2}
                        ],
                        "error_threshold": 0.05
                    }
                },
                {
                    "stage_id": "enrichment",
                    "type": "data_enhancement",
                    "config": {
                        "enrichment_sources": [
                            {"type": "geo_location", "field": "ip_address"},
                            {"type": "demographic", "field": "postal_code"}
                        ]
                    }
                }
            ]
        }
    }
    
    print(f"工作流: {workflow_data['pipeline']['name']}")
    print(f"阶段数: {len(workflow_data['pipeline']['stages'])}")
    
    # 1. 路径分析
    print(f"\n步骤1: 路径分析")
    path_analysis = await processor.intelligent_path_analysis(
        data=workflow_data,
        analysis_type="comprehensive"
    )
    
    print(f"  发现 {path_analysis['total_paths']} 个数据路径")
    print(f"  最大嵌套深度: {path_analysis['statistics']['max_depth']}")
    
    # 2. 数据序列化和分块
    print(f"\n步骤2: 数据序列化")
    json_str = json.dumps(workflow_data, ensure_ascii=False)
    chunks = [json_str[i:i+200] for i in range(0, len(json_str), 200)]
    
    print(f"  原始大小: {len(json_str)} 字符")
    print(f"  分块数量: {len(chunks)}")
    
    # 3. 流式处理
    print(f"\n步骤3: 流式处理")
    
    def chunk_generator():
        return chunks
    
    streaming_result = await processor.adaptive_streaming_processing(
        data_source=chunk_generator,
        session_id="workflow-demo",
        adaptive_config={
            "chunk_size_adjustment": True,
            "error_recovery": True,
            "performance_monitoring": True,
            "dynamic_buffering": False  # 禁用缓冲以确保实时处理
        }
    )
    
    print(f"  处理时间: {streaming_result['metrics']['processing_time']}秒")
    print(f"  吞吐量: {streaming_result['metrics']['throughput']} 块/秒")
    
    # 4. 结果验证
    print(f"\n步骤4: 结果验证")
    final_data = streaming_result['final_data']
    
    if final_data:
        # 验证数据完整性
        original_stages = len(workflow_data['pipeline']['stages'])
        processed_stages = len(final_data.get('pipeline', {}).get('stages', []))
        
        print(f"  原始阶段数: {original_stages}")
        print(f"  处理后阶段数: {processed_stages}")
        print(f"  数据完整性: {'✅ 完整' if original_stages == processed_stages else '❌ 不完整'}")
        
        # 验证特定字段
        pipeline_id = final_data.get('pipeline', {}).get('id')
        print(f"  管道ID: {pipeline_id}")
        
        # 检查配置完整性
        config_paths = []
        for stage in final_data.get('pipeline', {}).get('stages', []):
            if 'config' in stage:
                stage_id = stage.get('stage_id', 'unknown')
                config_paths.append(f"pipeline.stages[{stage_id}].config")
        
        print(f"  配置路径数: {len(config_paths)}")
        
    else:
        print(f"  ❌ 处理失败，无最终数据")
    
    # 5. 性能报告
    print(f"\n步骤5: 性能报告")
    performance = streaming_result['performance']
    
    print(f"  平均块处理时间: {performance['processing_times']['average']}秒")
    print(f"  最快处理时间: {performance['processing_times']['min']}秒")
    print(f"  最慢处理时间: {performance['processing_times']['max']}秒")
    
    efficiency = (streaming_result['metrics']['processed_chunks'] / 
                 streaming_result['metrics']['total_chunks']) * 100
    print(f"  处理效率: {efficiency:.1f}%")
    
    print(f"\n✅ 集成工作流完成")


async def main():
    """主函数 - 运行所有高级用法示例"""
    print("Agently Format - 高级用法示例")
    print("=" * 50)
    
    try:
        await ai_completion_example()
        await intelligent_analysis_example()
        await adaptive_streaming_example()
        await integration_workflow_example()
        
        print("\n=== 所有高级用法示例运行完成 ===")
        print("\n高级功能特性:")
        print("🤖 AI智能补全")
        print("🔍 智能路径分析")
        print("🔄 自适应流式处理")
        print("📊 性能监控和优化")
        print("🛠️ 错误恢复机制")
        print("🔗 集成工作流")
        
        print("\n应用场景:")
        print("• 大规模数据处理")
        print("• 实时数据流分析")
        print("• 复杂JSON结构处理")
        print("• 智能数据补全")
        print("• 性能优化和监控")
        
    except Exception as e:
        print(f"\n运行高级用法示例时发生错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    # 运行示例
    asyncio.run(main())