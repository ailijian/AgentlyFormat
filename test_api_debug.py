#!/usr/bin/env python3
"""API调试脚本"""

import requests
import json

def test_stream_parse():
    """测试流式解析API"""
    url = "http://localhost:8000/api/v1/parse/stream"
    data = {
        "chunk": '{"name": "Alice", "age": 25}',
        "session_id": "test-session",
        "is_final": True
    }
    
    try:
        response = requests.post(url, json=data)
        print(f"Status Code: {response.status_code}")
        print(f"Response Headers: {dict(response.headers)}")
        print(f"Response Text: {response.text}")
        
        if response.status_code != 200:
            print(f"Error: {response.status_code}")
            try:
                error_data = response.json()
                print(f"Error Details: {json.dumps(error_data, indent=2)}")
            except:
                print(f"Raw Error: {response.text}")
        else:
            result = response.json()
            print(f"Success: {json.dumps(result, indent=2)}")
            
    except Exception as e:
        print(f"Exception: {e}")

if __name__ == "__main__":
    test_stream_parse()