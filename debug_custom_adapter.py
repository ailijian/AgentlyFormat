#!/usr/bin/env python3

from src.agently_format.adapters.custom_adapter import create_custom_adapter

def custom_auth_handler(config):
    return {"X-API-Key": config.api_key}

try:
    adapter = create_custom_adapter(
        model_name="helper-model",
        api_key="helper-key",
        base_url="https://helper-api.com",
        auth_handler=custom_auth_handler
    )
    
    print(f"Adapter created successfully: {type(adapter)}")
    print(f"Model name: {adapter.model_name}")
    print(f"API key: {adapter.api_key}")
    print(f"Base URL: {adapter.base_url}")
    
    # 测试自定义认证
    headers = adapter._get_auth_headers()
    print(f"Auth headers: {headers}")
    
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()