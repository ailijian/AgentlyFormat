from agently_format.adapters.custom_adapter import create_custom_adapter, CustomAdapter

def custom_auth_handler(api_key):
    return {"X-API-Key": api_key}

try:
    adapter = create_custom_adapter(
        model_name="helper-model",
        api_key="helper-key",
        base_url="https://helper-api.com",
        auth_handler=custom_auth_handler
    )
    
    print(f"adapter type: {type(adapter)}")
    print(f"isinstance(adapter, CustomAdapter): {isinstance(adapter, CustomAdapter)}")
    print(f"adapter.model_name: {adapter.model_name}")
    
    headers = adapter._get_auth_headers()
    print(f"headers: {headers}")
    print(f"X-API-Key in headers: {'X-API-Key' in headers}")
    if 'X-API-Key' in headers:
        print(f"headers['X-API-Key']: {headers['X-API-Key']}")
        
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()