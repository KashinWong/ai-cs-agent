from datetime import datetime

from app.db.models import Conversation, ConversationStatus
from app.repositories.base import TenantScopedRepository

_UNSET = object()


class ConversationRepository(TenantScopedRepository[Conversation]):
    model = Conversation

    async def create(self, channel_id: int, contact_id: int, lang: str = "zh"):
        return await self.add(
            channel_id=channel_id,
            contact_id=contact_id,
            status=ConversationStatus.ai,
            lang=lang,
            last_activity_at=datetime.utcnow(),
        )

    async def set_status(self, id_: int, status: ConversationStatus, assigned_agent_id=_UNSET) -> None:
        values = {"status": status, "last_activity_at": datetime.utcnow()}
        if assigned_agent_id is not _UNSET:
            values["assigned_agent_id"] = assigned_agent_id
        await self.update_by_id(id_, **values)

    async def touch(self, id_: int) -> None:
        await self.update_by_id(id_, last_activity_at=datetime.utcnow())

    async def latest_active_for_contact(self, contact_id: int):
        stmt = (
            self.scoped_select()
            .where(
                Conversation.contact_id == contact_id,
                Conversation.status != ConversationStatus.closed,
            )
            .order_by(Conversation.last_activity_at.desc())
        )
        return (await self.session.execute(stmt)).scalars().first()

    async def list_by_status(self, status: ConversationStatus | None = None):
        stmt = self.scoped_select()
        if status:
            stmt = stmt.where(Conversation.status == status)
        stmt = stmt.order_by(Conversation.last_activity_at.desc())
        return (await self.session.execute(stmt)).scalars().all()
