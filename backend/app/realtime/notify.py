"""坐席工作台实时通知辅助（T067）：把会话状态/新消息变化推给坐席流。

置于独立模块避免 services 与 realtime 的循环导入。
"""
from app.realtime.ws_manager import envelope, ws_manager


async def conversation_upserted(tenant_id: int, conv) -> None:
    await ws_manager.notify_agents(
        tenant_id,
        envelope(
            "conversation_upserted",
            {
                "id": conv.id,
                "status": conv.status.value,
                "assigned_agent_id": conv.assigned_agent_id,
                "last_activity_at": conv.last_activity_at.isoformat()
                if conv.last_activity_at
                else None,
            },
        ),
    )


async def new_message(tenant_id: int, conversation_id: int, message: dict) -> None:
    await ws_manager.notify_agents(
        tenant_id,
        envelope("new_message", {"conversation_id": conversation_id, "message": message}),
    )
