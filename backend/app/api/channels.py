"""渠道管理 API（T073）：CRUD，创建时生成唯一 token。"""
import secrets

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_session, require_agent
from app.core.tenant import TenantContext
from app.db.models import Channel, ChannelType
from app.repositories.base import TenantScopedRepository

router = APIRouter()


class ChannelRepository(TenantScopedRepository[Channel]):
    model = Channel


class ChannelBody(BaseModel):
    type: str = "webhook"
    config: dict | None = None


class ChannelPatch(BaseModel):
    enabled: bool | None = None
    config: dict | None = None


def _dto(c) -> dict:
    return {
        "id": c.id,
        "type": c.type.value,
        "token": c.token,
        "enabled": c.enabled,
        "config": c.config_json,
    }


@router.get("/channels")
async def list_channels(
    ctx: TenantContext = Depends(require_agent),
    session: AsyncSession = Depends(get_session),
):
    repo = ChannelRepository(session)
    rows = (await session.execute(repo.scoped_select())).scalars().all()
    return [_dto(c) for c in rows]


@router.post("/channels", status_code=201)
async def create_channel(
    body: ChannelBody,
    ctx: TenantContext = Depends(require_agent),
    session: AsyncSession = Depends(get_session),
):
    c = await ChannelRepository(session).add(
        type=ChannelType(body.type),
        token=secrets.token_urlsafe(24),
        config_json=body.config or {},
        enabled=True,
    )
    await session.commit()
    return _dto(c)


@router.patch("/channels/{channel_id}")
async def patch_channel(
    channel_id: int,
    body: ChannelPatch,
    ctx: TenantContext = Depends(require_agent),
    session: AsyncSession = Depends(get_session),
):
    values: dict = {}
    if body.enabled is not None:
        values["enabled"] = body.enabled
    if body.config is not None:
        values["config_json"] = body.config
    if values:
        await ChannelRepository(session).update_by_id(channel_id, **values)
        await session.commit()
    return {"ok": True}
