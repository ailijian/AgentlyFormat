#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import json
import asyncio
sys.path.append('src')

from agently_format.core.streaming_parser import StreamingParser

async def debug_parsing_state():
    """调试ParsingState的is_complete状态"""
    parser = StreamingParser()
    session_id = parser.create_session('test')
    
    # 简单测试数据
    data = {'test': 'value'}
    json_str = json.dumps(data)
    
    print(f"JSON数据: {json_str}")
    
    result = await parser.parse_chunk(json_str, session_id, is_final=True)
    state = parser.get_parsing_state(session_id)
    
    print(f"is_complete: {state.is_complete}")
    print(f"errors: {state.errors}")
    print(f"current_data: {state.current_data}")
    
    if state.errors:
        print("\n错误详情:")
        for error in state.errors:
            print(f"  - {error}")

if __name__ == "__main__":
    asyncio.run(debug_parsing_state())