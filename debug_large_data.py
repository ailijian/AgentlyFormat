import asyncio
import json
import sys
sys.path.append('src')

from agently_format.core.streaming_parser import StreamingParser, FieldFilter
from agently_format.core.performance_optimizer import PerformanceOptimizer
from agently_format.core.memory_manager import MemoryManager

async def test_large_data():
    # 创建组件
    optimizer = PerformanceOptimizer()
    memory_manager = MemoryManager()
    field_filter = FieldFilter(performance_optimizer=optimizer)
    parser = StreamingParser(
        performance_optimizer=optimizer,
        memory_manager=memory_manager,
        field_filter=field_filter
    )
    
    # 创建测试数据（简化版）
    large_data = {
        "users": [
            {
                "id": i,
                "name": f"User_{i}",
                "email": f"user{i}@example.com",
                "profile": {
                    "age": 20 + (i % 50),
                    "city": f"City_{i % 100}",
                    "preferences": [f"pref_{j}" for j in range(5)]
                }
            }
            for i in range(10)  # 减少到10个用户进行调试
        ],
        "data": {
            "total_users": 10,
            "generated_at": "2024-01-01T00:00:00Z",
            "metadata": {f"key_{i}": f"value_{i}" for i in range(10)}
        }
    }
    
    session_id = parser.create_session("large_data_test")
    
    # 分块处理
    json_str = json.dumps(large_data)
    chunk_size = 1024
    chunks = [json_str[i:i+chunk_size] for i in range(0, len(json_str), chunk_size)]
    
    print(f"Total chunks: {len(chunks)}")
    print(f"JSON length: {len(json_str)}")
    
    for i, chunk in enumerate(chunks):
        is_final = (i == len(chunks) - 1)
        print(f"Processing chunk {i+1}/{len(chunks)}, is_final: {is_final}")
        
        try:
            result = await parser.parse_chunk(session_id, chunk, is_final=is_final)
            print(f"Chunk {i+1} result: {len(result)} events")
        except Exception as e:
            print(f"Error in chunk {i+1}: {e}")
            break
    
    # 检查最终状态
    state = parser.get_parsing_state(session_id)
    print(f"\nFinal state:")
    print(f"  is_complete: {state.is_complete}")
    print(f"  errors: {state.errors}")
    print(f"  current_data keys: {list(state.current_data.keys()) if state.current_data else None}")
    
    if state.current_data and 'users' in state.current_data:
        print(f"  users count: {len(state.current_data['users'])}")
    
    return state

if __name__ == "__main__":
    asyncio.run(test_large_data())