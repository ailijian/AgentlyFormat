"""基础使用示例

演示AgentlyFormat的基本功能使用。
"""

import asyncio
import json
from typing import Dict, Any

# 导入核心模块
from agently_format.core.streaming_parser import StreamingParser
from agently_format.core.json_completer import JSONCompleter, CompletionStrategy
from agently_format.core.path_builder import PathBuilder, PathStyle
from agently_format.core.event_system import get_global_emitter, EventType


def basic_json_completion_example():
    """基础JSON补全示例"""
    print("=== JSON补全示例 ===")
    
    # 创建JSON补全器
    completer = JSONCompleter()
    
    # 不完整的JSON字符串
    incomplete_json = '''
    {
        "user": {
            "name": "Alice",
            "age": 25,
            "profile": {
                "city": "New York",
                "interests": ["reading", "coding"
    '''
    
    print(f"原始不完整JSON:\n{incomplete_json}")
    
    # 执行补全
    result = completer.complete(incomplete_json)
    
    print(f"\n补全结果:")
    print(f"是否有效: {result.is_valid}")
    print(f"是否应用补全: {result.completion_applied}")
    print(f"\n补全后的JSON:\n{result.completed_json}")
    
    # 验证补全结果
    try:
        parsed_data = json.loads(result.completed_json)
        print(f"\n解析成功! 用户名: {parsed_data['user']['name']}")
    except json.JSONDecodeError as e:
        print(f"\n解析失败: {e}")


def basic_path_building_example():
    """基础路径构建示例"""
    print("\n=== 路径构建示例 ===")
    
    # 创建路径构建器
    builder = PathBuilder()
    
    # 示例数据
    data = {
        "api": {
            "version": "v1",
            "endpoints": [
                {
                    "path": "/users",
                    "methods": ["GET", "POST"],
                    "auth": {
                        "required": True,
                        "types": ["bearer", "api_key"]
                    }
                },
                {
                    "path": "/posts",
                    "methods": ["GET", "POST", "PUT", "DELETE"]
                }
            ]
        },
        "config": {
            "timeout": 30,
            "retries": 3
        }
    }
    
    print(f"原始数据:\n{json.dumps(data, indent=2, ensure_ascii=False)}")
    
    # 创建路径构建器
    builder = PathBuilder()
    
    # 提取所有路径
    print(f"\n点号风格路径:")
    paths = builder.extract_parsing_key_orders(data)
    for path in sorted(paths)[:10]:  # 只显示前10个路径
        success, value = builder.get_value_at_path(data, path)
        if success:
            print(f"  {path} = {value}")
    
    # 测试路径转换
    print(f"\n路径转换示例:")
    sample_path = "api.endpoints[0].auth.required"
    print(f"原始路径: {sample_path}")
    print(f"斜杠风格: {builder.convert_path(sample_path, PathStyle.SLASH)}")
    print(f"括号风格: {builder.convert_path(sample_path, PathStyle.BRACKET)}")
    
    if len(paths) > 10:
        print(f"  ... 还有 {len(paths) - 10} 个路径")


