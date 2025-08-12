"""流式处理示例

演示如何使用AgentlyFormat进行流式JSON解析和处理。
"""

import asyncio
import json
import time
from typing import List, Dict, Any, Optional

from agently_format.core.streaming_parser import StreamingParser
from agently_format.core.event_system import EventEmitter
from agently_format.core.types import ParseEvent, ParseEventType


class StreamingDemo:
    """流式处理演示类"""
    
    def __init__(self):
        self.event_emitter = EventEmitter()
        self.parser = StreamingParser(self.event_emitter)
        self.received_events: List[ParseEvent] = []
        
        # 注册事件监听器
        self.event_emitter.on('parse_start', self._on_parse_start)
        self.event_emitter.on('parse_progress', self._on_parse_progress)
        self.event_emitter.on('parse_complete', self._on_parse_complete)
        self.event_emitter.on('parse_error', self._on_parse_error)
        self.event_emitter.on('object_start', self._on_object_start)
        self.event_emitter.on('object_end', self._on_object_end)
        self.event_emitter.on('array_start', self._on_array_start)
        self.event_emitter.on('array_end', self._on_array_end)
        self.event_emitter.on('key_found', self._on_key_found)
        self.event_emitter.on('value_found', self._on_value_found)
    
    def _on_parse_start(self, event: ParseEvent):
        """解析开始事件"""
        self.received_events.append(event)
        print(f"🚀 解析开始 - 会话: {event.session_id}")
    
    def _on_parse_progress(self, event: ParseEvent):
        """解析进度事件"""
        self.received_events.append(event)
        progress = event.data.get('progress', 0)
        print(f"📊 解析进度: {progress:.1%}")
    
    def _on_parse_complete(self, event: ParseEvent):
        """解析完成事件"""
        self.received_events.append(event)
        print(f"✅ 解析完成 - 耗时: {event.data.get('duration', 0):.3f}秒")
    
    def _on_parse_error(self, event: ParseEvent):
        """解析错误事件"""
        self.received_events.append(event)
        error = event.data.get('error', 'Unknown error')
        print(f"❌ 解析错误: {error}")
    
    def _on_object_start(self, event: ParseEvent):
        """对象开始事件"""
        self.received_events.append(event)
        path = event.data.get('path', '')
        print(f"🔷 对象开始: {path}")
    
    def _on_object_end(self, event: ParseEvent):
        """对象结束事件"""
        self.received_events.append(event)
        path = event.data.get('path', '')
        print(f"🔶 对象结束: {path}")
    
    def _on_array_start(self, event: ParseEvent):
        """数组开始事件"""
        self.received_events.append(event)
        path = event.data.get('path', '')
        print(f"📋 数组开始: {path}")
    
    def _on_array_end(self, event: ParseEvent):
        """数组结束事件"""
        self.received_events.append(event)
        path = event.data.get('path', '')
        length = event.data.get('length', 0)
        print(f"📄 数组结束: {path} (长度: {length})")
    
    def _on_key_found(self, event: ParseEvent):
        """键发现事件"""
        self.received_events.append(event)
        key = event.data.get('key', '')
        path = event.data.get('path', '')
        print(f"🔑 发现键: '{key}' at {path}")
    
    def _on_value_found(self, event: ParseEvent):
        """值发现事件"""
        self.received_events.append(event)
        value = event.data.get('value')
        path = event.data.get('path', '')
        value_type = type(value).__name__
        print(f"💎 发现值: {value} ({value_type}) at {path}")
    
    def clear_events(self):
        """清空事件记录"""
        self.received_events.clear()


async def simple_streaming_example():
    """简单流式解析示例"""
    print("=== 简单流式解析示例 ===")
    
    demo = StreamingDemo()
    
    # 模拟分块接收的JSON数据
    json_chunks = [
        '{"user": {',
        '"id": 123,',
        '"name": "Alice",',
        '"email": "alice@example.com"',
        '},"timestamp": ',
        '1640995200}'
    ]
    
    session_id = "simple-demo"
    
    print(f"开始解析 {len(json_chunks)} 个数据块...\n")
    
    for i, chunk in enumerate(json_chunks):
        print(f"处理块 {i + 1}: '{chunk}'")
        
        # 模拟网络延迟
        await asyncio.sleep(0.1)
        
        # 解析块
        result = await demo.parser.parse_chunk(
            chunk=chunk,
            session_id=session_id,
            is_final=(i == len(json_chunks) - 1)
        )
        
        print(f"  状态: {result.status}")
        print(f"  进度: {result.progress:.1%}")
        print(f"  完成: {result.is_complete}")
        print()
    
    # 获取最终结果
    final_data = demo.parser.get_current_data(session_id)
    if final_data:
        print(f"最终解析结果:\n{json.dumps(final_data, indent=2, ensure_ascii=False)}")
    
    print(f"\n总共接收到 {len(demo.received_events)} 个事件")


