"""Bot 配置 API（T075）：GET/PUT 模型/护栏 prompt/检索阈值/top_k。"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_session, require_agent
from app.core.tenant import TenantContext
from app.db.models import BotConfig

router = APIRouter()


class BotConfigPatch(BaseModel):
    model: str | None = None
    system_prompt: str | None = None
    retrieval_threshold: float | None = None
    top_k: int | None = None


async def _load(session, tenant_id: int) -> BotConfig | None:
    return (
        await session.execute(select(BotConfig).where(BotConfig.tenant_id == tenant_id))
    ).scalar_one_or_none()


@router.get("/bot-config")
async def get_bot_config(
    ctx: TenantContext = Depends(require_agent),
    session: AsyncSession = Depends(get_session),
):
    row = await _load(session, ctx.tenant_id)
    if row is None:
        raise HTTPException(status_code=404, detail={"code": "not_found"})
    return {
        "model": row.model,
        "system_prompt": row.system_prompt,
        "retrieval_threshold": row.retrieval_threshold,
        "top_k": row.top_k,
    }


@router.put("/bot-config")
async def update_bot_config(
    body: BotConfigPatch,
    ctx: TenantContext = Depends(require_agent),
    session: AsyncSession = Depends(get_session),
):
    row = await _load(session, ctx.tenant_id)
    if row is None:
        raise HTTPException(status_code=404, detail={"code": "not_found"})
    if body.model is not None:
        row.model = body.model
    if body.system_prompt is not None:
        row.system_prompt = body.system_prompt
    if body.retrieval_threshold is not None:
        row.retrieval_threshold = body.retrieval_threshold
    if body.top_k is not None:
        row.top_k = body.top_k
    await session.commit()
    return {"ok": True}
