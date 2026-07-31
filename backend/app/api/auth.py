"""坐席登录（T055）：校验口令签发 JWT 会话令牌。"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_session
from app.core.security import create_token, verify_password
from app.db.models import Tenant
from app.repositories.agent import find_agent_for_login
from sqlalchemy import select

router = APIRouter()


class LoginBody(BaseModel):
    username: str
    password: str


@router.post("/auth/login")
async def login(body: LoginBody, session: AsyncSession = Depends(get_session)):
    agent = await find_agent_for_login(session, body.username)
    if agent is None or not verify_password(agent.password_hash, body.password):
        raise HTTPException(status_code=401, detail={"code": "invalid_credentials"})
    tenant = (
        await session.execute(select(Tenant).where(Tenant.id == agent.tenant_id))
    ).scalar_one_or_none()
    token = create_token(agent.id, agent.tenant_id)
    return {
        "token": token,
        "agent": {"id": agent.id, "display_name": agent.display_name},
        "tenant": {"slug": tenant.slug if tenant else "default"},
    }