async def complex_streaming_example():
    """复杂流式解析示例"""
    print("\n=== 复杂流式解析示例 ===")
    
    demo = StreamingDemo()
    demo.clear_events()
    
    # 复杂的嵌套JSON数据
    complex_json = {
        "application": {
            "name": "DataProcessor",
            "version": "2.1.0",
            "modules": [
                {
                    "name": "parser",
                    "enabled": True,
                    "config": {
                        "max_depth": 10,
                        "timeout": 30,
                        "features": ["streaming", "validation", "events"]
                    }
                },
                {
                    "name": "formatter",
                    "enabled": True,
                    "config": {
                        "output_format": "json",
                        "pretty_print": True
                    }
                }
            ],
            "metadata": {
                "created_at": "2024-01-15T10:30:00Z",
                "author": "Development Team",
                "tags": ["data", "processing", "json"]
            }
        }
    }
    
    # 将JSON转换为字符串并分块
    json_str = json.dumps(complex_json, ensure_ascii=False)
    chunk_size = 50  # 每块50个字符
    chunks = [json_str[i:i+chunk_size] for i in range(0, len(json_str), chunk_size)]
    
    session_id = "complex-demo"
    
    print(f"原始JSON大小: {len(json_str)} 字符")
    print(f"分为 {len(chunks)} 个块进行处理...\n")
    
    start_time = time.time()
    
    for i, chunk in enumerate(chunks):
        print(f"块 {i + 1}/{len(chunks)}: {len(chunk)} 字符")
        
        # 模拟网络传输延迟
        await asyncio.sleep(0.05)
        
        result = await demo.parser.parse_chunk(
            chunk=chunk,
            session_id=session_id,
            is_final=(i == len(chunks) - 1)
        )
        
        if i % 5 == 0 or i == len(chunks) - 1:  # 每5块显示一次进度
            print(f"  进度: {result.progress:.1%}")
    
    end_time = time.time()
    
    # 获取解析结果
    final_data = demo.parser.get_current_data(session_id)
    
    print(f"\n解析完成!")
    print(f"总耗时: {end_time - start_time:.3f}秒")
    print(f"事件总数: {len(demo.received_events)}")
    
    # 验证解析结果
    if final_data:
        print(f"\n解析结果验证:")
        print(f"  应用名称: {final_data['application']['name']}")
        print(f"  模块数量: {len(final_data['application']['modules'])}")
        print(f"  标签数量: {len(final_data['application']['metadata']['tags'])}")
        
        # 检查数据完整性
        if final_data == complex_json:
            print("✅ 数据完整性验证通过")
        else:
            print("❌ 数据完整性验证失败")


async def error_handling_example():
    """错误处理示例"""
    print("\n=== 错误处理示例 ===")
    
    demo = StreamingDemo()
    demo.clear_events()
    
    # 包含错误的JSON块
    error_chunks = [
        '{"valid": true,',
        '"data": [1, 2, 3',  # 缺少闭合括号
        ', "invalid": }',     # 语法错误
        ', "recovered": "yes"}'
    ]
    
    session_id = "error-demo"
    
    print("处理包含错误的JSON块...\n")
    
    for i, chunk in enumerate(error_chunks):
        print(f"块 {i + 1}: '{chunk}'")
        
        try:
            result = await demo.parser.parse_chunk(
                chunk=chunk,
                session_id=session_id,
                is_final=(i == len(error_chunks) - 1)
            )
            
            print(f"  状态: {result.status}")
            if result.errors:
                print(f"  错误: {result.errors}")
            
        except Exception as e:
            print(f"  异常: {e}")
        
        print()
    
    # 检查错误事件
    error_events = [e for e in demo.received_events if e.event_type == ParseEventType.PARSE_ERROR]
    print(f"捕获到 {len(error_events)} 个错误事件")
    
    for event in error_events:
        print(f"  错误: {event.data.get('error', 'Unknown')}")