async def basic_streaming_parser_example():
    """基础流式解析示例"""
    print("\n=== 流式解析示例 ===")
    
    # 创建流式解析器
    parser = StreamingParser()
    
    # 模拟分块接收的JSON数据
    json_chunks = [
        '{"users": [',
        '{"id": 1, "name": "Alice",',
        '"email": "alice@example.com",',
        '"profile": {"age": 25, "city": "NYC"}},',
        '{"id": 2, "name": "Bob",',
        '"email": "bob@example.com",',
        '"profile": {"age": 30, "city": "SF"}}',
        '], "total": 2, "page": 1}'
    ]
    
    session_id = parser.create_session()
    events_received = []
    
    # 事件回调函数
    async def event_callback(event):
        events_received.append(event)
        print(f"事件: {event.event_type.value} - {event.message}")
        if hasattr(event, 'data') and event.data:
            print(f"  数据: {event.data}")
    
    print("开始流式解析...")
    
    # 逐块解析
    for i, chunk in enumerate(json_chunks):
        is_final = (i == len(json_chunks) - 1)
        
        print(f"\n处理块 {i + 1}/{len(json_chunks)}: {chunk[:50]}...")
        
        result = await parser.parse_chunk(
            session_id=session_id,
            chunk=chunk
        )
        
        # 获取当前解析状态
        state = parser.parsing_states[session_id]
        print(f"处理了 {state.processed_chunks}/{state.total_chunks} 个块")
    
    # 获取最终结果
    final_state = parser.parsing_states[session_id]
    if final_state and final_state.current_data:
        print(f"\n最终解析结果:")
        print(json.dumps(final_state.current_data, indent=2, ensure_ascii=False))
        
        print(f"\n统计信息:")
        stats = parser.get_stats()
        print(f"  总会话数: {stats.get('total_sessions', 0)}")
        print(f"  总事件数: {len(events_received)}")
    
    # 清理会话
    parser.cleanup_session(session_id)


async def basic_event_system_example():
    """基础事件系统示例"""
    print("\n=== 事件系统示例 ===")
    
    # 获取全局事件发射器
    emitter = get_global_emitter()
    
    # 事件处理器
    async def on_data_parsed(event_data):
        print(f"数据解析完成: {event_data.get('message', '')}")
    
    async def on_error_occurred(event_data):
        print(f"发生错误: {event_data.get('error', '')}")
    
    # 注册事件监听器
    emitter.on(EventType.DELTA, on_data_parsed)
    emitter.on(EventType.ERROR, on_error_occurred)
    
    # 创建并发射事件
    from agently_format.types.events import create_delta_event, create_error_event
    
    delta_event = create_delta_event(
        path="users",
        value={"count": 2},
        delta_value={"count": 2},
        session_id="demo",
        sequence_number=1
    )
    await emitter.emit(delta_event)
    
    error_event = create_error_event(
        path="network",
        error_type="timeout",
        error_message="网络连接超时",
        session_id="demo",
        sequence_number=2
    )
    await emitter.emit(error_event)
    
    # 获取统计信息
    stats = emitter.get_stats()
    print(f"\n事件系统统计:")
    print(f"  总事件数: {stats.total_events}")
    print(f"  处理器数量: {stats.total_handlers}")


def comprehensive_example():
    """综合示例 - 组合使用多个功能"""
    print("\n=== 综合示例 ===")
    
    # 1. 补全不完整的JSON
    completer = JSONCompleter()
    incomplete = '{"config": {"api_url": "https://api.example.com", "timeout": 30'
    
    completion_result = completer.complete(incomplete)
    print(f"补全JSON: {completion_result.completed_json}")
    
    # 2. 解析补全后的数据
    if completion_result.is_valid:
        data = json.loads(completion_result.completed_json)
        
        # 3. 构建数据路径
        builder = PathBuilder()
        paths = builder.extract_parsing_key_orders(data)
        
        print(f"\n数据路径:")
        for path in paths[:5]:
            success, value = builder.get_value_at_path(data, path)
            if success:
                print(f"  {path}: {value}")
        
        # 4. 验证特定路径
        api_url_path = "config.api_url"
        success, api_url = builder.get_value_at_path(data, api_url_path)
        if success:
            print(f"\nAPI URL: {api_url}")
        else:
            print(f"\n路径 '{api_url_path}' 未找到")


async def main():
    """主函数 - 运行所有示例"""
    print("Agently Format - 基础使用示例")
    print("=" * 50)
    
    try:
        # 运行同步示例
        basic_json_completion_example()
        basic_path_building_example()
        comprehensive_example()
        
        # 运行异步示例
        await basic_streaming_parser_example()
        await basic_event_system_example()
        
        print("\n=== 所有示例运行完成 ===")
        
    except Exception as e:
        print(f"\n运行示例时发生错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    # 运行示例
    asyncio.run(main())