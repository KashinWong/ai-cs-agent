from sqlalchemy import select

from app.db.models import Agent
from app.repositories.base import TenantScopedRepository


class AgentRepository(TenantScopedRepository[Agent]):
    model = Agent

    async def by_username_scoped(self, username: str):
        stmt = self.scoped_select().where(Agent.username == username)
        return (await self.session.execute(stmt)).scalar_one_or_none()


async def find_agent_for_login(session, username: str):
    """登录时尚无租户上下文，按全局 username 直查（demo 单租户）。"""
    stmt = select(Agent).where(Agent.username == username)
    return (await session.execute(stmt)).scalar_one_or_none()
