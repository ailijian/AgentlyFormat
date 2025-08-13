"""API路由

定义所有的API端点和路由处理。
"""

import asyncio
import uuid
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse
import json

from .models import *
from .config import get_settings
from .middleware import get_metrics
from ..core.streaming_parser import StreamingParser
from ..core.json_completer import JSONCompleter, CompletionStrategy
from ..core.path_builder import PathBuilder, PathStyle
from ..adapters.model_adapter import ModelAdapter, create_adapter
from ..types.models import ModelType, create_model_config
from ..types.events import EventType


# 创建路由器
router = APIRouter()

# 全局状态管理
class AppState:
    def __init__(self):
        self.sessions: Dict[str, Dict[str, Any]] = {}
        self.model_configs: Dict[str, Any] = {}
        self.parsers: Dict[str, StreamingParser] = {}
        self.websocket_connections: Dict[str, WebSocket] = {}
        self.start_time = datetime.now()
    
    def cleanup_expired_sessions(self):
        """清理过期会话"""
        now = datetime.now()
        expired_sessions = []
        
        for session_id, session_data in self.sessions.items():
            if session_data.get('expires_at', now) < now:
                expired_sessions.append(session_id)
        
        for session_id in expired_sessions:
            self.remove_session(session_id)
    
    def remove_session(self, session_id: str):
        """移除会话"""
        if session_id in self.sessions:
            del self.sessions[session_id]
        if session_id in self.parsers:
            del self.parsers[session_id]
        if session_id in self.websocket_connections:
            del self.websocket_connections[session_id]


app_state = AppState()


# 依赖注入
def get_app_state() -> AppState:
    """获取应用状态"""
    return app_state


def get_settings_dependency():
    """获取配置依赖"""
    return get_settings()


# 健康检查
@router.get("/health", response_model=HealthCheckResponse)
async def health_check(state: AppState = Depends(get_app_state)):
    """健康检查端点"""
    settings = get_settings()
    uptime = (datetime.now() - state.start_time).total_seconds()
    
    # 检查依赖状态
    dependencies = {
        "streaming_parser": "healthy",
        "json_completer": "healthy",
        "path_builder": "healthy",
        "model_adapter": "healthy"
    }
    
    return HealthCheckResponse(
        message="Service is healthy",
        version=settings.app_version,
        uptime=uptime,
        dependencies=dependencies
    )


# 统计信息
@router.get("/stats", response_model=StatsResponse)
async def get_stats(state: AppState = Depends(get_app_state)):
    """获取统计信息"""
    metrics = get_metrics()
    
    # 从事件系统获取统计数据
    from ..core.event_system import get_global_emitter
    emitter = get_global_emitter()
    event_stats = emitter.get_stats()
    
    # 转换events_by_type为字符串键的字典
    events_by_type_str = {}
    for event_type, count in event_stats.events_by_type.items():
        events_by_type_str[event_type.value] = count
    
    return StatsResponse(
        message="Statistics retrieved successfully",
        total_requests=metrics.get("total_requests", 0),
        active_sessions=len(state.sessions),
        total_events=event_stats.total_events,
        events_by_type=events_by_type_str,
        average_response_time=metrics.get("average_response_time", 0),
        error_rate=metrics.get("error_rate", 0),
        uptime=metrics.get("uptime", 0)
    )


# JSON补全
@router.post("/json/complete", response_model=JSONCompleteResponse)
async def complete_json(request: JSONCompleteRequest):
    """JSON补全端点"""
    try:
        # 创建补全器
        completer = JSONCompleter()
        
        # 转换策略
        strategy_map = {
            CompletionStrategyEnum.CONSERVATIVE: CompletionStrategy.CONSERVATIVE,
            CompletionStrategyEnum.SMART: CompletionStrategy.SMART,
            CompletionStrategyEnum.AGGRESSIVE: CompletionStrategy.AGGRESSIVE
        }
        
        strategy = strategy_map.get(request.strategy, CompletionStrategy.SMART)
        
        # 执行补全
        result = completer.complete(
            request.content,
            strategy=strategy,
            max_depth=request.max_depth
        )
        
        return JSONCompleteResponse(
            message="JSON completion successful",
            completed_json=result.completed_json,
            is_valid=result.is_valid,
            changes_made=result.changes_made,
            confidence=result.confidence
        )
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# 路径构建
@router.post("/path/build", response_model=PathBuildResponse)
async def build_paths(request: PathBuildRequest):
    """路径构建端点"""
    try:
        # 创建路径构建器
        builder = PathBuilder()
        
        # 转换风格
        style_map = {
            PathStyleEnum.DOT: PathStyle.DOT,
            PathStyleEnum.SLASH: PathStyle.SLASH,
            PathStyleEnum.BRACKET: PathStyle.BRACKET,
            PathStyleEnum.MIXED: PathStyle.MIXED
        }
        
        style = style_map.get(request.style, PathStyle.DOT)
        
        # 构建路径
        paths = builder.build_paths(
            request.data,
            style=style,
            include_arrays=request.include_arrays
        )
        
        return PathBuildResponse(
            message="Path building successful",
            paths=paths,
            total_paths=len(paths)
        )
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# 会话管理
@router.post("/session/create", response_model=SessionCreateResponse)
async def create_session(
    request: SessionCreateRequest,
    state: AppState = Depends(get_app_state)
):
    """创建会话"""
    session_id = request.session_id or str(uuid.uuid4())
    
    if session_id in state.sessions:
        raise HTTPException(status_code=409, detail="Session already exists")
    
    expires_at = datetime.now() + timedelta(seconds=request.ttl)
    
    state.sessions[session_id] = {
        "session_id": session_id,
        "created_at": datetime.now(),
        "expires_at": expires_at,
        "metadata": request.metadata,
        "event_count": 0,
        "last_activity": datetime.now()
    }
    
    return SessionCreateResponse(
        message="Session created successfully",
        session_id=session_id,
        expires_at=expires_at
    )


