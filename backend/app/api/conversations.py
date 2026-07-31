"""坐席工作台会话 API（T057/T058/T059 + US3 列表/历史）。"""
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_session, require_agent
from app.core.tenant import TenantContext
from app.db.models import ConversationStatus
from app.repositories.conversation import ConversationRepository
from app.repositories.message import MessageRepository
from app.services import agent_service

router = APIRouter()


class ReplyBody(BaseModel):
    content: str
    lang: str = "zh"


class ModeBody(BaseModel):
    mode: str  # "ai" | "human"


def _conv_dto(c) -> dict:
    return {
        "id": c.id,
        "status": c.status.value,
        "lang": c.lang,
        "assigned_agent_id": c.assigned_agent_id,
        "last_activity_at": c.last_activity_at.isoformat() if c.last_activity_at else None,
    }


@router.get("/conversations")
async def list_conversations(
    status: str | None = Query(None),
    ctx: TenantContext = Depends(require_agent),
    session: AsyncSession = Depends(get_session),
):
    repo = ConversationRepository(session)
    st = ConversationStatus(status) if status else None
    rows = await repo.list_by_status(st)
    return [_conv_dto(c) for c in rows]


@router.get("/conversations/{conversation_id}/messages")
async def get_messages(
    conversation_id: int,
    after_id: int = Query(0),
    ctx: TenantContext = Depends(require_agent),
    session: AsyncSession = Depends(get_session),
):
    msgs = await MessageRepository(session).history(conversation_id, after_id=after_id)
    return [
        {
            "id": m.id,
            "source": m.source.value,
            "content": m.content,
            "lang": m.lang,
            "created_at": m.created_at.isoformat() if m.created_at else None,
        }
        for m in msgs
    ]


@router.post("/conversations/{conversation_id}/claim")
async def claim(
    conversation_id: int,
    ctx: TenantContext = Depends(require_agent),
    session: AsyncSession = Depends(get_session),
):
    try:
        await agent_service.claim(conversation_id, ctx.agent_id)
    except agent_service.AlreadyClaimed:
        raise HTTPException(status_code=409, detail={"code": "already_claimed"})
    except agent_service.NotFound:
        raise HTTPException(status_code=404, detail={"code": "not_found"})
    return {"ok": True}


@router.post("/conversations/{conversation_id}/reply")
async def reply(
    conversation_id: int,
    body: ReplyBody,
    ctx: TenantContext = Depends(require_agent),
    session: AsyncSession = Depends(get_session),
):
    try:
        mid = await agent_service.reply(conversation_id, ctx.agent_id, body.content, body.lang)
    except agent_service.Forbidden:
        raise HTTPException(status_code=403, detail={"code": "not_owner"})
    except agent_service.NotFound:
        raise HTTPException(status_code=404, detail={"code": "not_found"})
    return {"message_id": mid}


@router.post("/conversations/{conversation_id}/mode")
async def set_mode(
    conversation_id: int,
    body: ModeBody,
    ctx: TenantContext = Depends(require_agent),
    session: AsyncSession = Depends(get_session),
):
    try:
        await agent_service.set_mode(conversation_id, ctx.agent_id, body.mode)
    except agent_service.NotFound:
        raise HTTPException(status_code=404, detail={"code": "not_found"})
    return {"ok": True}


@router.post("/conversations/{conversation_id}/close")
async def close(
    conversation_id: int,
    ctx: TenantContext = Depends(require_agent),
    session: AsyncSession = Depends(get_session),
):
    try:
        await agent_service.close(conversation_id, ctx.agent_id)
    except agent_service.NotFound:
        raise HTTPException(status_code=404, detail={"code": "not_found"})
    return {"ok": True}
