from collections.abc import AsyncIterator

from fastapi import Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.tenant import TenantContext, get_tenant_context
from app.db.base import async_session_factory


async def get_session() -> AsyncIterator[AsyncSession]:
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


def require_agent() -> TenantContext:
    ctx = get_tenant_context()
    if ctx is None or ctx.agent_id is None:
        raise HTTPException(status_code=401, detail={"code": "unauthorized"})
    return ctx


SessionDep = Depends(get_session)
AgentDep = Depends(require_agent)