@router.get("/session/{session_id}", response_model=SessionInfoResponse)
async def get_session(
    session_id: str,
    state: AppState = Depends(get_app_state)
):
    """获取会话信息"""
    if session_id not in state.sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session_data = state.sessions[session_id]
    
    return SessionInfoResponse(
        message="Session info retrieved",
        **session_data
    )


@router.delete("/session/{session_id}")
async def delete_session(
    session_id: str,
    state: AppState = Depends(get_app_state)
):
    """删除会话"""
    if session_id not in state.sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    state.remove_session(session_id)
    
    return {"message": "Session deleted successfully"}


# 流式解析
@router.post("/parse/stream", response_model=StreamParseResponse)
async def parse_stream(
    request: StreamParseRequest,
    state: AppState = Depends(get_app_state)
):
    """流式解析端点"""
    try:
        session_id = request.session_id or str(uuid.uuid4())
        
        # 获取或创建解析器
        if session_id not in state.parsers:
            parser = StreamingParser()
            state.parsers[session_id] = parser
            
            # 创建解析会话
            parser.create_session(session_id)
            
            # 创建会话（如果不存在）
            if session_id not in state.sessions:
                state.sessions[session_id] = {
                    "session_id": session_id,
                    "created_at": datetime.now(),
                    "expires_at": datetime.now() + timedelta(hours=1),
                    "metadata": {},
                    "event_count": 0,
                    "last_activity": datetime.now()
                }
        else:
            parser = state.parsers[session_id]
        
        # 解析数据块
        events = await parser.parse_chunk(
            request.chunk,
            session_id=session_id,
            is_final=request.is_final
        )
        
        # 更新会话活动时间
        if session_id in state.sessions:
            state.sessions[session_id]["last_activity"] = datetime.now()
            state.sessions[session_id]["event_count"] += len(events)
        
        # 获取当前解析状态
        parsing_state = parser.get_parsing_state(session_id)
        
        # 转换事件为字典格式
        event_dicts = [event.to_dict() for event in events]
        
        # 计算进度
        progress = 0.0
        if parsing_state and parsing_state.total_chunks > 0:
            progress = parsing_state.processed_chunks / parsing_state.total_chunks
        
        return StreamParseResponse(
            status=StatusEnum.SUCCESS,
            message="Stream parsing successful",
            session_id=session_id,
            events=event_dicts,
            current_data=parsing_state.current_data if parsing_state else None,
            is_complete=parsing_state.is_complete if parsing_state else False,
            progress=progress
        )
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# 模型配置
@router.post("/model/config", response_model=ModelConfigResponse)
async def create_model_config_endpoint(
    request: ModelConfigRequest,
    state: AppState = Depends(get_app_state)
):
    """创建模型配置"""
    try:
        config_id = str(uuid.uuid4())
        
        # 创建模型配置
        config = create_model_config(
            model_type=request.model_type,
            model_name=request.model_name,
            api_key=request.api_key,
            base_url=request.base_url,
            api_version=request.api_version,
            request_params=request.request_params,
            headers=request.headers,
            timeout=request.timeout
        )
        
        # 测试配置
        test_result = await ModelAdapter.test_adapter(config)
        
        if not test_result["success"]:
            raise HTTPException(
                status_code=400,
                detail=f"Model configuration test failed: {test_result.get('error')}"
            )
        
        # 保存配置
        state.model_configs[config_id] = {
            "config_id": config_id,
            "config": config,
            "created_at": datetime.now(),
            "test_result": test_result
        }
        
        return ModelConfigResponse(
            message="Model configuration created successfully",
            config_id=config_id,
            model_info=test_result
        )
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# 聊天接口
@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    state: AppState = Depends(get_app_state)
):
    """聊天端点"""
    try:
        # 获取模型配置
        if request.config_id:
            if request.config_id not in state.model_configs:
                raise HTTPException(status_code=404, detail="Model config not found")
            config = state.model_configs[request.config_id]["config"]
        elif request.model_config_data:
            # 处理model_config_data，可能是字典或对象
            if isinstance(request.model_config_data, dict):
                model_config_data = request.model_config_data
            else:
                model_config_data = request.model_config_data.model_dump()
            
            config = create_model_config(
                model_type=model_config_data.get("model_type"),
                model_name=model_config_data.get("model_name"),
                api_key=model_config_data.get("api_key"),
                base_url=model_config_data.get("base_url"),
                api_version=model_config_data.get("api_version"),
                request_params=model_config_data.get("request_params"),
                headers=model_config_data.get("headers"),
                timeout=model_config_data.get("timeout")
            )
        else:
            raise HTTPException(status_code=400, detail="Model config required")
        
        # 创建适配器
        adapter = ModelAdapter.create_adapter(config)
        
        # 转换消息格式
        messages = [msg.model_dump() for msg in request.messages]
        
        # 调用模型
        if request.stream:
            # 流式响应
            async def generate():
                async for chunk in adapter.chat_completion(messages, stream=True):
                    yield f"data: {json.dumps({'content': chunk})}\n\n"
                yield "data: [DONE]\n\n"
            
            return StreamingResponse(
                generate(),
                media_type="text/plain",
                headers={"Cache-Control": "no-cache"}
            )
        else:
            # 非流式响应
            response = await adapter.chat_completion(messages, stream=False)
            
            await adapter.close()
            
            return ChatResponse(
                message="Chat completion successful",
                content=response.content,
                usage=response.usage,
                model=response.model,
                finish_reason=response.finish_reason
            )
            
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# WebSocket端点
@router.websocket("/ws/{session_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    session_id: str,
    state: AppState = Depends(get_app_state)
):
    """WebSocket端点"""
    await websocket.accept()
    
    # 注册连接
    state.websocket_connections[session_id] = websocket
    
    try:
        # 创建解析器（如果不存在）
        if session_id not in state.parsers:
            parser = StreamingParser()
            state.parsers[session_id] = parser
        else:
            parser = state.parsers[session_id]
        
        while True:
            # 接收消息
            data = await websocket.receive_text()
            message = json.loads(data)
            
            if message["type"] == "parse_chunk":
                # 处理解析请求
                events = []
                
                async def event_callback(event):
                    events.append(event.to_dict())
                    # 实时发送事件
                    await websocket.send_text(json.dumps({
                        "type": "event",
                        "data": event.to_dict()
                    }))
                
                result = await parser.parse_chunk(
                    message["data"]["chunk"],
                    session_id=session_id,
                    is_final=message["data"].get("is_final", False),
                    callback=event_callback
                )
                
                # 发送解析结果
                parsing_state = parser.get_parsing_state(session_id)
                
                await websocket.send_text(json.dumps({
                    "type": "parse_result",
                    "data": {
                        "session_id": session_id,
                        "events": events,
                        "current_data": parsing_state.current_data if parsing_state else None,
                        "is_complete": parsing_state.is_complete if parsing_state else False,
                        "progress": parsing_state.progress if parsing_state else 0.0
                    }
                }))
            
            elif message["type"] == "ping":
                # 心跳响应
                await websocket.send_text(json.dumps({
                    "type": "pong",
                    "timestamp": datetime.now().isoformat()
                }))
    
    except WebSocketDisconnect:
        # 清理连接
        if session_id in state.websocket_connections:
            del state.websocket_connections[session_id]
    
    except Exception as e:
        await websocket.send_text(json.dumps({
            "type": "error",
            "data": {"error": str(e)}
        }))
        await websocket.close()


