import sys
sys.path.insert(0, 'src')

import asyncio
from agently_format.core.streaming_parser import StreamingParser


async def debug_parsing():
    parser = StreamingParser()
    session_id = 'debug-session'
    
    chunks = [
        '{"users": [',
        '{"id": 1, "name": "Alice",',
        '"email": "alice@example.com"},',
        '{"id": 2, "name": "Bob",',
        '"email": "bob@example.com"}',
        '], "total": 2}'
    ]
    
    parser.create_session(session_id)
    
    for i, chunk in enumerate(chunks):
        is_final = (i == len(chunks) - 1)
        print(f'Processing chunk {i}: {chunk}')
        
        result = await parser.parse_chunk(chunk, session_id, is_final=is_final)
        
        state = parser.get_parsing_state(session_id)
        print(f'Current data after chunk {i}: {state.current_data}')
        print(f'Errors: {state.errors}')
        print('---')
    
    final_state = parser.get_parsing_state(session_id)
    print(f'Final data: {final_state.current_data}')
    if final_state.current_data:
        print(f'Has users: {"users" in final_state.current_data}')
        print(f'Has total: {"total" in final_state.current_data}')


if __name__ == "__main__":
    asyncio.run(debug_parsing())