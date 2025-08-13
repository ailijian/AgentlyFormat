# AgentlyFormat 最佳实践指南

## 📋 目录

1. [概述](#概述)
2. [智能JSON补全最佳实践](#智能json补全最佳实践)
3. [流式JSON解析最佳实践](#流式json解析最佳实践)
4. [数据路径构建最佳实践](#数据路径构建最佳实践)
5. [Schema验证最佳实践](#schema验证最佳实践)
6. [差分引擎最佳实践](#差分引擎最佳实践)
7. [多模型适配器最佳实践](#多模型适配器最佳实践)
8. [综合应用案例](#综合应用案例)
9. [常见问题与解决方案](#常见问题与解决方案)
10. [性能优化建议](#性能优化建议)

---

## 📖 概述

本指南提供AgentlyFormat项目各核心功能的最佳实践案例，通过真实场景和完整代码示例，帮助开发者快速掌握项目的使用方法和核心能力。

### 适用人群
- Python初学者
- 大模型应用开发者
- JSON数据处理工程师
- API服务开发者

### 前置要求
```bash
# 安装AgentlyFormat
pip install AgentlyFormat

# 或开发环境安装
pip install -e ".[dev]"
```

---

## 🔧 智能JSON补全最佳实践

### 应用场景1：处理大模型不完整输出

**场景描述**：ChatGPT等大模型在生成JSON时经常因为token限制或网络问题导致输出不完整。

```python
from agently_format.core.json_completer import JSONCompleter, CompletionStrategy
import json

def handle_incomplete_llm_output():
    """处理大模型不完整JSON输出的最佳实践"""
    completer = JSONCompleter()
    
    # 模拟大模型不完整输出
    incomplete_outputs = [
        '{"users": [{"name": "Alice", "age": 25}, {"name": "Bob"',  # 缺少结束括号
        '{"products": [{"id": 1, "name": "iPhone", "price": 999',    # 缺少字段和括号
        '{"data": {"total": 100, "items": [1, 2, 3',                # 数组未闭合
    ]
    
    for i, incomplete_json in enumerate(incomplete_outputs):
        print(f"\n=== 处理第{i+1}个不完整JSON ===")
        print(f"原始输出: {incomplete_json}")
        
        # 使用智能策略补全
        result = completer.complete(
            incomplete_json, 
            strategy=CompletionStrategy.SMART
        )
        
        if result.is_valid:
            print(f"补全成功: {result.completed_json}")
            print(f"置信度: {result.confidence:.2f}")
            
            # 验证补全结果
            try:
                parsed_data = json.loads(result.completed_json)
                print(f"解析成功: {parsed_data}")
            except json.JSONDecodeError as e:
                print(f"解析失败: {e}")
        else:
            print(f"补全失败: {result.error_message}")
            
            # 尝试保守策略
            conservative_result = completer.complete(
                incomplete_json, 
                strategy=CompletionStrategy.CONSERVATIVE
            )
            if conservative_result.is_valid:
                print(f"保守策略成功: {conservative_result.completed_json}")

# 运行示例
handle_incomplete_llm_output()
```

### 应用场景2：批量数据清洗

**场景描述**：从日志文件或API响应中提取的JSON数据经常格式不完整，需要批量处理。

```python
from agently_format.core.json_completer import JSONCompleter
from typing import List, Dict, Any
import json
import logging

class JSONDataCleaner:
    """JSON数据清洗器"""
    
    def __init__(self):
        self.completer = JSONCompleter()
        self.logger = logging.getLogger(__name__)
    
    def clean_batch(self, json_strings: List[str]) -> Dict[str, Any]:
        """批量清洗JSON数据"""
        results = {
            "success": [],
            "failed": [],
            "statistics": {
                "total": len(json_strings),
                "success_count": 0,
                "failed_count": 0,
                "average_confidence": 0.0
            }
        }
        
        total_confidence = 0.0
        
        for i, json_str in enumerate(json_strings):
            try:
                # 尝试补全
                completion_result = self.completer.complete(json_str)
                
                if completion_result.is_valid:
                    # 验证JSON格式
                    parsed_data = json.loads(completion_result.completed_json)
                    
                    results["success"].append({
                        "index": i,
                        "original": json_str,
                        "completed": completion_result.completed_json,
                        "parsed_data": parsed_data,
                        "confidence": completion_result.confidence
                    })
                    
                    total_confidence += completion_result.confidence
                    results["statistics"]["success_count"] += 1
                    
                else:
                    results["failed"].append({
                        "index": i,
                        "original": json_str,
                        "error": completion_result.error_message
                    })
                    results["statistics"]["failed_count"] += 1
                    
            except Exception as e:
                self.logger.error(f"处理第{i}个JSON时出错: {e}")
                results["failed"].append({
                    "index": i,
                    "original": json_str,
                    "error": str(e)
                })
                results["statistics"]["failed_count"] += 1
        
        # 计算平均置信度
        if results["statistics"]["success_count"] > 0:
            results["statistics"]["average_confidence"] = (
                total_confidence / results["statistics"]["success_count"]
            )
        
        return results

# 使用示例
def demo_batch_cleaning():
    """演示批量清洗功能"""
    cleaner = JSONDataCleaner()
    
    # 模拟从日志中提取的不完整JSON
    dirty_jsons = [
        '{"user_id": 123, "action": "login"',
        '{"product": {"id": 456, "name": "Laptop"',
        '{"order": {"total": 299.99, "items": [',
        'invalid json string',
        '{"status": "success", "data": {"count": 10}}',  # 完整的JSON
    ]
    
    results = cleaner.clean_batch(dirty_jsons)
    
    print("=== 批量清洗结果 ===")
    print(f"总数: {results['statistics']['total']}")
    print(f"成功: {results['statistics']['success_count']}")
    print(f"失败: {results['statistics']['failed_count']}")
    print(f"平均置信度: {results['statistics']['average_confidence']:.2f}")
    
    print("\n=== 成功案例 ===")
    for item in results["success"]:
        print(f"索引{item['index']}: {item['completed']}")
    
    print("\n=== 失败案例 ===")
    for item in results["failed"]:
        print(f"索引{item['index']}: {item['error']}")

# 运行演示
demo_batch_cleaning()
```

### 常见问题解决

**问题1：补全结果置信度低**
```python
def handle_low_confidence():
    """处理低置信度补全结果"""
    completer = JSONCompleter()
    
    incomplete_json = '{"complex": {"nested": {"data"'
    result = completer.complete(incomplete_json)
    
    if result.is_valid and result.confidence < 0.7:
        print("置信度较低，尝试不同策略")
        
        # 尝试保守策略
        conservative_result = completer.complete(
            incomplete_json, 
            strategy=CompletionStrategy.CONSERVATIVE
        )
        
        if conservative_result.confidence > result.confidence:
            print(f"保守策略更好: {conservative_result.completed_json}")
            return conservative_result
    
    return result
```

**问题2：处理特殊字符**
```python
def handle_special_characters():
    """处理包含特殊字符的JSON"""
    completer = JSONCompleter()
    
    # 包含特殊字符的不完整JSON
    special_json = '{"message": "Hello\nWorld", "emoji": "😀"'
    
    result = completer.complete(special_json)
    
    if result.is_valid:
        # 验证特殊字符是否正确处理
        parsed = json.loads(result.completed_json)
        print(f"消息: {parsed['message']}")
        print(f"表情: {parsed['emoji']}")
    
    return result
```

---

## 🌊 流式JSON解析最佳实践

### 应用场景1：实时处理大模型流式输出

**场景描述**：处理ChatGPT、Claude等大模型的流式JSON响应，实时解析并展示结果。

```python
import asyncio
from agently_format.core.streaming_parser import StreamingParser
from agently_format.core.event_system import get_global_emitter, EventType
import json

class RealTimeJSONProcessor:
    """实时JSON处理器"""
    
    def __init__(self):
        self.parser = StreamingParser()
        self.emitter = get_global_emitter()
        self.setup_event_handlers()
    
    def setup_event_handlers(self):
        """设置事件处理器"""
        @self.emitter.on(EventType.DELTA)
        async def on_parse_progress(event):
            print(f"解析进度: {event.data}")
        
        @self.emitter.on(EventType.ERROR)
        async def on_parse_error(event):
            print(f"解析错误: {event.data}")
        
        @self.emitter.on(EventType.COMPLETE)
        async def on_parse_complete(event):
            print(f"解析完成: {event.data}")
    
    async def process_llm_stream(self, chunks):
        """处理大模型流式输出"""
        session_id = self.parser.create_session()
        
        try:
            for i, chunk in enumerate(chunks):
                print(f"\n--- 处理块 {i+1}/{len(chunks)} ---")
                print(f"接收到: {chunk}")
                
                # 解析当前块
                result = await self.parser.parse_chunk(
                    session_id=session_id,
                    chunk=chunk
                )
                
                # 获取当前解析状态
                state = self.parser.parsing_states.get(session_id)
                if state and state.current_data:
                    print(f"当前数据: {json.dumps(state.current_data, ensure_ascii=False, indent=2)}")
                
                # 检查是否有完整对象
                if result and hasattr(result, 'parsed_objects'):
                    for obj in result.parsed_objects:
                        print(f"完整对象: {obj}")
            
            # 获取最终结果
            final_data = self.parser.get_current_data(session_id)
            print(f"\n=== 最终结果 ===")
            print(json.dumps(final_data, ensure_ascii=False, indent=2))
            
            return final_data
            
        finally:
            # 清理会话
            self.parser.cleanup_session(session_id)

# 模拟大模型流式输出
async def simulate_llm_streaming():
    """模拟大模型流式输出"""
    processor = RealTimeJSONProcessor()
    
    # 模拟分块接收的JSON数据
    chunks = [
        '{"response": {',
        '"users": [',
        '{"id": 1, "name": "Alice", "age": 25},',
        '{"id": 2, "name": "Bob", "age": 30}',
        '],',
        '"total": 2,',
        '"status": "success"',
        '}}'
    ]
    
    print("开始处理流式JSON数据...")
    result = await processor.process_llm_stream(chunks)
    
    return result

# 运行示例
asyncio.run(simulate_llm_streaming())
```

### 应用场景2：处理大文件JSON流

**场景描述**：处理大型JSON文件的流式读取，避免内存溢出。

```python
import asyncio
import aiofiles
from agently_format.core.streaming_parser import StreamingParser
from typing import AsyncGenerator

class LargeFileProcessor:
    """大文件流式处理器"""
    
    def __init__(self, chunk_size: int = 8192):
        self.parser = StreamingParser()
        self.chunk_size = chunk_size
    
    async def read_file_chunks(self, file_path: str) -> AsyncGenerator[str, None]:
        """异步读取文件块"""
        async with aiofiles.open(file_path, 'r', encoding='utf-8') as file:
            while True:
                chunk = await file.read(self.chunk_size)
                if not chunk:
                    break
                yield chunk
    
    async def process_large_json_file(self, file_path: str):
        """处理大型JSON文件"""
        session_id = self.parser.create_session()
        processed_objects = []
        
        try:
            print(f"开始处理文件: {file_path}")
            
            async for chunk in self.read_file_chunks(file_path):
                result = await self.parser.parse_chunk(
                    session_id=session_id,
                    chunk=chunk
                )
                
                # 处理完整的对象
                if result and hasattr(result, 'parsed_objects'):
                    for obj in result.parsed_objects:
                        processed_objects.append(obj)
                        print(f"处理了对象: {len(processed_objects)}")
                        
                        # 可以在这里进行实时处理
                        await self.process_single_object(obj)
            
            # 获取最终数据
            final_data = self.parser.get_current_data(session_id)
            
            return {
                "processed_objects": processed_objects,
                "final_data": final_data,
                "total_count": len(processed_objects)
            }
            
        finally:
            self.parser.cleanup_session(session_id)
    
    async def process_single_object(self, obj):
        """处理单个对象"""
        # 这里可以添加具体的业务逻辑
        # 例如：数据验证、转换、存储等
        if isinstance(obj, dict) and 'id' in obj:
            print(f"处理ID为 {obj['id']} 的对象")

# 创建测试文件
async def create_test_file():
    """创建测试用的大JSON文件"""
    test_data = {
        "users": [
            {"id": i, "name": f"User{i}", "email": f"user{i}@example.com"}
            for i in range(1000)  # 1000个用户
        ],
        "metadata": {
            "total": 1000,
            "created_at": "2024-01-01T00:00:00Z"
        }
    }
    
    async with aiofiles.open("large_test.json", 'w', encoding='utf-8') as file:
        await file.write(json.dumps(test_data, ensure_ascii=False))
    
    print("测试文件创建完成: large_test.json")

# 使用示例
async def demo_large_file_processing():
    """演示大文件处理"""
    # 创建测试文件
    await create_test_file()
    
    # 处理文件
    processor = LargeFileProcessor(chunk_size=1024)  # 1KB块
    result = await processor.process_large_json_file("large_test.json")
    
    print(f"\n=== 处理结果 ===")
    print(f"处理对象数: {result['total_count']}")
    print(f"最终数据键: {list(result['final_data'].keys()) if result['final_data'] else 'None'}")

# 运行演示
asyncio.run(demo_large_file_processing())
```

### 应用场景3：WebSocket实时数据处理

**场景描述**：通过WebSocket接收实时JSON数据流，如股票价格、聊天消息等。

```python
import asyncio
import websockets
import json
from agently_format.core.streaming_parser import StreamingParser
from typing import Dict, Any

class WebSocketJSONHandler:
    """WebSocket JSON处理器"""
    
    def __init__(self):
        self.parser = StreamingParser()
        self.active_sessions: Dict[str, str] = {}  # client_id -> session_id
    
    async def handle_client(self, websocket, path):
        """处理WebSocket客户端连接"""
        client_id = f"client_{id(websocket)}"
        session_id = self.parser.create_session()
        self.active_sessions[client_id] = session_id
        
        print(f"客户端 {client_id} 连接")
        
        try:
            async for message in websocket:
                await self.process_message(client_id, message, websocket)
        
        except websockets.exceptions.ConnectionClosed:
            print(f"客户端 {client_id} 断开连接")
        
        finally:
            # 清理会话
            if client_id in self.active_sessions:
                self.parser.cleanup_session(self.active_sessions[client_id])
                del self.active_sessions[client_id]
    
    async def process_message(self, client_id: str, message: str, websocket):
        """处理接收到的消息"""
        session_id = self.active_sessions[client_id]
        
        try:
            # 解析JSON块
            result = await self.parser.parse_chunk(
                session_id=session_id,
                chunk=message
            )
            
            # 获取当前数据
            current_data = self.parser.get_current_data(session_id)
            
            # 发送解析结果给客户端
            response = {
                "type": "parse_result",
                "client_id": client_id,
                "data": current_data,
                "is_complete": self.is_complete_json(current_data)
            }
            
            await websocket.send(json.dumps(response, ensure_ascii=False))
            
        except Exception as e:
            error_response = {
                "type": "error",
                "client_id": client_id,
                "error": str(e)
            }
            await websocket.send(json.dumps(error_response))
    
    def is_complete_json(self, data) -> bool:
        """检查JSON是否完整"""
        return data is not None and isinstance(data, (dict, list))
    
    async def start_server(self, host="localhost", port=8765):
        """启动WebSocket服务器"""
        print(f"启动WebSocket服务器: ws://{host}:{port}")
        
        async with websockets.serve(self.handle_client, host, port):
            await asyncio.Future()  # 永远运行

# 客户端示例
async def websocket_client_demo():
    """WebSocket客户端演示"""
    uri = "ws://localhost:8765"
    
    # 模拟分块发送的JSON数据
    chunks = [
        '{"stock_data": {',
        '"symbol": "AAPL",',
        '"price": 150.25,',
        '"volume": 1000000',
        '}}'
    ]
    
    async with websockets.connect(uri) as websocket:
        print("连接到WebSocket服务器")
        
        # 发送JSON块
        for i, chunk in enumerate(chunks):
            print(f"发送块 {i+1}: {chunk}")
            await websocket.send(chunk)
            
            # 接收响应
            response = await websocket.recv()
            result = json.loads(response)
            print(f"收到响应: {result}")
            
            await asyncio.sleep(0.5)  # 模拟延迟

# 运行服务器和客户端
async def demo_websocket_processing():
    """演示WebSocket处理"""
    handler = WebSocketJSONHandler()
    
    # 启动服务器（在后台）
    server_task = asyncio.create_task(
        handler.start_server()
    )
    
    # 等待服务器启动
    await asyncio.sleep(1)
    
    # 运行客户端
    try:
        await websocket_client_demo()
    except Exception as e:
        print(f"客户端错误: {e}")
    finally:
        server_task.cancel()

# 注意：这个示例需要在实际环境中运行
# asyncio.run(demo_websocket_processing())
```

### 常见问题解决

**问题1：内存使用过多**
```python
def optimize_memory_usage():
    """优化内存使用"""
    # 设置较小的缓冲区大小
    parser = StreamingParser(
        max_chunk_size=4096,  # 4KB
        session_ttl=300       # 5分钟超时
    )
    
    # 定期清理无用会话
    async def cleanup_sessions():
        while True:
            parser.cleanup_expired_sessions()
            await asyncio.sleep(60)  # 每分钟清理一次
    
    return parser
```

**问题2：处理损坏的JSON块**
```python
async def handle_corrupted_chunks():
    """处理损坏的JSON块"""
    parser = StreamingParser()
    session_id = parser.create_session()
    
    corrupted_chunks = [
        '{"data": [',
        'corrupted_chunk_here',  # 损坏的块
        '1, 2, 3]}'
    ]
    
    for chunk in corrupted_chunks:
        try:
            result = await parser.parse_chunk(session_id, chunk)
            print(f"处理成功: {result}")
        except Exception as e:
            print(f"处理失败: {e}")
            # 可以选择跳过或尝试修复
            continue
```

---

## 🗺️ 数据路径构建最佳实践

### 应用场景1：动态表单生成

**场景描述**：根据JSON Schema动态生成表单，需要提取所有可能的数据路径。

```python
from agently_format.core.path_builder import PathBuilder, PathStyle
from typing import Dict, List, Any
import json

class DynamicFormGenerator:
    """动态表单生成器"""
    
    def __init__(self):
        self.path_builder = PathBuilder()
    
    def generate_form_fields(self, schema_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """根据数据结构生成表单字段"""
        # 提取所有路径
        paths = self.path_builder.extract_parsing_key_orders(schema_data)
        
        form_fields = []
        
        for path in paths:
            # 获取路径对应的值
            success, value = self.path_builder.get_value_at_path(schema_data, path)
            
            if success:
                field_info = self.create_field_info(path, value)
                form_fields.append(field_info)
        
        return form_fields
    
    def create_field_info(self, path: str, value: Any) -> Dict[str, Any]:
        """创建字段信息"""
        field_type = self.determine_field_type(value)
        
        return {
            "path": path,
            "label": self.path_to_label(path),
            "type": field_type,
            "default_value": value,
            "required": value is not None,
            "validation": self.get_validation_rules(field_type, value)
        }
    
    def determine_field_type(self, value: Any) -> str:
        """确定字段类型"""
        if isinstance(value, bool):
            return "checkbox"
        elif isinstance(value, int):
            return "number"
        elif isinstance(value, float):
            return "decimal"
        elif isinstance(value, str):
            if "@" in value:
                return "email"
            elif len(value) > 100:
                return "textarea"
            else:
                return "text"
        elif isinstance(value, list):
            return "multiselect"
        elif isinstance(value, dict):
            return "object"
        else:
            return "text"
    
    def path_to_label(self, path: str) -> str:
        """将路径转换为用户友好的标签"""
        # 移除数组索引
        clean_path = path.replace('[0]', '').replace('[1]', '').replace('[2]', '')
        
        # 分割路径并转换为标题格式
        parts = clean_path.split('.')
        labels = []
        
        for part in parts:
            if part:
                # 转换驼峰命名为空格分隔
                import re
                label = re.sub(r'([A-Z])', r' \1', part).strip()
                label = label.replace('_', ' ').title()
                labels.append(label)
        
        return ' > '.join(labels)
    
    def get_validation_rules(self, field_type: str, value: Any) -> Dict[str, Any]:
        """获取验证规则"""
        rules = {}
        
        if field_type == "email":
            rules["pattern"] = r"^[\w\.-]+@[\w\.-]+\.\w+$"
        elif field_type == "number":
            if isinstance(value, int) and value > 0:
                rules["min"] = 0
        elif field_type == "text":
            if isinstance(value, str) and len(value) > 0:
                rules["minLength"] = 1
                rules["maxLength"] = 255
        
        return rules

# 使用示例
def demo_form_generation():
    """演示动态表单生成"""
    generator = DynamicFormGenerator()
    
    # 示例用户数据结构
    user_schema = {
        "personal_info": {
            "first_name": "John",
            "last_name": "Doe",
            "email": "john.doe@example.com",
            "age": 30,
            "is_active": True
        },
        "address": {
            "street": "123 Main St",
            "city": "New York",
            "zip_code": "10001",
            "country": "USA"
        },
        "preferences": {
            "languages": ["English", "Spanish"],
            "notifications": {
                "email": True,
                "sms": False
            }
        }
    }
    
    # 生成表单字段
    form_fields = generator.generate_form_fields(user_schema)
    
    print("=== 动态生成的表单字段 ===")
    for field in form_fields:
        print(f"路径: {field['path']}")
        print(f"标签: {field['label']}")
        print(f"类型: {field['type']}")
        print(f"默认值: {field['default_value']}")
        print(f"必填: {field['required']}")
        print(f"验证规则: {field['validation']}")
        print("-" * 40)

# 运行演示
demo_form_generation()
```

### 应用场景2：数据映射和转换

**场景描述**：在不同系统间进行数据迁移时，需要建立字段映射关系。

```python
from agently_format.core.path_builder import PathBuilder, PathStyle
from typing import Dict, Any, List, Tuple

class DataMapper:
    """数据映射器"""
    
    def __init__(self):
        self.path_builder = PathBuilder()
        self.mapping_rules: Dict[str, str] = {}
    
    def create_mapping(self, source_data: Dict[str, Any], target_schema: Dict[str, Any]) -> Dict[str, str]:
        """创建源数据到目标结构的映射"""
        source_paths = self.path_builder.extract_parsing_key_orders(source_data)
        target_paths = self.path_builder.extract_parsing_key_orders(target_schema)
        
        mapping = {}
        
        # 智能匹配路径
        for source_path in source_paths:
            best_match = self.find_best_match(source_path, target_paths)
            if best_match:
                mapping[source_path] = best_match
        
        return mapping
    
    def find_best_match(self, source_path: str, target_paths: List[str]) -> str:
        """找到最佳匹配的目标路径"""
        source_parts = source_path.split('.')
        best_score = 0
        best_match = None
        
        for target_path in target_paths:
            target_parts = target_path.split('.')
            score = self.calculate_similarity(source_parts, target_parts)
            
            if score > best_score:
                best_score = score
                best_match = target_path
        
        # 只返回相似度超过阈值的匹配
        return best_match if best_score > 0.5 else None
    
    def calculate_similarity(self, source_parts: List[str], target_parts: List[str]) -> float:
        """计算路径相似度"""
        # 简单的相似度计算：匹配的部分数量 / 总部分数量
        matches = 0
        total = max(len(source_parts), len(target_parts))
        
        for i in range(min(len(source_parts), len(target_parts))):
            if source_parts[i].lower() == target_parts[i].lower():
                matches += 1
            elif self.is_similar_field(source_parts[i], target_parts[i]):
                matches += 0.5
        
        return matches / total if total > 0 else 0
    
    def is_similar_field(self, field1: str, field2: str) -> bool:
        """检查字段名是否相似"""
        # 常见的字段名映射
        similar_fields = {
            "name": ["full_name", "username", "display_name"],
            "email": ["email_address", "mail"],
            "phone": ["phone_number", "mobile", "tel"],
            "address": ["addr", "location"],
            "id": ["identifier", "uid", "user_id"]
        }
        
        field1_lower = field1.lower()
        field2_lower = field2.lower()
        
        for key, variants in similar_fields.items():
            if (field1_lower == key and field2_lower in variants) or \
               (field2_lower == key and field1_lower in variants):
                return True
        
        return False
    
    def transform_data(self, source_data: Dict[str, Any], mapping: Dict[str, str]) -> Dict[str, Any]:
        """根据映射规则转换数据"""
        result = {}
        
        for source_path, target_path in mapping.items():
            # 获取源数据值
            success, value = self.path_builder.get_value_at_path(source_data, source_path)
            
            if success and value is not None:
                # 设置目标路径的值
                self.set_value_at_path(result, target_path, value)
        
        return result
    
    def set_value_at_path(self, data: Dict[str, Any], path: str, value: Any):
        """在指定路径设置值"""
        parts = path.split('.')
        current = data
        
        # 创建嵌套结构
        for part in parts[:-1]:
            if part not in current:
                current[part] = {}
            current = current[part]
        
        # 设置最终值
        current[parts[-1]] = value

# 使用示例
def demo_data_mapping():
    """演示数据映射功能"""
    mapper = DataMapper()
    
    # 源系统数据结构
    source_data = {
        "user_info": {
            "full_name": "John Doe",
            "email_address": "john@example.com",
            "phone_number": "+1234567890"
        },
        "profile": {
            "age": 30,
            "location": {
                "city": "New York",
                "country": "USA"
            }
        }
    }
    
    # 目标系统数据结构
    target_schema = {
        "personal": {
            "name": "",
            "email": "",
            "phone": ""
        },
        "demographics": {
            "age": 0,
            "address": {
                "city": "",
                "country": ""
            }
        }
    }
    
    # 创建映射
    mapping = mapper.create_mapping(source_data, target_schema)
    
    print("=== 自动生成的映射规则 ===")
    for source_path, target_path in mapping.items():
        print(f"{source_path} -> {target_path}")
    
    # 转换数据
    transformed_data = mapper.transform_data(source_data, mapping)
    
    print("\n=== 转换后的数据 ===")
    print(json.dumps(transformed_data, indent=2, ensure_ascii=False))

# 运行演示
demo_data_mapping()
```

### 应用场景3：配置文件验证

**场景描述**：验证复杂配置文件的结构和必需字段。

```python
from agently_format.core.path_builder import PathBuilder
from typing import Dict, Any, List, Set

class ConfigValidator:
    """配置文件验证器"""
    
    def __init__(self):
        self.path_builder = PathBuilder()
        self.required_paths: Set[str] = set()
        self.validation_rules: Dict[str, callable] = {}
    
    def add_required_path(self, path: str):
        """添加必需路径"""
        self.required_paths.add(path)
    
    def add_validation_rule(self, path: str, validator: callable):
        """添加验证规则"""
        self.validation_rules[path] = validator
    
    def validate_config(self, config_data: Dict[str, Any]) -> Dict[str, Any]:
        """验证配置文件"""
        result = {
            "is_valid": True,
            "errors": [],
            "warnings": [],
            "missing_required": [],
            "extra_fields": []
        }
        
        # 提取配置中的所有路径
        actual_paths = set(self.path_builder.extract_parsing_key_orders(config_data))
        
        # 检查必需字段
        missing_required = self.required_paths - actual_paths
        if missing_required:
            result["missing_required"] = list(missing_required)
            result["errors"].extend([
                f"缺少必需字段: {path}" for path in missing_required
            ])
            result["is_valid"] = False
        
        # 检查额外字段（可选）
        if hasattr(self, 'allowed_paths'):
            extra_fields = actual_paths - self.allowed_paths - self.required_paths
            if extra_fields:
                result["extra_fields"] = list(extra_fields)
                result["warnings"].extend([
                    f"未知字段: {path}" for path in extra_fields
                ])
        
        # 执行自定义验证规则
        for path, validator in self.validation_rules.items():
            if path in actual_paths:
                success, value = self.path_builder.get_value_at_path(config_data, path)
                if success:
                    try:
                        is_valid, error_msg = validator(value)
                        if not is_valid:
                            result["errors"].append(f"{path}: {error_msg}")
                            result["is_valid"] = False
                    except Exception as e:
                        result["errors"].append(f"{path}: 验证规则执行失败 - {e}")
                        result["is_valid"] = False
        
        return result

# 验证规则示例
def validate_port(value) -> Tuple[bool, str]:
    """验证端口号"""
    if not isinstance(value, int):
        return False, "端口号必须是整数"
    if not (1 <= value <= 65535):
        return False, "端口号必须在1-65535之间"
    return True, ""

def validate_email(value) -> Tuple[bool, str]:
    """验证邮箱地址"""
    import re
    if not isinstance(value, str):
        return False, "邮箱地址必须是字符串"
    pattern = r'^[\w\.-]+@[\w\.-]+\.\w+$'
    if not re.match(pattern, value):
        return False, "邮箱地址格式不正确"
    return True, ""

def validate_url(value) -> Tuple[bool, str]:
    """验证URL"""
    if not isinstance(value, str):
        return False, "URL必须是字符串"
    if not (value.startswith('http://') or value.startswith('https://')):
        return False, "URL必须以http://或https://开头"
    return True, ""

# 使用示例
def demo_config_validation():
    """演示配置验证功能"""
    validator = ConfigValidator()
    
    # 设置必需字段
    validator.add_required_path("server.host")
    validator.add_required_path("server.port")
    validator.add_required_path("database.url")
    validator.add_required_path("admin.email")
    
    # 设置验证规则
    validator.add_validation_rule("server.port", validate_port)
    validator.add_validation_rule("admin.email", validate_email)
    validator.add_validation_rule("database.url", validate_url)
    
    # 测试配置1：完整且正确的配置
    valid_config = {
        "server": {
            "host": "0.0.0.0",
            "port": 8000,
            "debug": False
        },
        "database": {
            "url": "https://db.example.com",
            "timeout": 30
        },
        "admin": {
            "email": "admin@example.com",
            "name": "Administrator"
        }
    }
    
    print("=== 验证正确配置 ===")
    result = validator.validate_config(valid_config)
    print(f"验证结果: {'通过' if result['is_valid'] else '失败'}")
    if result['errors']:
        print(f"错误: {result['errors']}")
    if result['warnings']:
        print(f"警告: {result['warnings']}")
    
    # 测试配置2：有问题的配置
    invalid_config = {
        "server": {
            "host": "0.0.0.0",
            "port": "invalid_port"  # 错误：应该是整数
        },
        "database": {
            "url": "invalid_url"  # 错误：URL格式不正确
        },
        "admin": {
            "email": "invalid_email"  # 错误：邮箱格式不正确
        }
        # 缺少必需字段
    }
    
    print("\n=== 验证错误配置 ===")
    result = validator.validate_config(invalid_config)
    print(f"验证结果: {'通过' if result['is_valid'] else '失败'}")
    if result['errors']:
        print("错误:")
        for error in result['errors']:
            print(f"  - {error}")
    if result['missing_required']:
        print(f"缺少必需字段: {result['missing_required']}")

# 运行演示
demo_config_validation()
```

### 常见问题解决

**问题1：处理数组索引**
```python
def handle_array_paths():
    """处理数组路径"""
    builder = PathBuilder()
    
    data = {
        "users": [
            {"name": "Alice", "age": 25},
            {"name": "Bob", "age": 30}
        ]
    }
    
    # 提取路径时会包含数组索引
    paths = builder.extract_parsing_key_orders(data)
    print("包含索引的路径:", paths)
    
    # 获取不包含索引的通用路径
    generic_paths = []
    for path in paths:
        # 移除数组索引
        generic_path = re.sub(r'\[\d+\]', '[]', path)
        if generic_path not in generic_paths:
            generic_paths.append(generic_path)
    
    print("通用路径:", generic_paths)
```

**问题2：路径格式转换**
```python
def convert_path_formats():
    """转换路径格式"""
    builder = PathBuilder()
    
    original_path = "user.profile.settings[0].value"
    
    # 转换为不同格式
    slash_path = builder.convert_path(original_path, PathStyle.SLASH)
    bracket_path = builder.convert_path(original_path, PathStyle.BRACKET)
    
    print(f"原始路径: {original_path}")
    print(f"斜杠格式: {slash_path}")
    print(f"括号格式: {bracket_path}")
```

---

## ✅ Schema验证最佳实践

### 应用场景1：API请求验证

**场景描述**：验证API请求数据的格式和内容，确保数据完整性和安全性。

```python
from agently_format.core.schemas import SchemaValidator
from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict, Any
from datetime import datetime
import re

# 定义API请求模型
class UserCreateRequest(BaseModel):
    """用户创建请求模型"""
    username: str = Field(..., min_length=3, max_length=50)
    email: str = Field(..., regex=r'^[\w\.-]+@[\w\.-]+\.\w+$')
    password: str = Field(..., min_length=8)
    full_name: str = Field(..., min_length=1, max_length=100)
    age: Optional[int] = Field(None, ge=13, le=120)
    tags: List[str] = Field(default_factory=list)
    metadata: Optional[Dict[str, Any]] = None
    
    @validator('username')
    def validate_username(cls, v):
        if not re.match(r'^[a-zA-Z0-9_]+$', v):
            raise ValueError('用户名只能包含字母、数字和下划线')
        return v
    
    @validator('password')
    def validate_password(cls, v):
        if not re.search(r'[A-Z]', v):
            raise ValueError('密码必须包含至少一个大写字母')
        if not re.search(r'[a-z]', v):
            raise ValueError('密码必须包含至少一个小写字母')
        if not re.search(r'\d', v):
            raise ValueError('密码必须包含至少一个数字')
        return v

class APIRequestValidator:
    """API请求验证器"""
    
    def __init__(self):
        self.user_validator = SchemaValidator(UserCreateRequest)
    
    def validate_user_creation(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """验证用户创建请求"""
        result = {
            "is_valid": False,
            "validated_data": None,
            "errors": [],
            "warnings": []
        }
        
        try:
            # 执行Schema验证
            validation_result = self.user_validator.validate(request_data)
            
            if validation_result.is_valid:
                result["is_valid"] = True
                result["validated_data"] = validation_result.validated_data
                
                # 添加业务逻辑验证
                business_validation = self.validate_business_rules(request_data)
                if business_validation["warnings"]:
                    result["warnings"] = business_validation["warnings"]
                
            else:
                result["errors"] = [
                    {"field": error.path, "message": error.message}
                    for error in validation_result.errors
                ]
        
        except Exception as e:
            result["errors"] = [{"field": "general", "message": str(e)}]
        
        return result
    
    def validate_business_rules(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """验证业务规则"""
        warnings = []
        
        # 检查常见的不安全用户名
        unsafe_usernames = ['admin', 'root', 'administrator', 'test']
        if data.get('username', '').lower() in unsafe_usernames:
            warnings.append("建议避免使用常见的系统用户名")
        
        # 检查邮箱域名
        email = data.get('email', '')
        if email:
            domain = email.split('@')[-1]
            suspicious_domains = ['tempmail.com', '10minutemail.com']
            if domain in suspicious_domains:
                warnings.append("检测到临时邮箱域名")
        
        # 检查年龄合理性
        age = data.get('age')
        if age and age < 16:
            warnings.append("用户年龄较小，可能需要监护人同意")
        
        return {"warnings": warnings}

# 使用示例
def demo_api_validation():
    """演示API验证功能"""
    validator = APIRequestValidator()
    
    # 测试数据1：有效请求
    valid_request = {
        "username": "john_doe",
        "email": "john@example.com",
        "password": "SecurePass123",
        "full_name": "John Doe",
        "age": 25,
        "tags": ["developer", "python"]
    }
    
    print("=== 验证有效请求 ===")
    result = validator.validate_user_creation(valid_request)
    print(f"验证结果: {'通过' if result['is_valid'] else '失败'}")
    if result['warnings']:
        print(f"警告: {result['warnings']}")
    
    # 测试数据2：无效请求
    invalid_request = {
        "username": "a",  # 太短
        "email": "invalid-email",  # 格式错误
        "password": "weak",  # 不符合密码规则
        "full_name": "",  # 空值
        "age": 200  # 超出范围
    }
    
    print("\n=== 验证无效请求 ===")
    result = validator.validate_user_creation(invalid_request)
    print(f"验证结果: {'通过' if result['is_valid'] else '失败'}")
    if result['errors']:
        print("错误详情:")
        for error in result['errors']:
            print(f"  {error['field']}: {error['message']}")

# 运行演示
demo_api_validation()
```

### 应用场景2：配置文件验证

**场景描述**：验证应用程序配置文件的结构和值，确保配置正确。

```python
from agently_format.core.schemas import SchemaValidator
from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict, Union
import os

# 定义配置模型
class DatabaseConfig(BaseModel):
    """数据库配置"""
    host: str = Field(..., min_length=1)
    port: int = Field(..., ge=1, le=65535)
    database: str = Field(..., min_length=1)
    username: str = Field(..., min_length=1)
    password: str = Field(..., min_length=1)
    pool_size: int = Field(default=10, ge=1, le=100)
    timeout: int = Field(default=30, ge=1, le=300)
    
    @validator('host')
    def validate_host(cls, v):
        # 简单的主机名验证
        if not (v == 'localhost' or '.' in v or ':' in v):
            raise ValueError('无效的主机名格式')
        return v

class RedisConfig(BaseModel):
    """Redis配置"""
    host: str = Field(default='localhost')
    port: int = Field(default=6379, ge=1, le=65535)
    password: Optional[str] = None
    db: int = Field(default=0, ge=0, le=15)
    max_connections: int = Field(default=50, ge=1, le=1000)

class LoggingConfig(BaseModel):
    """日志配置"""
    level: str = Field(..., regex=r'^(DEBUG|INFO|WARNING|ERROR|CRITICAL)$')
    format: str = Field(default='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_path: Optional[str] = None
    max_size: str = Field(default='10MB', regex=r'^\d+[KMGT]?B$')
    backup_count: int = Field(default=5, ge=1, le=100)
    
    @validator('file_path')
    def validate_file_path(cls, v):
        if v:
            directory = os.path.dirname(v)
            if directory and not os.path.exists(directory):
                raise ValueError(f'日志目录不存在: {directory}')
        return v

class ServerConfig(BaseModel):
    """服务器配置"""
    host: str = Field(default='0.0.0.0')
    port: int = Field(..., ge=1, le=65535)
    workers: int = Field(default=1, ge=1, le=32)
    debug: bool = Field(default=False)
    secret_key: str = Field(..., min_length=32)
    
    @validator('secret_key')
    def validate_secret_key(cls, v):
        if len(set(v)) < 10:  # 检查字符多样性
            raise ValueError('密钥字符多样性不足')
        return v

class AppConfig(BaseModel):
    """应用程序配置"""
    app_name: str = Field(..., min_length=1)
    version: str = Field(..., regex=r'^\d+\.\d+\.\d+$')
    environment: str = Field(..., regex=r'^(development|staging|production)$')
    
    server: ServerConfig
    database: DatabaseConfig
    redis: Optional[RedisConfig] = None
    logging: LoggingConfig
    
    features: Dict[str, bool] = Field(default_factory=dict)
    external_apis: Dict[str, str] = Field(default_factory=dict)

class ConfigFileValidator:
    """配置文件验证器"""
    
    def __init__(self):
        self.validator = SchemaValidator(AppConfig)
        self.environment_checks = {
            'development': self.validate_dev_environment,
            'staging': self.validate_staging_environment,
            'production': self.validate_prod_environment
        }
    
    def validate_config_file(self, config_data: Dict[str, Any]) -> Dict[str, Any]:
        """验证配置文件"""
        result = {
            "is_valid": False,
            "validated_data": None,
            "errors": [],
            "warnings": [],
            "security_issues": []
        }
        
        try:
            # 基础Schema验证
            validation_result = self.validator.validate(config_data)
            
            if validation_result.is_valid:
                result["validated_data"] = validation_result.validated_data
                
                # 环境特定验证
                env = config_data.get('environment', 'development')
                if env in self.environment_checks:
                    env_result = self.environment_checks[env](config_data)
                    result["warnings"].extend(env_result.get('warnings', []))
                    result["security_issues"].extend(env_result.get('security_issues', []))
                
                # 安全检查
                security_result = self.validate_security(config_data)
                result["security_issues"].extend(security_result)
                
                result["is_valid"] = True
            else:
                result["errors"] = [
                    {"field": error.path, "message": error.message}
                    for error in validation_result.errors
                ]
        
        except Exception as e:
            result["errors"] = [{"field": "general", "message": str(e)}]
        
        return result
    
    def validate_dev_environment(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """验证开发环境配置"""
        warnings = []
        security_issues = []
        
        if not config.get('server', {}).get('debug', False):
            warnings.append("开发环境建议启用debug模式")
        
        return {"warnings": warnings, "security_issues": security_issues}
    
    def validate_staging_environment(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """验证预发布环境配置"""
        warnings = []
        security_issues = []
        
        if config.get('server', {}).get('debug', False):
            warnings.append("预发布环境不建议启用debug模式")
        
        return {"warnings": warnings, "security_issues": security_issues}
    
    def validate_prod_environment(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """验证生产环境配置"""
        warnings = []
        security_issues = []
        
        server_config = config.get('server', {})
        
        if server_config.get('debug', False):
            security_issues.append("生产环境禁止启用debug模式")
        
        if server_config.get('host') == '0.0.0.0':
            warnings.append("生产环境建议限制服务器监听地址")
        
        # 检查密钥强度
        secret_key = server_config.get('secret_key', '')
        if len(secret_key) < 64:
            security_issues.append("生产环境密钥长度应至少64位")
        
        return {"warnings": warnings, "security_issues": security_issues}
    
    def validate_security(self, config: Dict[str, Any]) -> List[str]:
        """安全验证"""
        issues = []
        
        # 检查默认密码
        db_config = config.get('database', {})
        if db_config.get('password') in ['password', '123456', 'admin']:
            issues.append("数据库使用了弱密码")
        
        # 检查Redis密码
        redis_config = config.get('redis', {})
        if redis_config and not redis_config.get('password'):
            issues.append("Redis未设置密码")
        
        return issues

# 使用示例
def demo_config_validation():
    """演示配置验证功能"""
    validator = ConfigFileValidator()
    
    # 测试配置
    test_config = {
        "app_name": "MyApp",
        "version": "1.0.0",
        "environment": "production",
        "server": {
            "host": "0.0.0.0",
            "port": 8000,
            "workers": 4,
            "debug": False,
            "secret_key": "a_very_long_and_secure_secret_key_for_production_use_12345"
        },
        "database": {
            "host": "db.example.com",
            "port": 5432,
            "database": "myapp",
            "username": "dbuser",
            "password": "secure_password_123"
        },
        "logging": {
            "level": "INFO",
            "file_path": "/var/log/myapp.log"
        }
    }
    
    print("=== 配置文件验证结果 ===")
    result = validator.validate_config_file(test_config)
    
    print(f"验证结果: {'通过' if result['is_valid'] else '失败'}")
    
    if result['errors']:
        print("\n错误:")
        for error in result['errors']:
            print(f"  {error['field']}: {error['message']}")
    
    if result['warnings']:
        print("\n警告:")
        for warning in result['warnings']:
            print(f"  - {warning}")
    
    if result['security_issues']:
        print("\n安全问题:")
        for issue in result['security_issues']:
            print(f"  ⚠️ {issue}")

# 运行演示
demo_config_validation()
```

### 应用场景3：数据导入验证

**场景描述**：批量导入数据时验证每条记录的格式和内容。

```python
from agently_format.core.schemas import SchemaValidator
from pydantic import BaseModel, Field, validator
from typing import List, Dict, Any, Optional
from datetime import datetime, date
import csv
import json

# 定义数据模型
class EmployeeRecord(BaseModel):
    """员工记录模型"""
    employee_id: str = Field(..., regex=r'^EMP\d{6}$')
    first_name: str = Field(..., min_length=1, max_length=50)
    last_name: str = Field(..., min_length=1, max_length=50)
    email: str = Field(..., regex=r'^[\w\.-]+@[\w\.-]+\.\w+$')
    department: str = Field(..., min_length=1)
    position: str = Field(..., min_length=1)
    hire_date: date
    salary: float = Field(..., gt=0, le=1000000)
    is_active: bool = Field(default=True)
    manager_id: Optional[str] = Field(None, regex=r'^EMP\d{6}$')
    
    @validator('hire_date')
    def validate_hire_date(cls, v):
        if v > date.today():
            raise ValueError('入职日期不能是未来日期')
        if v < date(1950, 1, 1):
            raise ValueError('入职日期过早')
        return v
    
    @validator('email')
    def validate_email_domain(cls, v):
        allowed_domains = ['company.com', 'subsidiary.com']
        domain = v.split('@')[1]
        if domain not in allowed_domains:
            raise ValueError(f'邮箱域名必须是: {", ".join(allowed_domains)}')
        return v

class DataImportValidator:
    """数据导入验证器"""
    
    def __init__(self):
        self.employee_validator = SchemaValidator(EmployeeRecord)
        self.processed_ids = set()
    
    def validate_batch_import(self, records: List[Dict[str, Any]]) -> Dict[str, Any]:
        """批量验证导入数据"""
        result = {
            "total_records": len(records),
            "valid_records": [],
            "invalid_records": [],
            "duplicate_ids": [],
            "summary": {
                "valid_count": 0,
                "invalid_count": 0,
                "duplicate_count": 0
            }
        }
        
        for i, record in enumerate(records):
            record_result = self.validate_single_record(record, i)
            
            if record_result["is_valid"]:
                # 检查重复ID
                emp_id = record.get('employee_id')
                if emp_id in self.processed_ids:
                    result["duplicate_ids"].append({
                        "row": i + 1,
                        "employee_id": emp_id,
                        "error": "员工ID重复"
                    })
                    result["summary"]["duplicate_count"] += 1
                else:
                    self.processed_ids.add(emp_id)
                    result["valid_records"].append({
                        "row": i + 1,
                        "data": record_result["validated_data"]
                    })
                    result["summary"]["valid_count"] += 1
            else:
                result["invalid_records"].append({
                    "row": i + 1,
                    "data": record,
                    "errors": record_result["errors"]
                })
                result["summary"]["invalid_count"] += 1
        
        return result
    
    def validate_single_record(self, record: Dict[str, Any], row_index: int) -> Dict[str, Any]:
        """验证单条记录"""
        try:
            # 数据类型转换
            processed_record = self.preprocess_record(record)
            
            # Schema验证
            validation_result = self.employee_validator.validate(processed_record)
            
            if validation_result.is_valid:
                return {
                    "is_valid": True,
                    "validated_data": validation_result.validated_data,
                    "errors": []
                }
            else:
                return {
                    "is_valid": False,
                    "validated_data": None,
                    "errors": [
                        {"field": error.path, "message": error.message}
                        for error in validation_result.errors
                    ]
                }
        
        except Exception as e:
            return {
                "is_valid": False,
                "validated_data": None,
                "errors": [{"field": "general", "message": str(e)}]
            }
    
    def preprocess_record(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """预处理记录数据"""
        processed = record.copy()
        
        # 转换日期格式
        if 'hire_date' in processed and isinstance(processed['hire_date'], str):
            try:
                processed['hire_date'] = datetime.strptime(
                    processed['hire_date'], '%Y-%m-%d'
                ).date()
            except ValueError:
                try:
                    processed['hire_date'] = datetime.strptime(
                        processed['hire_date'], '%m/%d/%Y'
                    ).date()
                except ValueError:
                    pass  # 让Schema验证处理错误
        
        # 转换薪资格式
        if 'salary' in processed and isinstance(processed['salary'], str):
            try:
                # 移除货币符号和逗号
                salary_str = processed['salary'].replace('$', '').replace(',', '')
                processed['salary'] = float(salary_str)
            except ValueError:
                pass  # 让Schema验证处理错误
        
        # 转换布尔值
        if 'is_active' in processed and isinstance(processed['is_active'], str):
            processed['is_active'] = processed['is_active'].lower() in ['true', '1', 'yes', 'y']
        
        return processed
    
    def generate_error_report(self, validation_result: Dict[str, Any]) -> str:
        """生成错误报告"""
        report = []
        report.append("=== 数据导入验证报告 ===")
        report.append(f"总记录数: {validation_result['total_records']}")
        report.append(f"有效记录: {validation_result['summary']['valid_count']}")
        report.append(f"无效记录: {validation_result['summary']['invalid_count']}")
        report.append(f"重复记录: {validation_result['summary']['duplicate_count']}")
        report.append("")
        
        if validation_result['invalid_records']:
            report.append("=== 无效记录详情 ===")
            for record in validation_result['invalid_records']:
                report.append(f"第{record['row']}行:")
                for error in record['errors']:
                    report.append(f"  {error['field']}: {error['message']}")
                report.append("")
        
        if validation_result['duplicate_ids']:
            report.append("=== 重复ID记录 ===")
            for dup in validation_result['duplicate_ids']:
                report.append(f"第{dup['row']}行: {dup['employee_id']} - {dup['error']}")
        
        return "\n".join(report)

# 使用示例
def demo_data_import_validation():
    """演示数据导入验证"""
    validator = DataImportValidator()
    
    # 模拟CSV导入数据
    import_data = [
        {
            "employee_id": "EMP123456",
            "first_name": "John",
            "last_name": "Doe",
            "email": "john.doe@company.com",
            "department": "Engineering",
            "position": "Software Engineer",
            "hire_date": "2023-01-15",
            "salary": "75000.00",
            "is_active": "true"
        },
        {
            "employee_id": "EMP123457",
            "first_name": "Jane",
            "last_name": "Smith",
            "email": "jane.smith@external.com",  # 错误：域名不允许
            "department": "Marketing",
            "position": "Marketing Manager",
            "hire_date": "2025-01-01",  # 错误：未来日期
            "salary": "invalid_salary",  # 错误：无效薪资
            "is_active": "yes"
        },
        {
            "employee_id": "EMP123456",  # 错误：重复ID
            "first_name": "Bob",
            "last_name": "Johnson",
            "email": "bob.johnson@company.com",
            "department": "Sales",
            "position": "Sales Representative",
            "hire_date": "2023-03-01",
            "salary": "60000",
            "is_active": "true"
        }
    ]
    
    # 执行验证
    result = validator.validate_batch_import(import_data)
    
    # 生成报告
    report = validator.generate_error_report(result)
    print(report)
    
    # 输出有效记录
    if result['valid_records']:
        print("\n=== 有效记录 ===")
        for record in result['valid_records']:
            print(f"第{record['row']}行: {record['data']['first_name']} {record['data']['last_name']}")

# 运行演示
demo_data_import_validation()
```

### 常见问题解决方案

**Q1: 如何处理大量数据的验证性能问题？**

A1: 使用批量验证和缓存优化：

```python
from agently_format.core.schemas import SchemaValidator
from concurrent.futures import ThreadPoolExecutor
import time

class PerformanceOptimizedValidator:
    """性能优化的验证器"""
    
    def __init__(self, schema_class, batch_size=100, max_workers=4):
        self.validator = SchemaValidator(schema_class)
        self.batch_size = batch_size
        self.max_workers = max_workers
        self.validation_cache = {}
    
    def validate_large_dataset(self, records: List[Dict[str, Any]]) -> Dict[str, Any]:
        """验证大数据集"""
        start_time = time.time()
        
        # 分批处理
        batches = [records[i:i + self.batch_size] 
                  for i in range(0, len(records), self.batch_size)]
        
        all_results = []
        
        # 并行处理批次
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            batch_results = list(executor.map(self.validate_batch, batches))
        
        # 合并结果
        total_valid = sum(result['valid_count'] for result in batch_results)
        total_invalid = sum(result['invalid_count'] for result in batch_results)
        
        end_time = time.time()
        
        return {
            "total_records": len(records),
            "valid_count": total_valid,
            "invalid_count": total_invalid,
            "processing_time": end_time - start_time,
            "records_per_second": len(records) / (end_time - start_time)
        }
    
    def validate_batch(self, batch: List[Dict[str, Any]]) -> Dict[str, Any]:
        """验证单个批次"""
        valid_count = 0
        invalid_count = 0
        
        for record in batch:
            # 使用缓存加速重复验证
            record_hash = hash(str(sorted(record.items())))
            
            if record_hash in self.validation_cache:
                is_valid = self.validation_cache[record_hash]
            else:
                result = self.validator.validate(record)
                is_valid = result.is_valid
                self.validation_cache[record_hash] = is_valid
            
            if is_valid:
                valid_count += 1
            else:
                invalid_count += 1
        
        return {"valid_count": valid_count, "invalid_count": invalid_count}
```

**Q2: 如何自定义复杂的验证规则？**

A2: 创建自定义验证器：

```python
from agently_format.core.schemas import SchemaValidator
from pydantic import BaseModel, validator, root_validator
from typing import Dict, Any

class CustomBusinessRules(BaseModel):
    """自定义业务规则模型"""
    user_id: str
    account_type: str
    balance: float
    credit_limit: float
    
    @validator('balance')
    def validate_balance(cls, v, values):
        account_type = values.get('account_type')
        if account_type == 'savings' and v < 0:
            raise ValueError('储蓄账户余额不能为负')
        return v
    
    @root_validator
    def validate_credit_rules(cls, values):
        account_type = values.get('account_type')
        balance = values.get('balance')
        credit_limit = values.get('credit_limit')
        
        if account_type == 'credit':
            if balance < -credit_limit:
                raise ValueError('余额不能超过信用额度')
        
        return values

class BusinessRuleValidator:
    """业务规则验证器"""
    
    def __init__(self):
        self.validator = SchemaValidator(CustomBusinessRules)
        self.business_rules = {
            'vip_customer': self.validate_vip_rules,
            'corporate_account': self.validate_corporate_rules
        }
    
    def validate_with_business_context(self, data: Dict[str, Any], 
                                     context: Dict[str, Any]) -> Dict[str, Any]:
        """带业务上下文的验证"""
        # 基础Schema验证
        base_result = self.validator.validate(data)
        
        if not base_result.is_valid:
            return {
                "is_valid": False,
                "errors": [error.message for error in base_result.errors],
                "business_warnings": []
            }
        
        # 业务规则验证
        business_warnings = []
        customer_type = context.get('customer_type')
        
        if customer_type in self.business_rules:
            warnings = self.business_rules[customer_type](data, context)
            business_warnings.extend(warnings)
        
        return {
            "is_valid": True,
            "validated_data": base_result.validated_data,
            "business_warnings": business_warnings
        }
    
    def validate_vip_rules(self, data: Dict[str, Any], 
                          context: Dict[str, Any]) -> List[str]:
        """VIP客户规则验证"""
        warnings = []
        
        if data['balance'] < 10000:
            warnings.append("VIP客户余额建议保持在1万以上")
        
        if data['account_type'] == 'basic':
            warnings.append("VIP客户建议升级到高级账户类型")
        
        return warnings
    
    def validate_corporate_rules(self, data: Dict[str, Any], 
                               context: Dict[str, Any]) -> List[str]:
        """企业客户规则验证"""
        warnings = []
        
        if data['credit_limit'] < 50000:
            warnings.append("企业客户建议申请更高信用额度")
        
        return warnings
```

---

## 5. 差分引擎最佳实践

### 核心功能概述

差分引擎提供高效的数据变更检测和同步功能，支持结构化差分、增量更新、版本追踪等特性。

### 应用场景1：版本控制系统

**场景描述**：为配置文件或数据结构实现版本控制，追踪变更历史。

```python
from agently_format.core.diff import DiffEngine
from typing import Dict, Any, List
from datetime import datetime
import json
import uuid

class VersionControlSystem:
    """版本控制系统"""
    
    def __init__(self):
        self.diff_engine = DiffEngine()
        self.versions = {}  # version_id -> version_data
        self.version_history = []  # 版本历史记录
        self.current_version = None
    
    def create_initial_version(self, data: Dict[str, Any], 
                             description: str = "Initial version") -> str:
        """创建初始版本"""
        version_id = str(uuid.uuid4())
        
        version_info = {
            "id": version_id,
            "data": data,
            "timestamp": datetime.now().isoformat(),
            "description": description,
            "parent_version": None,
            "changes": None
        }
        
        self.versions[version_id] = version_info
        self.version_history.append(version_id)
        self.current_version = version_id
        
        return version_id
    
    def create_new_version(self, new_data: Dict[str, Any], 
                          description: str = "New version") -> str:
        """创建新版本"""
        if not self.current_version:
            return self.create_initial_version(new_data, description)
        
        # 计算与当前版本的差异
        current_data = self.versions[self.current_version]["data"]
        diff_result = self.diff_engine.compute_diff(current_data, new_data)
        
        version_id = str(uuid.uuid4())
        
        version_info = {
            "id": version_id,
            "data": new_data,
            "timestamp": datetime.now().isoformat(),
            "description": description,
            "parent_version": self.current_version,
            "changes": diff_result
        }
        
        self.versions[version_id] = version_info
        self.version_history.append(version_id)
        self.current_version = version_id
        
        return version_id
    
    def get_version_diff(self, version_a: str, version_b: str) -> Dict[str, Any]:
        """获取两个版本之间的差异"""
        if version_a not in self.versions or version_b not in self.versions:
            raise ValueError("版本不存在")
        
        data_a = self.versions[version_a]["data"]
        data_b = self.versions[version_b]["data"]
        
        return self.diff_engine.compute_diff(data_a, data_b)
    
    def rollback_to_version(self, version_id: str) -> bool:
        """回滚到指定版本"""
        if version_id not in self.versions:
            return False
        
        self.current_version = version_id
        return True
    
    def get_version_history(self) -> List[Dict[str, Any]]:
        """获取版本历史"""
        history = []
        
        for version_id in self.version_history:
            version_info = self.versions[version_id]
            
            # 计算变更统计
            changes_summary = self.summarize_changes(version_info.get("changes"))
            
            history.append({
                "id": version_id,
                "timestamp": version_info["timestamp"],
                "description": version_info["description"],
                "parent_version": version_info["parent_version"],
                "changes_summary": changes_summary
            })
        
        return history
    
    def summarize_changes(self, changes: Dict[str, Any]) -> Dict[str, int]:
        """汇总变更统计"""
        if not changes:
            return {"added": 0, "modified": 0, "deleted": 0}
        
        summary = {"added": 0, "modified": 0, "deleted": 0}
        
        for change in changes.get("changes", []):
            change_type = change.get("type")
            if change_type == "add":
                summary["added"] += 1
            elif change_type == "modify":
                summary["modified"] += 1
            elif change_type == "delete":
                summary["deleted"] += 1
        
        return summary
    
    def export_version_tree(self) -> Dict[str, Any]:
        """导出版本树结构"""
        tree = {}
        
        for version_id in self.version_history:
            version_info = self.versions[version_id]
            parent = version_info["parent_version"]
            
            tree[version_id] = {
                "parent": parent,
                "timestamp": version_info["timestamp"],
                "description": version_info["description"],
                "is_current": version_id == self.current_version
            }
        
        return tree

# 使用示例
def demo_version_control():
    """演示版本控制功能"""
    vcs = VersionControlSystem()
    
    # 创建初始配置
    initial_config = {
        "app_name": "MyApp",
        "version": "1.0.0",
        "database": {
            "host": "localhost",
            "port": 5432,
            "name": "myapp_db"
        },
        "features": {
            "user_auth": True,
            "file_upload": False
        }
    }
    
    v1 = vcs.create_initial_version(initial_config, "初始配置")
    print(f"创建初始版本: {v1}")
    
    # 更新配置 - 添加新功能
    updated_config = initial_config.copy()
    updated_config["version"] = "1.1.0"
    updated_config["features"]["file_upload"] = True
    updated_config["features"]["email_notifications"] = True
    
    v2 = vcs.create_new_version(updated_config, "启用文件上传和邮件通知")
    print(f"创建版本2: {v2}")
    
    # 再次更新 - 修改数据库配置
    final_config = updated_config.copy()
    final_config["version"] = "1.2.0"
    final_config["database"]["host"] = "prod-db.example.com"
    final_config["database"]["port"] = 5433
    
    v3 = vcs.create_new_version(final_config, "更新生产数据库配置")
    print(f"创建版本3: {v3}")
    
    # 查看版本历史
    print("\n=== 版本历史 ===")
    history = vcs.get_version_history()
    for version in history:
        print(f"版本: {version['id'][:8]}...")
        print(f"  时间: {version['timestamp']}")
        print(f"  描述: {version['description']}")
        print(f"  变更: +{version['changes_summary']['added']} "
              f"~{version['changes_summary']['modified']} "
              f"-{version['changes_summary']['deleted']}")
        print()
    
    # 查看特定版本间的差异
    print("=== 版本差异 (v1 -> v3) ===")
    diff = vcs.get_version_diff(v1, v3)
    print(json.dumps(diff, indent=2, ensure_ascii=False))
    
    # 回滚演示
    print(f"\n当前版本: {vcs.current_version[:8]}...")
    vcs.rollback_to_version(v2)
    print(f"回滚后版本: {vcs.current_version[:8]}...")

# 运行演示
demo_version_control()
```

### 应用场景2：数据同步系统

**场景描述**：在分布式系统中同步数据变更，减少网络传输量。

```python
from agently_format.core.diff import DiffEngine
from typing import Dict, Any, List, Optional
import json
import time
from datetime import datetime

class DataSyncManager:
    """数据同步管理器"""
    
    def __init__(self, node_id: str):
        self.node_id = node_id
        self.diff_engine = DiffEngine()
        self.local_data = {}
        self.sync_log = []  # 同步日志
        self.last_sync_time = {}
    
    def update_local_data(self, key: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """更新本地数据并生成差分"""
        old_data = self.local_data.get(key, {})
        
        # 计算差分
        diff_result = self.diff_engine.compute_diff(old_data, data)
        
        # 更新本地数据
        self.local_data[key] = data
        
        # 记录同步日志
        sync_entry = {
            "timestamp": datetime.now().isoformat(),
            "node_id": self.node_id,
            "key": key,
            "operation": "update",
            "diff": diff_result,
            "data_size": len(json.dumps(data)),
            "diff_size": len(json.dumps(diff_result))
        }
        
        self.sync_log.append(sync_entry)
        
        return {
            "success": True,
            "diff": diff_result,
            "compression_ratio": sync_entry["diff_size"] / sync_entry["data_size"] if sync_entry["data_size"] > 0 else 0
        }
    
    def apply_remote_diff(self, key: str, diff: Dict[str, Any], 
                         source_node: str) -> Dict[str, Any]:
        """应用远程节点的差分更新"""
        try:
            old_data = self.local_data.get(key, {})
            
            # 应用差分
            new_data = self.diff_engine.apply_diff(old_data, diff)
            
            # 更新本地数据
            self.local_data[key] = new_data
            
            # 记录同步日志
            sync_entry = {
                "timestamp": datetime.now().isoformat(),
                "node_id": self.node_id,
                "source_node": source_node,
                "key": key,
                "operation": "apply_diff",
                "diff": diff,
                "success": True
            }
            
            self.sync_log.append(sync_entry)
            self.last_sync_time[source_node] = datetime.now().isoformat()
            
            return {
                "success": True,
                "updated_data": new_data,
                "message": f"成功应用来自节点 {source_node} 的差分更新"
            }
        
        except Exception as e:
            sync_entry = {
                "timestamp": datetime.now().isoformat(),
                "node_id": self.node_id,
                "source_node": source_node,
                "key": key,
                "operation": "apply_diff",
                "diff": diff,
                "success": False,
                "error": str(e)
            }
            
            self.sync_log.append(sync_entry)
            
            return {
                "success": False,
                "error": str(e),
                "message": f"应用差分更新失败: {str(e)}"
            }
    
    def get_sync_package(self, target_node: str, keys: List[str] = None) -> Dict[str, Any]:
        """生成同步包"""
        if keys is None:
            keys = list(self.local_data.keys())
        
        sync_package = {
            "source_node": self.node_id,
            "target_node": target_node,
            "timestamp": datetime.now().isoformat(),
            "updates": []
        }
        
        total_original_size = 0
        total_compressed_size = 0
        
        for key in keys:
            if key in self.local_data:
                data = self.local_data[key]
                
                # 检查是否有历史数据用于差分
                last_sync = self.get_last_sync_data(target_node, key)
                
                if last_sync:
                    # 生成差分
                    diff = self.diff_engine.compute_diff(last_sync, data)
                    update_type = "diff"
                    payload = diff
                else:
                    # 全量数据
                    update_type = "full"
                    payload = data
                
                original_size = len(json.dumps(data))
                compressed_size = len(json.dumps(payload))
                
                total_original_size += original_size
                total_compressed_size += compressed_size
                
                sync_package["updates"].append({
                    "key": key,
                    "type": update_type,
                    "payload": payload,
                    "original_size": original_size,
                    "compressed_size": compressed_size
                })
        
        sync_package["summary"] = {
            "total_updates": len(sync_package["updates"]),
            "total_original_size": total_original_size,
            "total_compressed_size": total_compressed_size,
            "compression_ratio": total_compressed_size / total_original_size if total_original_size > 0 else 0
        }
        
        return sync_package
    
    def get_last_sync_data(self, target_node: str, key: str) -> Optional[Dict[str, Any]]:
        """获取上次同步的数据（模拟）"""
        # 在实际应用中，这里应该从持久化存储中获取
        # 这里简化为返回None，表示没有历史数据
        return None
    
    def get_sync_statistics(self) -> Dict[str, Any]:
        """获取同步统计信息"""
        total_syncs = len(self.sync_log)
        successful_syncs = sum(1 for entry in self.sync_log if entry.get("success", True))
        failed_syncs = total_syncs - successful_syncs
        
        # 计算平均压缩比
        compression_ratios = []
        for entry in self.sync_log:
            if "data_size" in entry and "diff_size" in entry and entry["data_size"] > 0:
                compression_ratios.append(entry["diff_size"] / entry["data_size"])
        
        avg_compression_ratio = sum(compression_ratios) / len(compression_ratios) if compression_ratios else 0
        
        return {
            "node_id": self.node_id,
            "total_syncs": total_syncs,
            "successful_syncs": successful_syncs,
            "failed_syncs": failed_syncs,
            "success_rate": successful_syncs / total_syncs if total_syncs > 0 else 0,
            "average_compression_ratio": avg_compression_ratio,
            "data_keys": list(self.local_data.keys()),
            "last_sync_times": self.last_sync_time
        }

# 使用示例
def demo_data_sync():
    """演示数据同步功能"""
    # 创建两个节点
    node_a = DataSyncManager("node_a")
    node_b = DataSyncManager("node_b")
    
    print("=== 数据同步演示 ===")
    
    # 节点A更新数据
    user_data = {
        "users": {
            "user_1": {"name": "Alice", "age": 25, "email": "alice@example.com"},
            "user_2": {"name": "Bob", "age": 30, "email": "bob@example.com"}
        },
        "settings": {
            "theme": "dark",
            "language": "en",
            "notifications": True
        }
    }
    
    result_a = node_a.update_local_data("app_data", user_data)
    print(f"节点A更新数据，压缩比: {result_a['compression_ratio']:.2%}")
    
    # 生成同步包
    sync_package = node_a.get_sync_package("node_b", ["app_data"])
    print(f"\n生成同步包:")
    print(f"  更新数量: {sync_package['summary']['total_updates']}")
    print(f"  原始大小: {sync_package['summary']['total_original_size']} bytes")
    print(f"  压缩大小: {sync_package['summary']['total_compressed_size']} bytes")
    print(f"  压缩比: {sync_package['summary']['compression_ratio']:.2%}")
    
    # 节点B应用同步包
    for update in sync_package["updates"]:
        if update["type"] == "full":
            # 全量更新
            node_b.local_data[update["key"]] = update["payload"]
        else:
            # 差分更新
            result_b = node_b.apply_remote_diff(
                update["key"], 
                update["payload"], 
                sync_package["source_node"]
            )
            print(f"\n节点B应用差分: {result_b['message']}")
    
    # 节点A再次更新数据
    updated_user_data = user_data.copy()
    updated_user_data["users"]["user_3"] = {"name": "Charlie", "age": 28, "email": "charlie@example.com"}
    updated_user_data["settings"]["theme"] = "light"
    
    result_a2 = node_a.update_local_data("app_data", updated_user_data)
    print(f"\n节点A再次更新数据，压缩比: {result_a2['compression_ratio']:.2%}")
    
    # 查看同步统计
    print("\n=== 同步统计 ===")
    stats_a = node_a.get_sync_statistics()
    stats_b = node_b.get_sync_statistics()
    
    print(f"节点A: 成功率 {stats_a['success_rate']:.2%}, 平均压缩比 {stats_a['average_compression_ratio']:.2%}")
    print(f"节点B: 成功率 {stats_b['success_rate']:.2%}, 平均压缩比 {stats_b['average_compression_ratio']:.2%}")

# 运行演示
demo_data_sync()
```

### 应用场景3：配置管理系统

**场景描述**：管理应用配置的变更，支持环境间配置同步和回滚。

```python
from agently_format.core.diff import DiffEngine
from typing import Dict, Any, List, Optional
from datetime import datetime
import json
import copy

class ConfigurationManager:
    """配置管理系统"""
    
    def __init__(self, environment: str):
        self.environment = environment
        self.diff_engine = DiffEngine()
        self.configurations = {}  # config_name -> config_data
        self.config_history = {}  # config_name -> [history_entries]
        self.config_templates = {}  # 配置模板
    
    def register_config_template(self, name: str, template: Dict[str, Any]):
        """注册配置模板"""
        self.config_templates[name] = template
    
    def create_config_from_template(self, config_name: str, template_name: str, 
                                  overrides: Dict[str, Any] = None) -> Dict[str, Any]:
        """从模板创建配置"""
        if template_name not in self.config_templates:
            raise ValueError(f"模板 {template_name} 不存在")
        
        # 复制模板
        config = copy.deepcopy(self.config_templates[template_name])
        
        # 应用覆盖值
        if overrides:
            config = self.merge_configs(config, overrides)
        
        # 保存配置
        self.update_configuration(config_name, config, f"从模板 {template_name} 创建")
        
        return config
    
    def update_configuration(self, config_name: str, new_config: Dict[str, Any], 
                           description: str = "配置更新") -> Dict[str, Any]:
        """更新配置"""
        old_config = self.configurations.get(config_name, {})
        
        # 计算差分
        diff_result = self.diff_engine.compute_diff(old_config, new_config)
        
        # 更新配置
        self.configurations[config_name] = new_config
        
        # 记录历史
        history_entry = {
            "timestamp": datetime.now().isoformat(),
            "environment": self.environment,
            "description": description,
            "diff": diff_result,
            "config_snapshot": copy.deepcopy(new_config)
        }
        
        if config_name not in self.config_history:
            self.config_history[config_name] = []
        
        self.config_history[config_name].append(history_entry)
        
        return {
            "success": True,
            "config_name": config_name,
            "changes": diff_result,
            "change_summary": self.summarize_config_changes(diff_result)
        }
    
    def rollback_configuration(self, config_name: str, steps: int = 1) -> Dict[str, Any]:
        """回滚配置"""
        if config_name not in self.config_history:
            return {"success": False, "error": "配置历史不存在"}
        
        history = self.config_history[config_name]
        
        if len(history) <= steps:
            return {"success": False, "error": "回滚步数超过历史记录"}
        
        # 获取目标配置
        target_entry = history[-(steps + 1)]
        target_config = target_entry["config_snapshot"]
        
        # 更新配置
        result = self.update_configuration(
            config_name, 
            target_config, 
            f"回滚 {steps} 步到 {target_entry['timestamp']}"
        )
        
        return result
    
    def sync_config_between_environments(self, config_name: str, 
                                       target_manager: 'ConfigurationManager',
                                       sync_mode: str = "diff") -> Dict[str, Any]:
        """在环境间同步配置"""
        if config_name not in self.configurations:
            return {"success": False, "error": "源配置不存在"}
        
        source_config = self.configurations[config_name]
        target_config = target_manager.configurations.get(config_name, {})
        
        if sync_mode == "full":
            # 全量同步
            result = target_manager.update_configuration(
                config_name,
                source_config,
                f"从 {self.environment} 环境全量同步"
            )
        else:
            # 差分同步
            diff = self.diff_engine.compute_diff(target_config, source_config)
            
            if not diff.get("changes"):
                return {
                    "success": True,
                    "message": "配置已同步，无需更新",
                    "changes": []
                }
            
            # 应用差分
            new_config = self.diff_engine.apply_diff(target_config, diff)
            
            result = target_manager.update_configuration(
                config_name,
                new_config,
                f"从 {self.environment} 环境差分同步"
            )
        
        return result
    
    def merge_configs(self, base_config: Dict[str, Any], 
                     override_config: Dict[str, Any]) -> Dict[str, Any]:
        """合并配置"""
        merged = copy.deepcopy(base_config)
        
        def deep_merge(base: Dict[str, Any], override: Dict[str, Any]):
            for key, value in override.items():
                if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                    deep_merge(base[key], value)
                else:
                    base[key] = value
        
        deep_merge(merged, override_config)
        return merged
    
    def summarize_config_changes(self, diff: Dict[str, Any]) -> Dict[str, Any]:
        """汇总配置变更"""
        summary = {
            "added_keys": [],
            "modified_keys": [],
            "deleted_keys": [],
            "total_changes": 0
        }
        
        for change in diff.get("changes", []):
            change_type = change.get("type")
            path = change.get("path", "")
            
            if change_type == "add":
                summary["added_keys"].append(path)
            elif change_type == "modify":
                summary["modified_keys"].append(path)
            elif change_type == "delete":
                summary["deleted_keys"].append(path)
            
            summary["total_changes"] += 1
        
        return summary
    
    def validate_config_consistency(self) -> Dict[str, Any]:
        """验证配置一致性"""
        issues = []
        
        for config_name, config in self.configurations.items():
            # 检查必需字段
            if "version" not in config:
                issues.append(f"配置 {config_name} 缺少版本信息")
            
            # 检查环境特定配置
            if self.environment == "production":
                if config.get("debug", False):
                    issues.append(f"生产环境配置 {config_name} 不应启用debug模式")
        
        return {
            "is_consistent": len(issues) == 0,
            "issues": issues,
            "total_configs": len(self.configurations)
        }
    
    def export_config_report(self) -> Dict[str, Any]:
        """导出配置报告"""
        report = {
            "environment": self.environment,
            "timestamp": datetime.now().isoformat(),
            "configurations": {},
            "summary": {
                "total_configs": len(self.configurations),
                "total_history_entries": sum(len(history) for history in self.config_history.values())
            }
        }
        
        for config_name, config in self.configurations.items():
            history = self.config_history.get(config_name, [])
            
            report["configurations"][config_name] = {
                "current_config": config,
                "last_updated": history[-1]["timestamp"] if history else None,
                "total_updates": len(history),
                "recent_changes": [entry["description"] for entry in history[-3:]]  # 最近3次变更
            }
        
        return report

# 使用示例
def demo_config_management():
    """演示配置管理功能"""
    # 创建不同环境的配置管理器
    dev_manager = ConfigurationManager("development")
    prod_manager = ConfigurationManager("production")
    
    print("=== 配置管理演示 ===")
    
    # 注册配置模板
    app_template = {
        "app_name": "MyApp",
        "version": "1.0.0",
        "server": {
            "host": "localhost",
            "port": 8000,
            "workers": 1,
            "debug": True
        },
        "database": {
            "host": "localhost",
            "port": 5432,
            "name": "myapp_dev"
        },
        "logging": {
            "level": "DEBUG",
            "file": "app.log"
        }
    }
    
    dev_manager.register_config_template("app_template", app_template)
    prod_manager.register_config_template("app_template", app_template)
    
    # 开发环境创建配置
    dev_config = dev_manager.create_config_from_template("app_config", "app_template")
    print("创建开发环境配置")
    
    # 生产环境创建配置（带覆盖）
    prod_overrides = {
        "server": {
            "host": "0.0.0.0",
            "workers": 4,
            "debug": False
        },
        "database": {
            "host": "prod-db.example.com",
            "name": "myapp_prod"
        },
        "logging": {
            "level": "INFO"
        }
    }
    
    prod_config = prod_manager.create_config_from_template(
        "app_config", "app_template", prod_overrides
    )
    print("创建生产环境配置")
    
    # 更新开发环境配置
    updated_dev_config = copy.deepcopy(dev_config)
    updated_dev_config["server"]["port"] = 8080
    updated_dev_config["features"] = {"new_feature": True}
    
    update_result = dev_manager.update_configuration(
        "app_config", updated_dev_config, "添加新功能配置"
    )
    
    print(f"\n开发环境配置更新:")
    print(f"  变更数量: {update_result['change_summary']['total_changes']}")
    print(f"  新增字段: {update_result['change_summary']['added_keys']}")
    print(f"  修改字段: {update_result['change_summary']['modified_keys']}")
    
    # 同步到生产环境
    sync_result = dev_manager.sync_config_between_environments(
        "app_config", prod_manager, "diff"
    )
    
    print(f"\n同步到生产环境: {sync_result['success']}")
    if sync_result['success']:
        print(f"  变更数量: {sync_result['change_summary']['total_changes']}")
    
    # 验证配置一致性
    dev_consistency = dev_manager.validate_config_consistency()
    prod_consistency = prod_manager.validate_config_consistency()
    
    print(f"\n配置一致性检查:")
    print(f"  开发环境: {'通过' if dev_consistency['is_consistent'] else '失败'}")
    print(f"  生产环境: {'通过' if prod_consistency['is_consistent'] else '失败'}")
    
    if not prod_consistency['is_consistent']:
        print(f"  生产环境问题: {prod_consistency['issues']}")
    
    # 回滚演示
    rollback_result = dev_manager.rollback_configuration("app_config", 1)
    print(f"\n配置回滚: {rollback_result['success']}")

# 运行演示
demo_config_management()
```

### 常见问题解决方案

**Q1: 如何处理大型数据结构的差分计算性能问题？**

A1: 使用分层差分和缓存优化：

```python
from agently_format.core.diff import DiffEngine
from typing import Dict, Any
import hashlib
import json

class OptimizedDiffEngine:
    """优化的差分引擎"""
    
    def __init__(self):
        self.diff_engine = DiffEngine()
        self.hash_cache = {}  # 哈希缓存
        self.diff_cache = {}  # 差分缓存
    
    def compute_hash(self, data: Dict[str, Any]) -> str:
        """计算数据哈希"""
        data_str = json.dumps(data, sort_keys=True)
        return hashlib.md5(data_str.encode()).hexdigest()
    
    def compute_optimized_diff(self, old_data: Dict[str, Any], 
                             new_data: Dict[str, Any]) -> Dict[str, Any]:
        """优化的差分计算"""
        old_hash = self.compute_hash(old_data)
        new_hash = self.compute_hash(new_data)
        
        # 检查缓存
        cache_key = f"{old_hash}:{new_hash}"
        if cache_key in self.diff_cache:
            return self.diff_cache[cache_key]
        
        # 如果哈希相同，无需计算差分
        if old_hash == new_hash:
            result = {"changes": [], "unchanged": True}
            self.diff_cache[cache_key] = result
            return result
        
        # 分层处理大型结构
        if len(json.dumps(old_data)) > 10000:  # 大于10KB
            result = self.compute_hierarchical_diff(old_data, new_data)
        else:
            result = self.diff_engine.compute_diff(old_data, new_data)
        
        # 缓存结果
        self.diff_cache[cache_key] = result
        return result
    
    def compute_hierarchical_diff(self, old_data: Dict[str, Any], 
                                new_data: Dict[str, Any]) -> Dict[str, Any]:
        """分层差分计算"""
        changes = []
        
        # 先比较顶层键
        old_keys = set(old_data.keys())
        new_keys = set(new_data.keys())
        
        # 处理删除的键
        for key in old_keys - new_keys:
            changes.append({
                "type": "delete",
                "path": key,
                "old_value": old_data[key]
            })
        
        # 处理新增的键
        for key in new_keys - old_keys:
            changes.append({
                "type": "add",
                "path": key,
                "new_value": new_data[key]
            })
        
        # 处理修改的键
        for key in old_keys & new_keys:
            old_value = old_data[key]
            new_value = new_data[key]
            
            if isinstance(old_value, dict) and isinstance(new_value, dict):
                # 递归处理嵌套字典
                sub_diff = self.compute_optimized_diff(old_value, new_value)
                for change in sub_diff.get("changes", []):
                    change["path"] = f"{key}.{change['path']}"
                    changes.append(change)
            elif old_value != new_value:
                changes.append({
                    "type": "modify",
                    "path": key,
                    "old_value": old_value,
                    "new_value": new_value
                })
        
        return {"changes": changes}
```

**Q2: 如何处理差分应用时的冲突？**

A2: 实现冲突检测和解决机制：

```python
from agently_format.core.diff import DiffEngine
from typing import Dict, Any, List, Optional
from enum import Enum

class ConflictResolution(Enum):
    """冲突解决策略"""
    MANUAL = "manual"  # 手动解决
    SOURCE_WINS = "source_wins"  # 源数据优先
    TARGET_WINS = "target_wins"  # 目标数据优先
    MERGE = "merge"  # 尝试合并

class ConflictAwareDiffEngine:
    """支持冲突处理的差分引擎"""
    
    def __init__(self):
        self.diff_engine = DiffEngine()
    
    def apply_diff_with_conflict_detection(self, 
                                         target_data: Dict[str, Any],
                                         diff: Dict[str, Any],
                                         current_data: Dict[str, Any] = None,
                                         resolution: ConflictResolution = ConflictResolution.MANUAL) -> Dict[str, Any]:
        """应用差分并检测冲突"""
        if current_data is None:
            current_data = target_data
        
        conflicts = self.detect_conflicts(target_data, diff, current_data)
        
        if not conflicts:
            # 无冲突，直接应用
            result_data = self.diff_engine.apply_diff(target_data, diff)
            return {
                "success": True,
                "data": result_data,
                "conflicts": [],
                "resolution_applied": None
            }
        
        # 有冲突，根据策略处理
        if resolution == ConflictResolution.MANUAL:
            return {
                "success": False,
                "data": target_data,
                "conflicts": conflicts,
                "resolution_applied": None,
                "message": "检测到冲突，需要手动解决"
            }
        
        # 自动解决冲突
        resolved_diff = self.resolve_conflicts(diff, conflicts, resolution)
        result_data = self.diff_engine.apply_diff(target_data, resolved_diff)
        
        return {
            "success": True,
            "data": result_data,
            "conflicts": conflicts,
            "resolution_applied": resolution.value,
            "message": f"使用 {resolution.value} 策略解决了 {len(conflicts)} 个冲突"
        }
    
    def detect_conflicts(self, target_data: Dict[str, Any], 
                        diff: Dict[str, Any], 
                        current_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """检测冲突"""
        conflicts = []
        
        for change in diff.get("changes", []):
            path = change.get("path", "")
            change_type = change.get("type")
            
            # 获取当前路径的值
            current_value = self.get_value_by_path(current_data, path)
            target_value = self.get_value_by_path(target_data, path)
            
            # 检测冲突
            if change_type == "modify":
                expected_old_value = change.get("old_value")
                if current_value != expected_old_value:
                    conflicts.append({
                        "path": path,
                        "type": "modify_conflict",
                        "expected_old_value": expected_old_value,
                        "actual_current_value": current_value,
                        "new_value": change.get("new_value"),
                        "message": f"路径 {path} 的当前值与期望的旧值不匹配"
                    })
            
            elif change_type == "delete":
                if current_value is None:
                    conflicts.append({
                        "path": path,
                        "type": "delete_conflict",
                        "message": f"路径 {path} 已经不存在，无法删除"
                    })
            
            elif change_type == "add":
                if current_value is not None:
                    conflicts.append({
                        "path": path,
                        "type": "add_conflict",
                        "existing_value": current_value,
                        "new_value": change.get("new_value"),
                        "message": f"路径 {path} 已存在值，无法添加"
                    })
        
        return conflicts
    
    def resolve_conflicts(self, diff: Dict[str, Any], 
                         conflicts: List[Dict[str, Any]], 
                         resolution: ConflictResolution) -> Dict[str, Any]:
        """解决冲突"""
        resolved_diff = diff.copy()
        conflict_paths = {conflict["path"] for conflict in conflicts}
        
        if resolution == ConflictResolution.SOURCE_WINS:
            # 源数据优先，保持原差分不变
            pass
        
        elif resolution == ConflictResolution.TARGET_WINS:
            # 目标数据优先，移除冲突的变更
            resolved_diff["changes"] = [
                change for change in diff.get("changes", [])
                if change.get("path") not in conflict_paths
            ]
        
        elif resolution == ConflictResolution.MERGE:
            # 尝试合并，这里简化为源数据优先
            # 实际应用中可以实现更复杂的合并逻辑
            pass
        
        return resolved_diff
    
    def get_value_by_path(self, data: Dict[str, Any], path: str) -> Any:
        """根据路径获取值"""
        if not path:
            return data
        
        keys = path.split(".")
        current = data
        
        try:
            for key in keys:
                if isinstance(current, dict) and key in current:
                    current = current[key]
                else:
                    return None
            return current
        except (KeyError, TypeError):
            return None
```

---

## 6. 多模型适配器最佳实践

### 核心功能概述

多模型适配器提供统一的接口来处理不同AI模型的输入输出格式，支持模型切换、参数适配、响应格式化等功能。

### 应用场景1：AI模型统一管理

**场景描述**：在应用中集成多个AI模型，提供统一的调用接口。

```python
from agently_format.core.adapters import ModelAdapter
from typing import Dict, Any, List, Optional, Union
from abc import ABC, abstractmethod
import json
import time
from datetime import datetime

class BaseModelProvider(ABC):
    """模型提供者基类"""
    
    @abstractmethod
    def generate_response(self, prompt: str, **kwargs) -> Dict[str, Any]:
        """生成响应"""
        pass
    
    @abstractmethod
    def get_model_info(self) -> Dict[str, Any]:
        """获取模型信息"""
        pass

class OpenAIProvider(BaseModelProvider):
    """OpenAI模型提供者"""
    
    def __init__(self, api_key: str, model_name: str = "gpt-3.5-turbo"):
        self.api_key = api_key
        self.model_name = model_name
    
    def generate_response(self, prompt: str, **kwargs) -> Dict[str, Any]:
        """生成响应（模拟）"""
        # 模拟API调用
        time.sleep(0.1)  # 模拟网络延迟
        
        return {
            "model": self.model_name,
            "response": f"OpenAI响应: {prompt[:50]}...",
            "usage": {
                "prompt_tokens": len(prompt.split()),
                "completion_tokens": 20,
                "total_tokens": len(prompt.split()) + 20
            },
            "finish_reason": "stop"
        }
    
    def get_model_info(self) -> Dict[str, Any]:
        return {
            "provider": "OpenAI",
            "model": self.model_name,
            "max_tokens": 4096,
            "supports_streaming": True
        }

class AnthropicProvider(BaseModelProvider):
    """Anthropic模型提供者"""
    
    def __init__(self, api_key: str, model_name: str = "claude-3-sonnet"):
        self.api_key = api_key
        self.model_name = model_name
    
    def generate_response(self, prompt: str, **kwargs) -> Dict[str, Any]:
        """生成响应（模拟）"""
        time.sleep(0.15)  # 模拟网络延迟
        
        return {
            "model": self.model_name,
            "content": f"Claude响应: {prompt[:50]}...",
            "stop_reason": "end_turn",
            "usage": {
                "input_tokens": len(prompt.split()),
                "output_tokens": 25
            }
        }
    
    def get_model_info(self) -> Dict[str, Any]:
        return {
            "provider": "Anthropic",
            "model": self.model_name,
            "max_tokens": 8192,
            "supports_streaming": True
        }

class UnifiedModelManager:
    """统一模型管理器"""
    
    def __init__(self):
        self.providers = {}  # provider_name -> provider_instance
        self.adapters = {}   # provider_name -> adapter_instance
        self.default_provider = None
        self.usage_stats = {}  # 使用统计
    
    def register_provider(self, name: str, provider: BaseModelProvider, 
                         adapter: ModelAdapter = None):
        """注册模型提供者"""
        self.providers[name] = provider
        
        if adapter:
            self.adapters[name] = adapter
        else:
            # 使用默认适配器
            self.adapters[name] = self.create_default_adapter(name, provider)
        
        if self.default_provider is None:
            self.default_provider = name
        
        # 初始化使用统计
        self.usage_stats[name] = {
            "total_requests": 0,
            "total_tokens": 0,
            "total_cost": 0.0,
            "average_response_time": 0.0,
            "error_count": 0
        }
    
    def create_default_adapter(self, provider_name: str, 
                             provider: BaseModelProvider) -> ModelAdapter:
        """创建默认适配器"""
        return ModelAdapter(
            input_formatter=self.get_input_formatter(provider_name),
            output_formatter=self.get_output_formatter(provider_name),
            error_handler=self.get_error_handler(provider_name)
        )
    
    def get_input_formatter(self, provider_name: str):
        """获取输入格式化器"""
        def format_input(prompt: str, **kwargs) -> Dict[str, Any]:
            if provider_name == "openai":
                return {
                    "messages": [{"role": "user", "content": prompt}],
                    "model": kwargs.get("model", "gpt-3.5-turbo"),
                    "max_tokens": kwargs.get("max_tokens", 1000),
                    "temperature": kwargs.get("temperature", 0.7)
                }
            elif provider_name == "anthropic":
                return {
                    "prompt": f"Human: {prompt}\n\nAssistant:",
                    "model": kwargs.get("model", "claude-3-sonnet"),
                    "max_tokens_to_sample": kwargs.get("max_tokens", 1000),
                    "temperature": kwargs.get("temperature", 0.7)
                }
            else:
                return {"prompt": prompt, **kwargs}
        
        return format_input
    
    def get_output_formatter(self, provider_name: str):
        """获取输出格式化器"""
        def format_output(response: Dict[str, Any]) -> Dict[str, Any]:
            if provider_name == "openai":
                return {
                    "text": response.get("response", ""),
                    "model": response.get("model"),
                    "usage": response.get("usage", {}),
                    "finish_reason": response.get("finish_reason")
                }
            elif provider_name == "anthropic":
                return {
                    "text": response.get("content", ""),
                    "model": response.get("model"),
                    "usage": {
                        "prompt_tokens": response.get("usage", {}).get("input_tokens", 0),
                        "completion_tokens": response.get("usage", {}).get("output_tokens", 0),
                        "total_tokens": response.get("usage", {}).get("input_tokens", 0) + 
                                       response.get("usage", {}).get("output_tokens", 0)
                    },
                    "finish_reason": response.get("stop_reason")
                }
            else:
                return response
        
        return format_output
    
    def get_error_handler(self, provider_name: str):
        """获取错误处理器"""
        def handle_error(error: Exception) -> Dict[str, Any]:
            return {
                "error": True,
                "provider": provider_name,
                "error_type": type(error).__name__,
                "error_message": str(error),
                "timestamp": datetime.now().isoformat()
            }
        
        return handle_error
    
    def generate_response(self, prompt: str, provider: str = None, 
                         **kwargs) -> Dict[str, Any]:
        """生成响应"""
        if provider is None:
            provider = self.default_provider
        
        if provider not in self.providers:
            return {
                "error": True,
                "message": f"未知的提供者: {provider}",
                "available_providers": list(self.providers.keys())
            }
        
        start_time = time.time()
        
        try:
            # 获取提供者和适配器
            provider_instance = self.providers[provider]
            adapter = self.adapters[provider]
            
            # 格式化输入
            formatted_input = adapter.input_formatter(prompt, **kwargs)
            
            # 调用模型
            raw_response = provider_instance.generate_response(prompt, **formatted_input)
            
            # 格式化输出
            formatted_response = adapter.output_formatter(raw_response)
            
            # 更新统计信息
            response_time = time.time() - start_time
            self.update_usage_stats(provider, formatted_response, response_time)
            
            # 添加元数据
            formatted_response.update({
                "provider": provider,
                "response_time": response_time,
                "timestamp": datetime.now().isoformat()
            })
            
            return formatted_response
        
        except Exception as e:
            # 错误处理
            adapter = self.adapters[provider]
            error_response = adapter.error_handler(e)
            
            # 更新错误统计
            self.usage_stats[provider]["error_count"] += 1
            
            return error_response
    
    def update_usage_stats(self, provider: str, response: Dict[str, Any], 
                          response_time: float):
        """更新使用统计"""
        stats = self.usage_stats[provider]
        
        stats["total_requests"] += 1
        
        usage = response.get("usage", {})
        total_tokens = usage.get("total_tokens", 0)
        stats["total_tokens"] += total_tokens
        
        # 计算平均响应时间
        current_avg = stats["average_response_time"]
        total_requests = stats["total_requests"]
        stats["average_response_time"] = (
            (current_avg * (total_requests - 1) + response_time) / total_requests
        )
        
        # 估算成本（简化计算）
        cost_per_token = self.get_cost_per_token(provider)
        stats["total_cost"] += total_tokens * cost_per_token
    
    def get_cost_per_token(self, provider: str) -> float:
        """获取每token成本（简化）"""
        cost_map = {
            "openai": 0.0001,
            "anthropic": 0.00015,
            "default": 0.0001
        }
        return cost_map.get(provider, cost_map["default"])
    
    def get_usage_report(self) -> Dict[str, Any]:
        """获取使用报告"""
        total_requests = sum(stats["total_requests"] for stats in self.usage_stats.values())
        total_cost = sum(stats["total_cost"] for stats in self.usage_stats.values())
        
        return {
            "summary": {
                "total_requests": total_requests,
                "total_cost": total_cost,
                "active_providers": len(self.providers)
            },
            "by_provider": self.usage_stats,
            "recommendations": self.generate_recommendations()
        }
    
    def generate_recommendations(self) -> List[str]:
        """生成优化建议"""
        recommendations = []
        
        # 分析成本效率
        cost_efficiency = {}
        for provider, stats in self.usage_stats.items():
            if stats["total_requests"] > 0:
                cost_per_request = stats["total_cost"] / stats["total_requests"]
                cost_efficiency[provider] = cost_per_request
        
        if cost_efficiency:
            cheapest = min(cost_efficiency, key=cost_efficiency.get)
            most_expensive = max(cost_efficiency, key=cost_efficiency.get)
            
            if cost_efficiency[most_expensive] > cost_efficiency[cheapest] * 1.5:
                recommendations.append(
                    f"考虑更多使用 {cheapest} 提供者，成本效率更高"
                )
        
        # 分析响应时间
        response_times = {
            provider: stats["average_response_time"]
            for provider, stats in self.usage_stats.items()
            if stats["total_requests"] > 0
        }
        
        if response_times:
            fastest = min(response_times, key=response_times.get)
            recommendations.append(
                f"{fastest} 提供者响应时间最快，适合实时应用"
            )
        
        return recommendations

# 使用示例
def demo_unified_model_management():
    """演示统一模型管理"""
    # 创建模型管理器
    manager = UnifiedModelManager()
    
    # 注册提供者
    openai_provider = OpenAIProvider("fake-api-key")
    anthropic_provider = AnthropicProvider("fake-api-key")
    
    manager.register_provider("openai", openai_provider)
    manager.register_provider("anthropic", anthropic_provider)
    
    print("=== 统一模型管理演示 ===")
    
    # 测试不同提供者
    test_prompt = "请解释什么是机器学习"
    
    # 使用OpenAI
    response1 = manager.generate_response(test_prompt, provider="openai")
    print(f"OpenAI响应: {response1.get('text', 'N/A')[:50]}...")
    print(f"响应时间: {response1.get('response_time', 0):.3f}s")
    
    # 使用Anthropic
    response2 = manager.generate_response(test_prompt, provider="anthropic")
    print(f"\nAnthropic响应: {response2.get('text', 'N/A')[:50]}...")
    print(f"响应时间: {response2.get('response_time', 0):.3f}s")
    
    # 使用默认提供者
    response3 = manager.generate_response("另一个测试问题")
    print(f"\n默认提供者响应: {response3.get('text', 'N/A')[:50]}...")
    
    # 查看使用报告
    print("\n=== 使用报告 ===")
    report = manager.get_usage_report()
    print(f"总请求数: {report['summary']['total_requests']}")
    print(f"总成本: ${report['summary']['total_cost']:.4f}")
    
    print("\n各提供者统计:")
    for provider, stats in report["by_provider"].items():
        if stats["total_requests"] > 0:
            print(f"  {provider}: {stats['total_requests']}次请求, "
                  f"平均响应时间 {stats['average_response_time']:.3f}s")
    
    if report["recommendations"]:
        print("\n优化建议:")
        for rec in report["recommendations"]:
            print(f"  - {rec}")

# 运行演示
demo_unified_model_management()
```

### 应用场景2：智能路由和负载均衡

**场景描述**：根据请求类型、模型性能和成本自动选择最适合的模型。

```python
from agently_format.core.adapters import ModelAdapter
from typing import Dict, Any, List, Optional
from enum import Enum
import random
import time

class RequestType(Enum):
    """请求类型"""
    SIMPLE_QA = "simple_qa"  # 简单问答
    COMPLEX_REASONING = "complex_reasoning"  # 复杂推理
    CODE_GENERATION = "code_generation"  # 代码生成
    CREATIVE_WRITING = "creative_writing"  # 创意写作
    DATA_ANALYSIS = "data_analysis"  # 数据分析

class RoutingStrategy(Enum):
    """路由策略"""
    COST_OPTIMIZED = "cost_optimized"  # 成本优化
    PERFORMANCE_OPTIMIZED = "performance_optimized"  # 性能优化
    BALANCED = "balanced"  # 平衡策略
    ROUND_ROBIN = "round_robin"  # 轮询

class IntelligentModelRouter:
    """智能模型路由器"""
    
    def __init__(self, model_manager):
        self.model_manager = model_manager
        self.model_capabilities = {}  # 模型能力评分
        self.model_costs = {}  # 模型成本
        self.model_performance = {}  # 模型性能指标
        self.request_history = []  # 请求历史
        self.round_robin_index = 0  # 轮询索引
        
        # 初始化模型配置
        self.initialize_model_configs()
    
    def initialize_model_configs(self):
        """初始化模型配置"""
        # 模型能力评分（1-10分）
        self.model_capabilities = {
            "openai": {
                RequestType.SIMPLE_QA: 8,
                RequestType.COMPLEX_REASONING: 9,
                RequestType.CODE_GENERATION: 9,
                RequestType.CREATIVE_WRITING: 8,
                RequestType.DATA_ANALYSIS: 8
            },
            "anthropic": {
                RequestType.SIMPLE_QA: 9,
                RequestType.COMPLEX_REASONING: 10,
                RequestType.CODE_GENERATION: 8,
                RequestType.CREATIVE_WRITING: 9,
                RequestType.DATA_ANALYSIS: 9
            }
        }
        
        # 模型成本（每1000 tokens）
        self.model_costs = {
            "openai": 0.002,
            "anthropic": 0.003
        }
        
        # 模型性能指标
        self.model_performance = {
            "openai": {
                "average_response_time": 1.2,
                "reliability_score": 0.95,
                "throughput": 100  # requests per minute
            },
            "anthropic": {
                "average_response_time": 1.5,
                "reliability_score": 0.98,
                "throughput": 80
            }
        }
    
    def classify_request(self, prompt: str) -> RequestType:
        """分类请求类型"""
        prompt_lower = prompt.lower()
        
        # 简单的关键词匹配分类
        if any(keyword in prompt_lower for keyword in ["代码", "编程", "函数", "class", "def"]):
            return RequestType.CODE_GENERATION
        elif any(keyword in prompt_lower for keyword in ["分析", "数据", "统计", "图表"]):
            return RequestType.DATA_ANALYSIS
        elif any(keyword in prompt_lower for keyword in ["故事", "创作", "诗歌", "小说"]):
            return RequestType.CREATIVE_WRITING
        elif len(prompt.split()) > 50:  # 长文本通常需要复杂推理
            return RequestType.COMPLEX_REASONING
        else:
            return RequestType.SIMPLE_QA
    
    def select_model(self, request_type: RequestType, 
                    strategy: RoutingStrategy = RoutingStrategy.BALANCED) -> str:
        """选择最适合的模型"""
        available_providers = list(self.model_manager.providers.keys())
        
        if not available_providers:
            raise ValueError("没有可用的模型提供者")
        
        if strategy == RoutingStrategy.ROUND_ROBIN:
            # 轮询策略
            selected = available_providers[self.round_robin_index % len(available_providers)]
            self.round_robin_index += 1
            return selected
        
        # 计算每个模型的得分
        model_scores = {}
        
        for provider in available_providers:
            capability_score = self.model_capabilities.get(provider, {}).get(request_type, 5)
            cost_score = 10 - (self.model_costs.get(provider, 0.002) * 1000)  # 成本越低分数越高
            performance_score = (
                (10 - self.model_performance.get(provider, {}).get("average_response_time", 2)) +
                (self.model_performance.get(provider, {}).get("reliability_score", 0.9) * 10)
            ) / 2
            
            if strategy == RoutingStrategy.COST_OPTIMIZED:
                total_score = cost_score * 0.6 + capability_score * 0.3 + performance_score * 0.1
            elif strategy == RoutingStrategy.PERFORMANCE_OPTIMIZED:
                total_score = performance_score * 0.6 + capability_score * 0.3 + cost_score * 0.1
            else:  # BALANCED
                total_score = capability_score * 0.4 + cost_score * 0.3 + performance_score * 0.3
            
            model_scores[provider] = total_score
        
        # 选择得分最高的模型
        return max(model_scores, key=model_scores.get)
    
    def route_request(self, prompt: str, 
                     strategy: RoutingStrategy = RoutingStrategy.BALANCED,
                     **kwargs) -> Dict[str, Any]:
        """路由请求到最适合的模型"""
        # 分类请求
        request_type = self.classify_request(prompt)
        
        # 选择模型
        selected_provider = self.select_model(request_type, strategy)
        
        # 记录路由决策
        routing_info = {
            "request_type": request_type.value,
            "selected_provider": selected_provider,
            "strategy": strategy.value,
            "timestamp": time.time()
        }
        
        # 生成响应
        response = self.model_manager.generate_response(
            prompt, provider=selected_provider, **kwargs
        )
        
        # 添加路由信息
        response["routing_info"] = routing_info
        
        # 记录历史
        self.request_history.append({
            "prompt": prompt[:100],  # 只保存前100个字符
            "routing_info": routing_info,
            "response_time": response.get("response_time", 0),
            "success": not response.get("error", False)
        })
        
        return response
    
    def get_routing_analytics(self) -> Dict[str, Any]:
        """获取路由分析报告"""
        if not self.request_history:
            return {"message": "暂无路由历史数据"}
        
        # 统计各种指标
        total_requests = len(self.request_history)
        success_requests = sum(1 for req in self.request_history if req["success"])
        
        # 按提供者统计
        provider_stats = {}
        request_type_stats = {}
        
        for req in self.request_history:
            provider = req["routing_info"]["selected_provider"]
            req_type = req["routing_info"]["request_type"]
            
            if provider not in provider_stats:
                provider_stats[provider] = {"count": 0, "total_time": 0, "success_count": 0}
            
            provider_stats[provider]["count"] += 1
            provider_stats[provider]["total_time"] += req["response_time"]
            if req["success"]:
                provider_stats[provider]["success_count"] += 1
            
            if req_type not in request_type_stats:
                request_type_stats[req_type] = 0
            request_type_stats[req_type] += 1
        
        # 计算平均响应时间
        for provider in provider_stats:
            stats = provider_stats[provider]
            stats["average_response_time"] = stats["total_time"] / stats["count"]
            stats["success_rate"] = stats["success_count"] / stats["count"]
        
        return {
            "summary": {
                "total_requests": total_requests,
                "success_rate": success_requests / total_requests,
                "average_response_time": sum(req["response_time"] for req in self.request_history) / total_requests
            },
            "provider_distribution": provider_stats,
            "request_type_distribution": request_type_stats,
            "recommendations": self.generate_routing_recommendations(provider_stats)
        }
    
    def generate_routing_recommendations(self, provider_stats: Dict[str, Any]) -> List[str]:
        """生成路由优化建议"""
        recommendations = []
        
        if not provider_stats:
            return recommendations
        
        # 找出性能最好的提供者
        best_provider = min(provider_stats.keys(), 
                           key=lambda p: provider_stats[p]["average_response_time"])
        
        # 找出成功率最高的提供者
        most_reliable = max(provider_stats.keys(), 
                           key=lambda p: provider_stats[p]["success_rate"])
        
        recommendations.append(f"{best_provider} 提供者响应时间最快")
        recommendations.append(f"{most_reliable} 提供者成功率最高")
        
        # 检查负载分布
        total_requests = sum(stats["count"] for stats in provider_stats.values())
        for provider, stats in provider_stats.items():
            usage_percentage = (stats["count"] / total_requests) * 100
            if usage_percentage > 80:
                recommendations.append(f"{provider} 提供者负载过高 ({usage_percentage:.1f}%)，建议分散负载")
        
        return recommendations

# 使用示例
def demo_intelligent_routing():
    """演示智能路由"""
    from agently_format.core.adapters import ModelAdapter
    
    # 创建模型管理器（使用之前的代码）
    manager = UnifiedModelManager()
    
    # 注册提供者
    openai_provider = OpenAIProvider("fake-api-key")
    anthropic_provider = AnthropicProvider("fake-api-key")
    
    manager.register_provider("openai", openai_provider)
    manager.register_provider("anthropic", anthropic_provider)
    
    # 创建智能路由器
    router = IntelligentModelRouter(manager)
    
    print("=== 智能路由演示 ===")
    
    # 测试不同类型的请求
    test_requests = [
        "请写一个Python函数来计算斐波那契数列",
        "分析一下这组销售数据的趋势",
        "写一个关于未来城市的科幻故事",
        "什么是机器学习？",
        "请详细解释量子计算的原理和应用前景，包括其在密码学、优化问题和模拟等领域的潜在影响"
    ]
    
    strategies = [RoutingStrategy.BALANCED, RoutingStrategy.COST_OPTIMIZED, RoutingStrategy.PERFORMANCE_OPTIMIZED]
    
    for i, prompt in enumerate(test_requests):
        strategy = strategies[i % len(strategies)]
        
        print(f"\n请求 {i+1}: {prompt[:50]}...")
        
        response = router.route_request(prompt, strategy=strategy)
        
        routing_info = response.get("routing_info", {})
        print(f"请求类型: {routing_info.get('request_type')}")
        print(f"选择的提供者: {routing_info.get('selected_provider')}")
        print(f"路由策略: {routing_info.get('strategy')}")
        print(f"响应时间: {response.get('response_time', 0):.3f}s")
    
    # 查看路由分析
    print("\n=== 路由分析报告 ===")
    analytics = router.get_routing_analytics()
    
    summary = analytics["summary"]
    print(f"总请求数: {summary['total_requests']}")
    print(f"成功率: {summary['success_rate']:.2%}")
    print(f"平均响应时间: {summary['average_response_time']:.3f}s")
    
    print("\n提供者分布:")
    for provider, stats in analytics["provider_distribution"].items():
        print(f"  {provider}: {stats['count']}次请求, "
              f"平均响应时间 {stats['average_response_time']:.3f}s, "
              f"成功率 {stats['success_rate']:.2%}")
    
    print("\n请求类型分布:")
    for req_type, count in analytics["request_type_distribution"].items():
        print(f"  {req_type}: {count}次")
    
    if analytics["recommendations"]:
        print("\n优化建议:")
        for rec in analytics["recommendations"]:
            print(f"  - {rec}")

# 运行演示
demo_intelligent_routing()
```

### 应用场景3：模型性能监控和自动切换

**场景描述**：监控模型性能，在检测到异常时自动切换到备用模型。

```python
from agently_format.core.adapters import ModelAdapter
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
import time
import statistics
from collections import deque

@dataclass
class HealthMetrics:
    """健康指标"""
    response_time: float
    success_rate: float
    error_count: int
    total_requests: int
    last_error: Optional[str] = None
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()

class ModelHealthMonitor:
    """模型健康监控器"""
    
    def __init__(self, model_manager, check_interval: int = 60):
        self.model_manager = model_manager
        self.check_interval = check_interval  # 检查间隔（秒）
        self.health_history = {}  # provider -> deque of HealthMetrics
        self.alert_thresholds = {
            "max_response_time": 5.0,  # 最大响应时间（秒）
            "min_success_rate": 0.8,   # 最小成功率
            "max_error_rate": 0.2      # 最大错误率
        }
        self.failover_enabled = True
        self.primary_provider = None
        self.backup_providers = []
        self.current_provider = None
        self.alert_callbacks = []  # 告警回调函数
        
        # 初始化健康历史
        for provider in model_manager.providers.keys():
            self.health_history[provider] = deque(maxlen=100)  # 保留最近100条记录
    
    def set_failover_config(self, primary: str, backups: List[str]):
        """设置故障转移配置"""
        self.primary_provider = primary
        self.backup_providers = backups
        self.current_provider = primary
    
    def add_alert_callback(self, callback: Callable[[str, Dict[str, Any]], None]):
        """添加告警回调"""
        self.alert_callbacks.append(callback)
    
    def record_request(self, provider: str, response_time: float, 
                      success: bool, error_message: str = None):
        """记录请求结果"""
        if provider not in self.health_history:
            self.health_history[provider] = deque(maxlen=100)
        
        # 计算最近的指标
        recent_records = list(self.health_history[provider])[-20:]  # 最近20条记录
        
        if recent_records:
            recent_success_count = sum(1 for r in recent_records if r.success_rate > 0)
            recent_total = len(recent_records)
            success_rate = recent_success_count / recent_total
            error_count = recent_total - recent_success_count
        else:
            success_rate = 1.0 if success else 0.0
            error_count = 0 if success else 1
        
        # 创建健康指标
        metrics = HealthMetrics(
            response_time=response_time,
            success_rate=success_rate,
            error_count=error_count,
            total_requests=len(recent_records) + 1,
            last_error=error_message if not success else None
        )
        
        self.health_history[provider].append(metrics)
        
        # 检查健康状态
        self.check_health(provider, metrics)
    
    def check_health(self, provider: str, metrics: HealthMetrics):
        """检查提供者健康状态"""
        alerts = []
        
        # 检查响应时间
        if metrics.response_time > self.alert_thresholds["max_response_time"]:
            alerts.append({
                "type": "high_response_time",
                "message": f"{provider} 响应时间过高: {metrics.response_time:.2f}s",
                "severity": "warning"
            })
        
        # 检查成功率
        if metrics.success_rate < self.alert_thresholds["min_success_rate"]:
            alerts.append({
                "type": "low_success_rate",
                "message": f"{provider} 成功率过低: {metrics.success_rate:.2%}",
                "severity": "critical"
            })
        
        # 检查错误率
        error_rate = metrics.error_count / metrics.total_requests
        if error_rate > self.alert_thresholds["max_error_rate"]:
            alerts.append({
                "type": "high_error_rate",
                "message": f"{provider} 错误率过高: {error_rate:.2%}",
                "severity": "critical"
            })
        
        # 触发告警和故障转移
        for alert in alerts:
            self.trigger_alert(provider, alert)
            
            # 如果是严重告警且启用了故障转移
            if (alert["severity"] == "critical" and 
                self.failover_enabled and 
                provider == self.current_provider):
                self.trigger_failover(provider, alert["message"])
    
    def trigger_alert(self, provider: str, alert: Dict[str, Any]):
        """触发告警"""
        alert_data = {
            "provider": provider,
            "timestamp": datetime.now().isoformat(),
            **alert
        }
        
        # 调用告警回调
        for callback in self.alert_callbacks:
            try:
                callback(provider, alert_data)
            except Exception as e:
                print(f"告警回调执行失败: {e}")
    
    def trigger_failover(self, failed_provider: str, reason: str):
        """触发故障转移"""
        if not self.backup_providers:
            print(f"无可用的备用提供者，无法从 {failed_provider} 故障转移")
            return
        
        # 选择最健康的备用提供者
        best_backup = self.select_best_backup()
        
        if best_backup:
            old_provider = self.current_provider
            self.current_provider = best_backup
            
            failover_alert = {
                "type": "failover",
                "message": f"从 {old_provider} 故障转移到 {best_backup}: {reason}",
                "severity": "info",
                "old_provider": old_provider,
                "new_provider": best_backup
            }
            
            self.trigger_alert("system", failover_alert)
            print(f"故障转移: {old_provider} -> {best_backup}")
    
    def select_best_backup(self) -> Optional[str]:
        """选择最佳备用提供者"""
        backup_scores = {}
        
        for provider in self.backup_providers:
            if provider not in self.health_history or not self.health_history[provider]:
                backup_scores[provider] = 0.5  # 默认分数
                continue
            
            recent_metrics = list(self.health_history[provider])[-10:]  # 最近10条记录
            
            if recent_metrics:
                avg_response_time = statistics.mean(m.response_time for m in recent_metrics)
                avg_success_rate = statistics.mean(m.success_rate for m in recent_metrics)
                
                # 计算健康分数（响应时间越低越好，成功率越高越好）
                time_score = max(0, 1 - (avg_response_time / 10))  # 10秒为最差
                success_score = avg_success_rate
                
                backup_scores[provider] = (time_score + success_score) / 2
            else:
                backup_scores[provider] = 0.5
        
        if backup_scores:
            return max(backup_scores, key=backup_scores.get)
        return None
    
    def get_current_provider(self) -> str:
        """获取当前活跃的提供者"""
        return self.current_provider or self.primary_provider
    
    def get_health_report(self) -> Dict[str, Any]:
        """获取健康报告"""
        report = {
            "current_provider": self.current_provider,
            "primary_provider": self.primary_provider,
            "backup_providers": self.backup_providers,
            "provider_health": {},
            "system_status": "healthy"
        }
        
        for provider, history in self.health_history.items():
            if not history:
                continue
            
            recent_metrics = list(history)[-10:]  # 最近10条记录
            
            if recent_metrics:
                avg_response_time = statistics.mean(m.response_time for m in recent_metrics)
                avg_success_rate = statistics.mean(m.success_rate for m in recent_metrics)
                total_requests = sum(m.total_requests for m in recent_metrics)
                
                # 判断健康状态
                is_healthy = (
                    avg_response_time <= self.alert_thresholds["max_response_time"] and
                    avg_success_rate >= self.alert_thresholds["min_success_rate"]
                )
                
                report["provider_health"][provider] = {
                    "status": "healthy" if is_healthy else "unhealthy",
                    "average_response_time": avg_response_time,
                    "average_success_rate": avg_success_rate,
                    "total_requests": total_requests,
                    "last_check": recent_metrics[-1].timestamp.isoformat()
                }
                
                if not is_healthy and provider == self.current_provider:
                    report["system_status"] = "degraded"
        
        return report

class MonitoredModelManager(UnifiedModelManager):
    """带监控的模型管理器"""
    
    def __init__(self):
        super().__init__()
        self.monitor = ModelHealthMonitor(self)
        
        # 设置默认告警回调
        self.monitor.add_alert_callback(self.default_alert_handler)
    
    def setup_failover(self, primary: str, backups: List[str]):
        """设置故障转移"""
        self.monitor.set_failover_config(primary, backups)
    
    def default_alert_handler(self, provider: str, alert_data: Dict[str, Any]):
        """默认告警处理器"""
        timestamp = alert_data.get("timestamp", "")
        message = alert_data.get("message", "")
        severity = alert_data.get("severity", "info")
        
        print(f"[{timestamp}] {severity.upper()}: {message}")
    
    def generate_response(self, prompt: str, provider: str = None, **kwargs) -> Dict[str, Any]:
        """生成响应（带监控）"""
        # 如果没有指定提供者，使用监控器推荐的提供者
        if provider is None:
            provider = self.monitor.get_current_provider() or self.default_provider
        
        start_time = time.time()
        
        try:
            response = super().generate_response(prompt, provider, **kwargs)
            
            # 记录成功请求
            response_time = time.time() - start_time
            self.monitor.record_request(provider, response_time, True)
            
            return response
        
        except Exception as e:
            # 记录失败请求
            response_time = time.time() - start_time
            self.monitor.record_request(provider, response_time, False, str(e))
            
            # 如果启用了故障转移，尝试使用备用提供者
            if (self.monitor.failover_enabled and 
                provider == self.monitor.current_provider and 
                self.monitor.backup_providers):
                
                backup_provider = self.monitor.select_best_backup()
                if backup_provider:
                    print(f"尝试使用备用提供者: {backup_provider}")
                    return self.generate_response(prompt, backup_provider, **kwargs)
            
            raise e
    
    def get_system_status(self) -> Dict[str, Any]:
        """获取系统状态"""
        health_report = self.monitor.get_health_report()
        usage_report = self.get_usage_report()
        
        return {
            "health": health_report,
            "usage": usage_report,
            "timestamp": datetime.now().isoformat()
        }

# 使用示例
def demo_health_monitoring():
    """演示健康监控"""
    # 创建带监控的模型管理器
    manager = MonitoredModelManager()
    
    # 注册提供者
    openai_provider = OpenAIProvider("fake-api-key")
    anthropic_provider = AnthropicProvider("fake-api-key")
    
    manager.register_provider("openai", openai_provider)
    manager.register_provider("anthropic", anthropic_provider)
    
    # 设置故障转移
    manager.setup_failover("openai", ["anthropic"])
    
    print("=== 健康监控演示 ===")
    
    # 模拟正常请求
    for i in range(5):
        try:
            response = manager.generate_response(f"测试请求 {i+1}")
            print(f"请求 {i+1} 成功: {response.get('provider')}")
        except Exception as e:
            print(f"请求 {i+1} 失败: {e}")
        
        time.sleep(0.1)  # 短暂延迟
    
    # 查看系统状态
    print("\n=== 系统状态报告 ===")
    status = manager.get_system_status()
    
    health = status["health"]
    print(f"当前提供者: {health['current_provider']}")
    print(f"系统状态: {health['system_status']}")
    
    print("\n提供者健康状态:")
    for provider, health_info in health["provider_health"].items():
        print(f"  {provider}: {health_info['status']} - "
              f"响应时间 {health_info['average_response_time']:.3f}s, "
              f"成功率 {health_info['average_success_rate']:.2%}")

# 运行演示
demo_health_monitoring()
```

### 常见问题解决方案

**Q1: 如何处理不同模型的API限制和配额管理？**

A1: 实现配额管理和限流机制：

```python
from agently_format.core.adapters import ModelAdapter
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from collections import defaultdict
import time
import threading

class QuotaManager:
    """配额管理器"""
    
    def __init__(self):
        self.provider_quotas = {}  # provider -> quota config
        self.usage_tracking = defaultdict(lambda: defaultdict(int))  # provider -> {period -> usage}
        self.rate_limits = {}  # provider -> rate limit config
        self.last_request_time = {}  # provider -> last request timestamp
        self.lock = threading.Lock()
    
    def set_quota(self, provider: str, daily_limit: int, monthly_limit: int):
        """设置配额限制"""
        self.provider_quotas[provider] = {
            "daily_limit": daily_limit,
            "monthly_limit": monthly_limit
        }
    
    def set_rate_limit(self, provider: str, requests_per_minute: int):
        """设置速率限制"""
        self.rate_limits[provider] = {
            "requests_per_minute": requests_per_minute,
            "min_interval": 60.0 / requests_per_minute  # 最小请求间隔
        }
    
    def check_quota(self, provider: str, tokens_to_use: int = 1) -> Dict[str, Any]:
        """检查配额是否可用"""
        with self.lock:
            now = datetime.now()
            today = now.strftime("%Y-%m-%d")
            this_month = now.strftime("%Y-%m")
            
            # 检查日配额
            daily_usage = self.usage_tracking[provider][f"daily_{today}"]
            daily_limit = self.provider_quotas.get(provider, {}).get("daily_limit", float('inf'))
            
            if daily_usage + tokens_to_use > daily_limit:
                return {
                    "allowed": False,
                    "reason": "daily_quota_exceeded",
                    "daily_usage": daily_usage,
                    "daily_limit": daily_limit
                }
            
            # 检查月配额
            monthly_usage = self.usage_tracking[provider][f"monthly_{this_month}"]
            monthly_limit = self.provider_quotas.get(provider, {}).get("monthly_limit", float('inf'))
            
            if monthly_usage + tokens_to_use > monthly_limit:
                return {
                    "allowed": False,
                    "reason": "monthly_quota_exceeded",
                    "monthly_usage": monthly_usage,
                    "monthly_limit": monthly_limit
                }
            
            return {
                "allowed": True,
                "daily_remaining": daily_limit - daily_usage,
                "monthly_remaining": monthly_limit - monthly_usage
            }
    
    def check_rate_limit(self, provider: str) -> Dict[str, Any]:
        """检查速率限制"""
        if provider not in self.rate_limits:
            return {"allowed": True, "wait_time": 0}
        
        with self.lock:
            now = time.time()
            last_request = self.last_request_time.get(provider, 0)
            min_interval = self.rate_limits[provider]["min_interval"]
            
            time_since_last = now - last_request
            
            if time_since_last < min_interval:
                wait_time = min_interval - time_since_last
                return {
                    "allowed": False,
                    "wait_time": wait_time,
                    "reason": "rate_limit_exceeded"
                }
            
            return {"allowed": True, "wait_time": 0}
    
    def record_usage(self, provider: str, tokens_used: int):
        """记录使用量"""
        with self.lock:
            now = datetime.now()
            today = now.strftime("%Y-%m-%d")
            this_month = now.strftime("%Y-%m")
            
            self.usage_tracking[provider][f"daily_{today}"] += tokens_used
            self.usage_tracking[provider][f"monthly_{this_month}"] += tokens_used
            self.last_request_time[provider] = time.time()
    
    def get_usage_summary(self) -> Dict[str, Any]:
        """获取使用量摘要"""
        summary = {}
        now = datetime.now()
        today = now.strftime("%Y-%m-%d")
        this_month = now.strftime("%Y-%m")
        
        for provider in self.provider_quotas:
            daily_usage = self.usage_tracking[provider].get(f"daily_{today}", 0)
            monthly_usage = self.usage_tracking[provider].get(f"monthly_{this_month}", 0)
            
            quotas = self.provider_quotas[provider]
            
            summary[provider] = {
                "daily": {
                    "used": daily_usage,
                    "limit": quotas["daily_limit"],
                    "remaining": quotas["daily_limit"] - daily_usage,
                    "usage_percentage": (daily_usage / quotas["daily_limit"]) * 100
                },
                "monthly": {
                    "used": monthly_usage,
                    "limit": quotas["monthly_limit"],
                    "remaining": quotas["monthly_limit"] - monthly_usage,
                    "usage_percentage": (monthly_usage / quotas["monthly_limit"]) * 100
                }
            }
        
        return summary

class QuotaAwareModelManager(UnifiedModelManager):
    """支持配额管理的模型管理器"""
    
    def __init__(self):
        super().__init__()
        self.quota_manager = QuotaManager()
        
        # 设置默认配额（示例）
        self.setup_default_quotas()
    
    def setup_default_quotas(self):
        """设置默认配额"""
        # OpenAI配额设置
        self.quota_manager.set_quota("openai", daily_limit=10000, monthly_limit=100000)
        self.quota_manager.set_rate_limit("openai", requests_per_minute=60)
        
        # Anthropic配额设置
        self.quota_manager.set_quota("anthropic", daily_limit=8000, monthly_limit=80000)
        self.quota_manager.set_rate_limit("anthropic", requests_per_minute=50)
    
    def generate_response(self, prompt: str, provider: str = None, **kwargs) -> Dict[str, Any]:
        """生成响应（带配额管理）"""
        if provider is None:
            provider = self.default_provider
        
        # 估算token使用量（简化计算）
        estimated_tokens = len(prompt.split()) + kwargs.get("max_tokens", 100)
        
        # 检查配额
        quota_check = self.quota_manager.check_quota(provider, estimated_tokens)
        if not quota_check["allowed"]:
            # 尝试使用其他提供者
            alternative_provider = self.find_alternative_provider(provider)
            if alternative_provider:
                print(f"配额不足，切换到 {alternative_provider}")
                return self.generate_response(prompt, alternative_provider, **kwargs)
            else:
                return {
                    "error": True,
                    "message": f"配额不足: {quota_check['reason']}",
                    "quota_info": quota_check
                }
        
        # 检查速率限制
        rate_check = self.quota_manager.check_rate_limit(provider)
        if not rate_check["allowed"]:
            wait_time = rate_check["wait_time"]
            print(f"速率限制，等待 {wait_time:.2f} 秒")
            time.sleep(wait_time)
        
        try:
            # 调用父类方法生成响应
            response = super().generate_response(prompt, provider, **kwargs)
            
            # 记录实际使用量
            actual_tokens = response.get("usage", {}).get("total_tokens", estimated_tokens)
            self.quota_manager.record_usage(provider, actual_tokens)
            
            # 添加配额信息
            response["quota_info"] = self.quota_manager.get_usage_summary().get(provider, {})
            
            return response
        
        except Exception as e:
            # 即使失败也要记录使用量（避免配额泄露）
            self.quota_manager.record_usage(provider, estimated_tokens // 2)
            raise e
    
    def find_alternative_provider(self, current_provider: str) -> Optional[str]:
        """寻找替代提供者"""
        for provider in self.providers.keys():
            if provider != current_provider:
                # 检查替代提供者的配额
                quota_check = self.quota_manager.check_quota(provider, 100)  # 检查小量配额
                if quota_check["allowed"]:
                    return provider
        return None
    
    def get_quota_report(self) -> Dict[str, Any]:
        """获取配额报告"""
        return {
            "usage_summary": self.quota_manager.get_usage_summary(),
            "timestamp": datetime.now().isoformat(),
            "recommendations": self.generate_quota_recommendations()
        }
    
    def generate_quota_recommendations(self) -> List[str]:
        """生成配额优化建议"""
        recommendations = []
        usage_summary = self.quota_manager.get_usage_summary()
        
        for provider, usage in usage_summary.items():
            daily_usage_pct = usage["daily"]["usage_percentage"]
            monthly_usage_pct = usage["monthly"]["usage_percentage"]
            
            if daily_usage_pct > 80:
                recommendations.append(f"{provider} 日配额使用率过高 ({daily_usage_pct:.1f}%)")
            
            if monthly_usage_pct > 90:
                recommendations.append(f"{provider} 月配额即将耗尽 ({monthly_usage_pct:.1f}%)")
            
            if daily_usage_pct < 20 and monthly_usage_pct < 20:
                recommendations.append(f"{provider} 配额利用率较低，可以考虑调整")
        
        return recommendations

# 使用示例
def demo_quota_management():
    """演示配额管理"""
    # 创建支持配额管理的模型管理器
    manager = QuotaAwareModelManager()
    
    # 注册提供者
    openai_provider = OpenAIProvider("fake-api-key")
    anthropic_provider = AnthropicProvider("fake-api-key")
    
    manager.register_provider("openai", openai_provider)
    manager.register_provider("anthropic", anthropic_provider)
    
    print("=== 配额管理演示 ===")
    
    # 模拟多次请求
    for i in range(3):
        try:
            response = manager.generate_response(
                f"测试请求 {i+1}: 请解释人工智能的发展历程",
                provider="openai"
            )
            
            print(f"\n请求 {i+1} 成功")
            print(f"使用的提供者: {response.get('provider')}")
            
            # 显示配额信息
            quota_info = response.get("quota_info", {})
            if quota_info:
                daily_info = quota_info.get("daily", {})
                print(f"日配额使用: {daily_info.get('used', 0)}/{daily_info.get('limit', 0)} "
                      f"({daily_info.get('usage_percentage', 0):.1f}%)")
        
        except Exception as e:
            print(f"请求 {i+1} 失败: {e}")
    
    # 查看配额报告
    print("\n=== 配额使用报告 ===")
    quota_report = manager.get_quota_report()
    
    for provider, usage in quota_report["usage_summary"].items():
        print(f"\n{provider} 提供者:")
        print(f"  日使用量: {usage['daily']['used']}/{usage['daily']['limit']} "
              f"({usage['daily']['usage_percentage']:.1f}%)")
        print(f"  月使用量: {usage['monthly']['used']}/{usage['monthly']['limit']} "
              f"({usage['monthly']['usage_percentage']:.1f}%)")
    
    if quota_report["recommendations"]:
        print("\n优化建议:")
        for rec in quota_report["recommendations"]:
            print(f"  - {rec}")

# 运行演示
demo_quota_management()
```

**Q2: 如何实现模型响应的缓存和优化？**

A2: 实现智能缓存机制：

```python
from agently_format.core.adapters import ModelAdapter
from typing import Dict, Any, Optional, Tuple
import hashlib
import json
import time
from datetime import datetime, timedelta
from collections import OrderedDict
import threading

class ResponseCache:
    """响应缓存管理器"""
    
    def __init__(self, max_size: int = 1000, ttl_seconds: int = 3600):
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self.cache = OrderedDict()  # LRU缓存
        self.access_times = {}  # 访问时间记录
        self.hit_count = 0
        self.miss_count = 0
        self.lock = threading.Lock()
    
    def generate_cache_key(self, prompt: str, provider: str, **kwargs) -> str:
        """生成缓存键"""
        # 创建包含所有相关参数的字典
        cache_data = {
            "prompt": prompt.strip().lower(),  # 标准化提示
            "provider": provider,
            "params": {k: v for k, v in sorted(kwargs.items()) if k in [
                "temperature", "max_tokens", "top_p", "frequency_penalty", "presence_penalty"
            ]}
        }
        
        # 生成哈希
        cache_str = json.dumps(cache_data, sort_keys=True)
        return hashlib.md5(cache_str.encode()).hexdigest()
    
    def get(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """获取缓存的响应"""
        with self.lock:
            if cache_key not in self.cache:
                self.miss_count += 1
                return None
            
            # 检查TTL
            cached_time = self.access_times.get(cache_key, 0)
            if time.time() - cached_time > self.ttl_seconds:
                # 缓存过期，删除
                del self.cache[cache_key]
                del self.access_times[cache_key]
                self.miss_count += 1
                return None
            
            # 缓存命中，移到最后（LRU）
            response = self.cache[cache_key]
            self.cache.move_to_end(cache_key)
            self.access_times[cache_key] = time.time()
            self.hit_count += 1
            
            # 添加缓存标记
            response_copy = response.copy()
            response_copy["from_cache"] = True
            response_copy["cache_hit_time"] = datetime.now().isoformat()
            
            return response_copy
    
    def put(self, cache_key: str, response: Dict[str, Any]):
        """存储响应到缓存"""
        with self.lock:
            # 如果缓存已满，删除最旧的条目
            if len(self.cache) >= self.max_size:
                oldest_key = next(iter(self.cache))
                del self.cache[oldest_key]
                del self.access_times[oldest_key]
            
            # 存储响应（移除一些不需要缓存的字段）
            cacheable_response = {k: v for k, v in response.items() 
                                if k not in ["response_time", "timestamp", "from_cache"]}
            
            self.cache[cache_key] = cacheable_response
            self.access_times[cache_key] = time.time()
    
    def invalidate_pattern(self, pattern: str):
        """根据模式失效缓存"""
        with self.lock:
            keys_to_remove = []
            for key in self.cache.keys():
                if pattern in key:
                    keys_to_remove.append(key)
            
            for key in keys_to_remove:
                del self.cache[key]
                del self.access_times[key]
    
    def clear(self):
        """清空缓存"""
        with self.lock:
            self.cache.clear()
            self.access_times.clear()
            self.hit_count = 0
            self.miss_count = 0
    
    def get_stats(self) -> Dict[str, Any]:
        """获取缓存统计信息"""
        total_requests = self.hit_count + self.miss_count
        hit_rate = (self.hit_count / total_requests * 100) if total_requests > 0 else 0
        
        return {
            "cache_size": len(self.cache),
            "max_size": self.max_size,
            "hit_count": self.hit_count,
            "miss_count": self.miss_count,
            "hit_rate": hit_rate,
            "ttl_seconds": self.ttl_seconds
        }

class CachedModelManager(UnifiedModelManager):
    """支持缓存的模型管理器"""
    
    def __init__(self, cache_size: int = 1000, cache_ttl: int = 3600):
        super().__init__()
        self.cache = ResponseCache(cache_size, cache_ttl)
        self.cache_enabled = True
        self.cache_bypass_keywords = ["random", "current time", "latest", "now"]  # 不缓存的关键词
    
    def should_cache(self, prompt: str, **kwargs) -> bool:
        """判断是否应该缓存"""
        if not self.cache_enabled:
            return False
        
        # 检查是否包含不应缓存的关键词
        prompt_lower = prompt.lower()
        for keyword in self.cache_bypass_keywords:
            if keyword in prompt_lower:
                return False
        
        # 检查参数中是否有随机性设置
        temperature = kwargs.get("temperature", 0.7)
        if temperature > 0.8:  # 高温度设置通常期望随机性
            return False
        
        return True
    
    def generate_response(self, prompt: str, provider: str = None, **kwargs) -> Dict[str, Any]:
        """生成响应（带缓存）"""
        if provider is None:
            provider = self.default_provider
        
        # 检查是否应该使用缓存
        if self.should_cache(prompt, **kwargs):
            cache_key = self.cache.generate_cache_key(prompt, provider, **kwargs)
            
            # 尝试从缓存获取
            cached_response = self.cache.get(cache_key)
            if cached_response:
                print(f"缓存命中: {cache_key[:8]}...")
                return cached_response
        
        # 缓存未命中或不使用缓存，调用实际API
        response = super().generate_response(prompt, provider, **kwargs)
        
        # 如果应该缓存且请求成功，存储到缓存
        if (self.should_cache(prompt, **kwargs) and 
            not response.get("error", False)):
            self.cache.put(cache_key, response)
        
        return response
    
    def invalidate_cache(self, pattern: str = None):
        """失效缓存"""
        if pattern:
            self.cache.invalidate_pattern(pattern)
        else:
            self.cache.clear()
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """获取缓存统计"""
        return self.cache.get_stats()
    
    def configure_cache(self, enabled: bool = True, 
                       bypass_keywords: List[str] = None):
        """配置缓存设置"""
        self.cache_enabled = enabled
        if bypass_keywords is not None:
            self.cache_bypass_keywords = bypass_keywords

# 使用示例
def demo_response_caching():
    """演示响应缓存"""
    # 创建支持缓存的模型管理器
    manager = CachedModelManager(cache_size=100, cache_ttl=300)  # 5分钟TTL
    
    # 注册提供者
    openai_provider = OpenAIProvider("fake-api-key")
    manager.register_provider("openai", openai_provider)
    
    print("=== 响应缓存演示 ===")
    
    # 测试相同请求的缓存效果
    test_prompt = "什么是机器学习？请简要解释。"
    
    print("第一次请求（应该调用API）:")
    start_time = time.time()
    response1 = manager.generate_response(test_prompt, temperature=0.3)
    time1 = time.time() - start_time
    print(f"响应时间: {time1:.3f}s")
    print(f"来自缓存: {response1.get('from_cache', False)}")
    
    print("\n第二次相同请求（应该来自缓存）:")
    start_time = time.time()
    response2 = manager.generate_response(test_prompt, temperature=0.3)
    time2 = time.time() - start_time
    print(f"响应时间: {time2:.3f}s")
    print(f"来自缓存: {response2.get('from_cache', False)}")
    
    print("\n不同参数的请求（应该调用API）:")
    start_time = time.time()
    response3 = manager.generate_response(test_prompt, temperature=0.8)
    time3 = time.time() - start_time
    print(f"响应时间: {time3:.3f}s")
    print(f"来自缓存: {response3.get('from_cache', False)}")
    
    print("\n包含随机性关键词的请求（不应缓存）:")
    random_prompt = "给我一个随机的编程建议"
    response4 = manager.generate_response(random_prompt)
    print(f"来自缓存: {response4.get('from_cache', False)}")
    
    # 查看缓存统计
    print("\n=== 缓存统计 ===")
    stats = manager.get_cache_stats()
    print(f"缓存大小: {stats['cache_size']}/{stats['max_size']}")
    print(f"命中次数: {stats['hit_count']}")
    print(f"未命中次数: {stats['miss_count']}")
    print(f"命中率: {stats['hit_rate']:.1f}%")
    
    # 演示缓存失效
    print("\n清空缓存...")
    manager.invalidate_cache()
    
    print("清空后的缓存统计:")
    stats_after = manager.get_cache_stats()
    print(f"缓存大小: {stats_after['cache_size']}/{stats_after['max_size']}")

# 运行演示
demo_response_caching()
```

---

## 总结

本最佳实践指南详细介绍了AgentlyFormat项目六个核心功能模块的实际应用场景和解决方案：

### 🎯 核心价值

1. **智能JSON补全**：解决AI模型输出不完整JSON的问题，提供智能修复和验证
2. **流式JSON解析**：支持实时处理大型JSON数据流，提升用户体验
3. **数据路径构建**：提供灵活的数据访问和操作方式，支持多种路径格式
4. **Schema验证**：确保数据质量和一致性，支持增量验证和自定义规则
5. **差分引擎**：高效的数据变更追踪和版本管理，支持冲突解决
6. **多模型适配器**：统一的AI模型接口，支持智能路由和性能监控

### 🚀 应用场景

- **企业级应用**：配置管理、数据同步、版本控制
- **AI应用开发**：模型集成、响应处理、性能优化
- **数据处理**：实时分析、批量验证、格式转换
- **Web应用**：表单验证、API响应处理、用户交互

### 💡 最佳实践要点

1. **性能优化**：使用缓存、批量处理、异步操作
2. **错误处理**：完善的异常捕获和恢复机制
3. **监控告警**：实时监控系统状态和性能指标
4. **扩展性**：模块化设计，支持自定义扩展
5. **安全性**：数据验证、访问控制、配额管理

### 📈 进阶建议

- 根据实际业务需求选择合适的功能组合
- 定期监控和优化系统性能
- 建立完善的测试和部署流程
- 持续关注项目更新和社区最佳实践

通过本指南的学习和实践，您将能够充分发挥AgentlyFormat项目的强大功能，构建高效、稳定的数据处理和AI应用系统。