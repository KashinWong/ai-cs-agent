"""Widget 引导配置（公开，无需鉴权）：返回默认 widget 渠道 token，供前端自动连 WS。

widget token 本就是要嵌入公开页面的凭证，故此 endpoint 公开可接受（demo 单租户）。
"""
from fastapi import APIRouter
from sqlalchemy import select

from app.db.base import async_session_factory
from app.db.models import Channel, ChannelType

router = APIRouter()


@router.get("/widget/config")
async def widget_config():
    async with async_session_factory() as session:
        ch = (
            await session.execute(
                select(Channel)
                .where(Channel.type == ChannelType.widget, Channel.enabled.is_(True))
                .limit(1)
            )
        ).scalar_one_or_none()
    return {"channel_token": ch.token if ch else None}