# 批量处理
@router.post("/batch/process", response_model=BatchProcessResponse)
async def batch_process(
    request: BatchProcessRequest,
    background_tasks: BackgroundTasks
):
    """批量处理端点"""
    try:
        results = []
        errors = []
        processed_count = 0
        
        for i, item in enumerate(request.items):
            try:
                if request.operation == "json_complete":
                    completer = JSONCompleter()
                    result = completer.complete(item.get("content", ""))
                    results.append({
                        "index": i,
                        "result": result.to_dict()
                    })
                elif request.operation == "path_build":
                    builder = PathBuilder()
                    paths = builder.build_paths(item.get("data", {}))
                    results.append({
                        "index": i,
                        "result": {"paths": paths}
                    })
                else:
                    raise ValueError(f"Unknown operation: {request.operation}")
                
                processed_count += 1
                
            except Exception as e:
                errors.append({
                    "index": i,
                    "error": str(e)
                })
        
        return BatchProcessResponse(
            message="Batch processing completed",
            total_items=len(request.items),
            processed_items=processed_count,
            failed_items=len(errors),
            results=results,
            errors=errors
        )
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# 后台任务：清理过期会话
async def cleanup_sessions():
    """清理过期会话的后台任务"""
    while True:
        try:
            app_state.cleanup_expired_sessions()
            await asyncio.sleep(300)  # 每5分钟清理一次
        except Exception as e:
            print(f"Error in cleanup task: {e}")
            await asyncio.sleep(60)  # 出错时等待1分钟后重试