async def performance_streaming_example():
    """性能测试示例"""
    print("\n=== 性能测试示例 ===")
    
    demo = StreamingDemo()
    demo.clear_events()
    
    # 生成大量数据
    large_data = {
        "users": [
            {
                "id": i,
                "name": f"User{i}",
                "email": f"user{i}@example.com",
                "profile": {
                    "age": 20 + (i % 50),
                    "city": f"City{i % 10}",
                    "preferences": {
                        "theme": "dark" if i % 2 == 0 else "light",
                        "notifications": i % 3 == 0,
                        "language": "en" if i % 4 == 0 else "zh"
                    }
                }
            }
            for i in range(100)  # 100个用户
        ],
        "metadata": {
            "total_users": 100,
            "generated_at": "2024-01-15T10:30:00Z",
            "version": "1.0"
        }
    }
    
    # 转换为JSON字符串并分块
    json_str = json.dumps(large_data, ensure_ascii=False)
    chunk_size = 1000  # 每块1000字符
    chunks = [json_str[i:i+chunk_size] for i in range(0, len(json_str), chunk_size)]
    
    session_id = "performance-demo"
    
    print(f"性能测试数据:")
    print(f"  JSON大小: {len(json_str):,} 字符")
    print(f"  用户数量: {len(large_data['users'])}")
    print(f"  分块数量: {len(chunks)}")
    print(f"  平均块大小: {len(json_str) // len(chunks)} 字符")
    print()
    
    start_time = time.time()
    
    # 处理所有块
    for i, chunk in enumerate(chunks):
        result = await demo.parser.parse_chunk(
            chunk=chunk,
            session_id=session_id,
            is_final=(i == len(chunks) - 1)
        )
        
        # 每10块显示一次进度
        if i % 10 == 0 or i == len(chunks) - 1:
            print(f"进度: {i + 1}/{len(chunks)} ({result.progress:.1%})")
    
    end_time = time.time()
    
    # 性能统计
    total_time = end_time - start_time
    chars_per_second = len(json_str) / total_time
    chunks_per_second = len(chunks) / total_time
    
    print(f"\n性能统计:")
    print(f"  总耗时: {total_time:.3f}秒")
    print(f"  处理速度: {chars_per_second:,.0f} 字符/秒")
    print(f"  块处理速度: {chunks_per_second:.1f} 块/秒")
    print(f"  事件数量: {len(demo.received_events)}")
    print(f"  平均每块事件: {len(demo.received_events) / len(chunks):.1f}")
    
    # 验证结果
    final_data = demo.parser.get_current_data(session_id)
    if final_data and final_data == large_data:
        print("✅ 大数据解析验证通过")
    else:
        print("❌ 大数据解析验证失败")


async def multi_session_example():
    """多会话并发示例"""
    print("\n=== 多会话并发示例 ===")
    
    demo = StreamingDemo()
    demo.clear_events()
    
    # 准备多个会话的数据
    sessions_data = {
        "session-1": [
            '{"type": "user",',
            '"data": {"id": 1, "name": "Alice"}}'
        ],
        "session-2": [
            '{"type": "config",',
            '"settings": {"theme": "dark", "lang": "en"}}'
        ],
        "session-3": [
            '{"type": "metrics",',
            '"values": [10, 20, 30, 40, 50]}'
        ]
    }
    
    print(f"启动 {len(sessions_data)} 个并发会话...\n")
    
    async def process_session(session_id: str, chunks: List[str]):
        """处理单个会话"""
        print(f"会话 {session_id} 开始处理 {len(chunks)} 个块")
        
        for i, chunk in enumerate(chunks):
            await demo.parser.parse_chunk(
                chunk=chunk,
                session_id=session_id,
                is_final=(i == len(chunks) - 1)
            )
            
            # 模拟不同的处理速度
            await asyncio.sleep(0.1 + (hash(session_id) % 3) * 0.05)
        
        print(f"会话 {session_id} 处理完成")
    
    # 并发处理所有会话
    start_time = time.time()
    
    tasks = [
        process_session(session_id, chunks)
        for session_id, chunks in sessions_data.items()
    ]
    
    await asyncio.gather(*tasks)
    
    end_time = time.time()
    
    print(f"\n所有会话处理完成，耗时: {end_time - start_time:.3f}秒")
    
    # 检查每个会话的结果
    print("\n会话结果:")
    for session_id in sessions_data.keys():
        data = demo.parser.get_current_data(session_id)
        if data:
            print(f"  {session_id}: {data['type']} - ✅")
        else:
            print(f"  {session_id}: 无数据 - ❌")
    
    # 统计事件
    events_by_session = {}
    for event in demo.received_events:
        session = event.session_id
        if session not in events_by_session:
            events_by_session[session] = 0
        events_by_session[session] += 1
    
    print(f"\n事件统计:")
    for session_id, count in events_by_session.items():
        print(f"  {session_id}: {count} 个事件")


async def main():
    """主函数 - 运行所有流式处理示例"""
    print("Agently Format - 流式处理示例")
    print("=" * 50)
    
    try:
        await simple_streaming_example()
        await complex_streaming_example()
        await error_handling_example()
        await performance_streaming_example()
        await multi_session_example()
        
        print("\n=== 所有流式处理示例运行完成 ===")
        print("\n关键特性演示:")
        print("✅ 分块流式解析")
        print("✅ 实时事件通知")
        print("✅ 多会话并发处理")
        print("✅ 错误恢复机制")
        print("✅ 性能优化")
        
    except Exception as e:
        print(f"\n运行流式处理示例时发生错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    # 运行示例
    asyncio.run(main())