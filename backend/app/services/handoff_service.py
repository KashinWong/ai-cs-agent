"""转人工服务（T051）：置 pending_human、落 system 提示、向用户实时下发 handoff。

无坐席在线时保持排队不自动关闭（澄清 Q5）。
"""
from app.core.tenant import current_tenant_id
from app.db.base import async_session_factory
from app.db.models import ConversationStatus, MessageSource
from app.domain.prompt import HANDOFF_NOTICE
from app.realtime.ws_manager import envelope, ws_manager
from app.repositories.conversation import ConversationRepository
from app.repositories.message import MessageRepository


async def escalate(conversation_id: int, reason: str) -> str:
    tenant_id = current_tenant_id()
    async with async_session_factory() as session:
        crepo = ConversationRepository(session)
        conv = await crepo.get(conversation_id)
        if conv and conv.status == ConversationStatus.ai:
            await crepo.set_status(conversation_id, ConversationStatus.pending_human)
        await MessageRepository(session).append(
            conversation_id,
            MessageSource.system,
            HANDOFF_NOTICE,
            meta={"handoff": True, "reason": reason},
        )
        await session.commit()

    await ws_manager.broadcast(
        tenant_id,
        conversation_id,
        envelope("handoff", {"status": "pending_human", "notice": HANDOFF_NOTICE}),
    )
    # 通知坐席工作台列表实时更新（US3/T067）
    try:
        async with async_session_factory() as session:
            conv = await ConversationRepository(session).get(conversation_id)
        if conv:
            from app.realtime import notify

            await notify.conversation_upserted(tenant_id, conv)
    except Exception:
        pass
    return HANDOFF_NOTICE
