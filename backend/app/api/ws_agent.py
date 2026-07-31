"""坐席实时 WS（T060/T067）：令牌经 query 握手（浏览器 WS 无法带 Authorization 头）。

注册进 ws_manager 坐席流；服务端在会话状态变化/新消息时经 notify_agents 推送
conversation_upserted / new_message / pending_count，工作台据此免刷新更新列表。
"""
from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect

from app.core.security import decode_token
from app.core.tenant import bind_tenant
from app.db.base import async_session_factory
from app.db.models import ConversationStatus
from app.realtime.ws_manager import envelope, ws_manager
from app.repositories.conversation import ConversationRepository

router = APIRouter()


async def _pending_count(tenant_id: int) -> int:
    bind_tenant(tenant_id)
    async with async_session_factory() as session:
        rows = await ConversationRepository(session).list_by_status(
            ConversationStatus.pending_human
        )
    return len(rows)


@router.websocket("/ws/agent")
async def agent_ws(ws: WebSocket, token: str = Query(...)):
    payload = decode_token(token)
    if not payload:
        await ws.close(code=4401)
        return
    await ws.accept()
    tenant_id = int(payload["tenant_id"])
    bind_tenant(tenant_id, int(payload["agent_id"]))
    ws_manager.register_agent(tenant_id, ws)
    try:
        await ws.send_json(
            envelope("pending_count", {"count": await _pending_count(tenant_id)})
        )
    except Exception:
        pass
    try:
        while True:
            raw = await ws.receive_json()
            if raw.get("type") == "ping":
                await ws.send_json(envelope("pong", {}))
    except WebSocketDisconnect:
        return
    finally:
        ws_manager.unregister_agent(tenant_id, ws)
