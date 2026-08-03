"""用户 widget WebSocket 端点（T040 + T044a 接线）。

流程：user_message → run_turn →(noise)noise_reply |(ai)ai_token*+ai_done |(escalate)handoff。
request_human → 直接转人工。断线/刷新按 conversation_id 从 MySQL 回读历史（FR-015）。
human/pending_human 态下用户消息落库但 AI 不抢答（FR-005）。
"""
import secrets
import time

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect
from sqlalchemy import select

from app.core.tenant import bind_tenant
from app.db.base import async_session_factory
from app.db.models import Channel, ConversationStatus, MessageSource
from app.realtime.ws_manager import ws_manager
from app.repositories.contact import ContactRepository
from app.repositories.conversation import ConversationRepository
from app.repositories.message import MessageRepository
from app.services import chat_service, handoff_service

router = APIRouter()


def _env(mtype: str, data: dict) -> dict:
    return {"type": mtype, "data": data, "ts": int(time.time() * 1000)}


def _msg_dto(m) -> dict:
    return {"id": m.id, "source": m.source.value, "content": m.content, "lang": m.lang}


async def _resolve_channel(token: str):
    async with async_session_factory() as session:
        return (
            await session.execute(
                select(Channel).where(Channel.token == token, Channel.enabled.is_(True))
            )
        ).scalar_one_or_none()


@router.websocket("/ws/widget")
async def widget_ws(
    ws: WebSocket,
    channel_token: str = Query(...),
    conversation_id: int | None = Query(None),
    contact_key: str | None = Query(None),
):
    channel = await _resolve_channel(channel_token)
    if channel is None:
        await ws.close(code=4404)
        return
    await ws.accept()
    tenant_id = channel.tenant_id
    bind_tenant(tenant_id)

    async with async_session_factory() as session:
        crepo = ConversationRepository(session)
        if conversation_id:
            conv = await crepo.get(conversation_id)
        else:
            key = contact_key or secrets.token_hex(8)
            contact = await ContactRepository(session).upsert(channel.id, key)
            conv = await crepo.latest_active_for_contact(contact.id) or await crepo.create(
                channel.id, contact.id
            )
        await session.commit()
        if conv is None:
            await ws.close(code=4404)
            return
        conv_id = conv.id
        conv_status = conv.status.value

    ws_manager.register(conv_id, ws)
    await ws.send_json(_env("conversation", {"id": conv_id, "status": conv_status}))
    async with async_session_factory() as session:
        hist = await MessageRepository(session).history(conv_id)
    await ws.send_json(_env("history", {"messages": [_msg_dto(m) for m in hist]}))

    try:
        while True:
            raw = await ws.receive_json()
            bind_tenant(tenant_id)
            mtype = raw.get("type")
            data = raw.get("data") or {}

            if mtype == "ping":
                await ws.send_json(_env("pong", {}))
                continue

            if mtype == "request_human":
                # escalate() 已 broadcast handoff 到本会话频道（含本地连接），不再重复直发
                await handoff_service.escalate(conv_id, reason="user_requested")
                continue

            if mtype != "user_message":
                continue

            text = (data.get("text") or "").strip()
            if not text:
                continue
            lang = data.get("lang") or "zh"

            async with async_session_factory() as session:
                await MessageRepository(session).append(
                    conv_id, MessageSource.user, text, lang=lang
                )
                await ConversationRepository(session).touch(conv_id)
                await session.commit()
                conv = await ConversationRepository(session).get(conv_id)

            # 人工态：消息落库交给坐席，AI 不抢答（FR-005）
            if conv and conv.status == ConversationStatus.human:
                continue
            # 待接管但无人接管：检测用户意图，有实质问题自动切回 AI
            if conv and conv.status == ConversationStatus.pending_human:
                from app.domain.routing import classify_noise, detect_human_intent

                if detect_human_intent(text):
                    await ws.send_json(
                        _env("handoff", {"status": "pending_human",
                              "notice": "仍在排队等待人工客服，也可问我知识库内的问题，我会尝试解答。"}))
                    continue
                if classify_noise(text):
                    await ws.send_json(
                        _env("handoff", {"status": "pending_human",
                              "notice": "人工客服仍在忙线，请描述具体问题。"}))
                    continue
                # 用户发了实质问题 → 自动切回 AI，继续回答
                async with async_session_factory() as session:
                    await ConversationRepository(session).set_status(
                        conv_id, ConversationStatus.ai)
                    await session.commit()
                await ws.send_json(_env("mode_changed", {"mode": "ai"}))

            async def on_token(tok: str) -> None:
                await ws.send_json(_env("ai_token", {"delta": tok}))

            decision = await chat_service.run_turn(conv_id, text, lang, on_token)
            kind = decision.get("kind")
            if kind == "noise":
                await ws.send_json(_env("noise_reply", {"content": decision["content"]}))
            elif kind == "ai":
                await ws.send_json(
                    _env("ai_done", {"message_id": decision["message_id"], "content": decision["content"]})
                )
            elif kind == "escalate":
                # escalate() 已 broadcast handoff 到本会话频道，不再重复直发
                await handoff_service.escalate(conv_id, reason=decision.get("reason", "low_confidence"))
    except WebSocketDisconnect:
        ws_manager.unregister(conv_id, ws)
