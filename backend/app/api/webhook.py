"""通用 Webhook 入站（T082/T083）：token 反查租户，归一化后走同一引擎链路。

校验失败先于任何写库，保证不产生脏会话（FR-011）。
"""
from fastapi import APIRouter
from fastapi.responses import JSONResponse
from sqlalchemy import select

from app.channels.webhook import WebhookAdapter
from app.core.tenant import bind_tenant
from app.db.base import async_session_factory
from app.db.models import Channel, ChannelType, ConversationStatus, MessageSource
from app.repositories.contact import ContactRepository
from app.repositories.conversation import ConversationRepository
from app.repositories.message import MessageRepository
from app.services import chat_service, handoff_service

router = APIRouter()
_adapter = WebhookAdapter()


def _err(status: int, code: str, message: str) -> JSONResponse:
    return JSONResponse(status_code=status, content={"error": {"code": code, "message": message}})


@router.post("/channels/webhook/{token}")
async def webhook_inbound(token: str, payload: dict):
    async with async_session_factory() as session:
        channel = (
            await session.execute(
                select(Channel).where(
                    Channel.token == token,
                    Channel.type == ChannelType.webhook,
                    Channel.enabled.is_(True),
                )
            )
        ).scalar_one_or_none()
    if channel is None:
        return _err(404, "channel_not_found", "invalid token")

    try:
        inbound = _adapter.normalize_inbound(payload)
    except ValueError:
        return _err(400, "invalid_payload", "missing text/external_user_id")

    bind_tenant(channel.tenant_id)
    lang = inbound.lang or "zh"
    async with async_session_factory() as session:
        contact = await ContactRepository(session).upsert(channel.id, inbound.external_user_id)
        crepo = ConversationRepository(session)
        conv = await crepo.latest_active_for_contact(contact.id) or await crepo.create(
            channel.id, contact.id, lang=lang
        )
        await MessageRepository(session).append(
            conv.id, MessageSource.user, inbound.text, lang=lang
        )
        await crepo.touch(conv.id)
        await session.commit()
        conv_id = conv.id
        conv_status = conv.status

    # 人工/待接管态：仅落库入队，不由 AI 抢答（FR-005）
    if conv_status in (ConversationStatus.human, ConversationStatus.pending_human):
        return JSONResponse(status_code=202, content={"conversation_id": conv_id, "accepted": True})

    async def _noop_token(_tok: str) -> None:
        return None

    decision = await chat_service.run_turn(conv_id, inbound.text, lang, _noop_token)
    if decision.get("kind") == "escalate":
        await handoff_service.escalate(conv_id, reason=decision.get("reason", "low_confidence"))
    return JSONResponse(status_code=202, content={"conversation_id": conv_id, "accepted": True})
