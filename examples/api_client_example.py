"""API客户端使用示例

演示如何使用AgentlyFormat的REST API。
"""

import asyncio
import json
from typing import Dict, Any, Optional

import httpx


class AgentyFormatClient:
    """Agently Format API客户端"""
    
    def __init__(self, base_url: str = "http://localhost:8000", api_version: str = "v1"):
        self.base_url = base_url.rstrip('/')
        self.api_version = api_version
        self.api_base = f"{self.base_url}/api/{api_version}"
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def close(self):
        """关闭客户端"""
        await self.client.aclose()
    
    async def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        response = await self.client.get(f"{self.api_base}/health")
        response.raise_for_status()
        return response.json()
    
    async def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        response = await self.client.get(f"{self.api_base}/stats")
        response.raise_for_status()
        return response.json()
    
    async def complete_json(
        self,
        content: str,
        strategy: str = "smart",
        max_depth: int = 10
    ) -> Dict[str, Any]:
        """JSON补全"""
        data = {
            "content": content,
            "strategy": strategy,
            "max_depth": max_depth
        }
        
        response = await self.client.post(
            f"{self.api_base}/json/complete",
            json=data
        )
        response.raise_for_status()
        return response.json()
    
    async def build_paths(
        self,
        data: Dict[str, Any],
        style: str = "dot",
        include_arrays: bool = True
    ) -> Dict[str, Any]:
        """构建数据路径"""
        request_data = {
            "data": data,
            "style": style,
            "include_arrays": include_arrays
        }
        
        response = await self.client.post(
            f"{self.api_base}/path/build",
            json=request_data
        )
        response.raise_for_status()
        return response.json()
    
    async def create_session(
        self,
        session_id: Optional[str] = None,
        ttl: int = 3600,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """创建会话"""
        data = {
            "ttl": ttl,
            "metadata": metadata or {}
        }
        
        if session_id:
            data["session_id"] = session_id
        
        response = await self.client.post(
            f"{self.api_base}/session/create",
            json=data
        )
        response.raise_for_status()
        return response.json()
    
    async def get_session(self, session_id: str) -> Dict[str, Any]:
        """获取会话信息"""
        response = await self.client.get(f"{self.api_base}/session/{session_id}")
        response.raise_for_status()
        return response.json()
    
    async def delete_session(self, session_id: str) -> Dict[str, Any]:
        """删除会话"""
        response = await self.client.delete(f"{self.api_base}/session/{session_id}")
        response.raise_for_status()
        return response.json()
    
    async def parse_stream(
        self,
        chunk: str,
        session_id: Optional[str] = None,
        is_final: bool = False,
        expected_schema: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """流式解析"""
        data = {
            "chunk": chunk,
            "is_final": is_final
        }
        
        if session_id:
            data["session_id"] = session_id
        
        if expected_schema:
            data["expected_schema"] = expected_schema
        
        response = await self.client.post(
            f"{self.api_base}/parse/stream",
            json=data
        )
        response.raise_for_status()
        return response.json()
    
    async def create_model_config(
        self,
        model_type: str,
        model_name: str,
        api_key: str,
        base_url: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """创建模型配置"""
        data = {
            "model_type": model_type,
            "model_name": model_name,
            "api_key": api_key
        }
        
        if base_url:
            data["base_url"] = base_url
        
        data.update(kwargs)
        
        response = await self.client.post(
            f"{self.api_base}/model/config",
            json=data
        )
        response.raise_for_status()
        return response.json()
    
    async def chat(
        self,
        messages: list,
        model_config: Optional[Dict[str, Any]] = None,
        config_id: Optional[str] = None,
        stream: bool = False
    ) -> Dict[str, Any]:
        """聊天补全"""
        data = {
            "messages": messages,
            "stream": stream
        }
        
        if model_config:
            data["model_config"] = model_config
        
        if config_id:
            data["config_id"] = config_id
        
        response = await self.client.post(
            f"{self.api_base}/chat",
            json=data
        )
        response.raise_for_status()
        return response.json()
    
    async def batch_process(
        self,
        operation: str,
        items: list
    ) -> Dict[str, Any]:
        """批量处理"""
        data = {
            "operation": operation,
            "items": items
        }
        
        response = await self.client.post(
            f"{self.api_base}/batch/process",
            json=data
        )
        response.raise_for_status()
        return response.json()


async def health_check_example():
    """健康检查示例"""
    print("=== 健康检查示例 ===")
    
    client = AgentyFormatClient()
    
    try:
        health = await client.health_check()
        print(f"服务状态: {health['status']}")
        print(f"版本: {health['version']}")
        print(f"运行时间: {health['uptime']:.2f}秒")
        
        # 检查依赖状态
        deps = health['dependencies']
        print("\n依赖状态:")
        for dep, status in deps.items():
            print(f"  {dep}: {status}")
        
        # 获取统计信息
        stats = await client.get_stats()
        print(f"\n统计信息:")
        print(f"  总请求数: {stats['total_requests']}")
        print(f"  活跃会话: {stats['active_sessions']}")
        print(f"  平均响应时间: {stats['average_response_time']:.3f}秒")
        
    except Exception as e:
        print(f"健康检查失败: {e}")
    
    finally:
        await client.close()


async def json_completion_example():
    """JSON补全示例"""
    print("\n=== JSON补全示例 ===")
    
    client = AgentyFormatClient()
    
    try:
        # 不完整的JSON
        incomplete_json = '''
        {
            "user": {
                "id": 123,
                "name": "Alice",
                "profile": {
                    "email": "alice@example.com",
                    "preferences": {
                        "theme": "dark",
                        "notifications": true
        '''
        
        print(f"原始JSON:\n{incomplete_json}")
        
        # 执行补全
        result = await client.complete_json(
            content=incomplete_json,
            strategy="smart",
            max_depth=10
        )
        
        print(f"\n补全结果:")
        print(f"状态: {result['status']}")
        print(f"是否有效: {result['is_valid']}")
        print(f"修改次数: {result['changes_made']}")
        print(f"置信度: {result['confidence']:.2f}")
        print(f"\n补全后的JSON:\n{result['completed_json']}")
        
        # 验证补全结果
        try:
            parsed = json.loads(result['completed_json'])
            print(f"\n解析成功! 用户ID: {parsed['user']['id']}")
        except json.JSONDecodeError:
            print("\n补全结果无法解析")
    
    except Exception as e:
        print(f"JSON补全失败: {e}")
    
    finally:
        await client.close()


async def path_building_example():
    """路径构建示例"""
    print("\n=== 路径构建示例 ===")
    
    client = AgentyFormatClient()
    
    try:
        # 示例数据
        data = {
            "application": {
                "name": "MyApp",
                "version": "1.0.0",
                "features": [
                    {
                        "name": "authentication",
                        "enabled": True,
                        "config": {
                            "providers": ["oauth", "local"],
                            "session_timeout": 3600
                        }
                    },
                    {
                        "name": "analytics",
                        "enabled": False
                    }
                ]
            }
        }
        
        print(f"原始数据:\n{json.dumps(data, indent=2, ensure_ascii=False)}")
        
        # 构建路径
        result = await client.build_paths(
            data=data,
            style="dot",
            include_arrays=True
        )
        
        print(f"\n路径构建结果:")
        print(f"状态: {result['status']}")
        print(f"总路径数: {result['total_paths']}")
        
        print(f"\n生成的路径:")
        for path in result['paths']:
            print(f"  {path}")
    
    except Exception as e:
        print(f"路径构建失败: {e}")
    
    finally:
        await client.close()


async def session_management_example():
    """会话管理示例"""
    print("\n=== 会话管理示例 ===")
    
    client = AgentyFormatClient()
    
    try:
        # 创建会话
        session_result = await client.create_session(
            session_id="demo-session-123",
            ttl=1800,  # 30分钟
            metadata={
                "user_id": "user-456",
                "project": "demo-project"
            }
        )
        
        print(f"会话创建结果:")
        print(f"状态: {session_result['status']}")
        print(f"会话ID: {session_result['session_id']}")
        print(f"过期时间: {session_result['expires_at']}")
        
        session_id = session_result['session_id']
        
        # 获取会话信息
        session_info = await client.get_session(session_id)
        print(f"\n会话信息:")
        print(f"创建时间: {session_info['created_at']}")
        print(f"元数据: {session_info['metadata']}")
        
        # 使用会话进行流式解析
        chunks = [
            '{"data": [',
            '{"id": 1, "value": "test1"},',
            '{"id": 2, "value": "test2"}',
            '], "count": 2}'
        ]
        
        print(f"\n流式解析:")
        for i, chunk in enumerate(chunks):
            is_final = (i == len(chunks) - 1)
            
            result = await client.parse_stream(
                chunk=chunk,
                session_id=session_id,
                is_final=is_final
            )
            
            print(f"块 {i + 1}: 进度 {result['progress']:.1%}, 完成: {result['is_complete']}")
            
            if result['events']:
                print(f"  事件数: {len(result['events'])}")
        
        # 显示最终数据
        if result['current_data']:
            print(f"\n最终解析数据:\n{json.dumps(result['current_data'], indent=2, ensure_ascii=False)}")
        
        # 删除会话
        delete_result = await client.delete_session(session_id)
        print(f"\n会话删除: {delete_result['message']}")
    
    except Exception as e:
        print(f"会话管理失败: {e}")
    
    finally:
        await client.close()


async def batch_processing_example():
    """批量处理示例"""
    print("\n=== 批量处理示例 ===")
    
    client = AgentyFormatClient()
    
    try:
        # 批量JSON补全
        json_items = [
            {"content": '{"name": "Alice", "age": 25'},
            {"content": '{"name": "Bob", "age": 30, "city": "NYC"'},
            {"content": '{"invalid": json syntax'},  # 故意的错误
            {"content": '{"name": "Charlie", "profile": {"email": "charlie@example.com"'}
        ]
        
        print(f"批量JSON补全 - 处理 {len(json_items)} 个项目")
        
        result = await client.batch_process(
            operation="json_complete",
            items=json_items
        )
        
        print(f"\n批量处理结果:")
        print(f"状态: {result['status']}")
        print(f"总项目: {result['total_items']}")
        print(f"成功处理: {result['processed_items']}")
        print(f"失败项目: {result['failed_items']}")
        
        # 显示成功结果
        if result['results']:
            print(f"\n成功结果:")
            for item in result['results'][:3]:  # 只显示前3个
                print(f"  索引 {item['index']}: 补全成功")
        
        # 显示错误
        if result['errors']:
            print(f"\n错误信息:")
            for error in result['errors']:
                print(f"  索引 {error['index']}: {error['error']}")
        
        # 批量路径构建
        path_items = [
            {"data": {"user": {"name": "Alice", "id": 1}}},
            {"data": {"config": {"timeout": 30, "retries": 3}}},
            {"data": {"items": [1, 2, 3, 4, 5]}}
        ]
        
        print(f"\n批量路径构建 - 处理 {len(path_items)} 个项目")
        
        path_result = await client.batch_process(
            operation="path_build",
            items=path_items
        )
        
        print(f"路径构建结果: 成功 {path_result['processed_items']}/{path_result['total_items']}")
    
    except Exception as e:
        print(f"批量处理失败: {e}")
    
    finally:
        await client.close()


async def model_integration_example():
    """模型集成示例"""
    print("\n=== 模型集成示例 ===")
    
    client = AgentyFormatClient()
    
    try:
        # 注意: 这里使用模拟的API密钥，实际使用时需要真实的密钥
        print("创建模型配置...")
        
        config_result = await client.create_model_config(
            model_type="openai",
            model_name="gpt-3.5-turbo",
            api_key="sk-mock-api-key-for-demo",  # 模拟密钥
            timeout=30
        )
        
        print(f"模型配置创建: {config_result['status']}")
        
        if config_result['status'] == 'success':
            config_id = config_result['config_id']
            print(f"配置ID: {config_id}")
            
            # 使用配置进行聊天
            messages = [
                {"role": "user", "content": "请帮我生成一个JSON格式的用户配置文件"}
            ]
            
            chat_result = await client.chat(
                messages=messages,
                config_id=config_id,
                stream=False
            )
            
            print(f"\n聊天结果:")
            print(f"状态: {chat_result['status']}")
            print(f"内容: {chat_result['content']}")
            print(f"模型: {chat_result['model']}")
            print(f"使用量: {chat_result['usage']}")
    
    except Exception as e:
        print(f"模型集成示例失败: {e}")
        # 这是预期的，因为我们使用的是模拟API密钥
        if "API key" in str(e) or "authentication" in str(e).lower():
            print("提示: 请使用真实的API密钥来测试模型功能")
    
    finally:
        await client.close()


async def main():
    """主函数 - 运行所有API示例"""
    print("Agently Format - API客户端使用示例")
    print("=" * 50)
    
    try:
        await health_check_example()
        await json_completion_example()
        await path_building_example()
        await session_management_example()
        await batch_processing_example()
        await model_integration_example()
        
        print("\n=== 所有API示例运行完成 ===")
        print("\n注意事项:")
        print("1. 确保Agently Format服务正在运行 (默认端口8000)")
        print("2. 模型功能需要有效的API密钥")
        print("3. 某些示例可能因为网络或配置问题而失败")
        
    except Exception as e:
        print(f"\n运行API示例时发生错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    # 运行示例
    asyncio.run(main())