from app.db.models import Message, MessageSource
from app.repositories.base import TenantScopedRepository


class MessageRepository(TenantScopedRepository[Message]):
    model = Message

    async def append(
        self,
        conversation_id: int,
        source: MessageSource,
        content: str,
        lang: str = "zh",
        meta: dict | None = None,
    ):
        return await self.add(
            conversation_id=conversation_id,
            source=source,
            content=content,
            lang=lang,
            meta_json=meta or {},
        )

    async def history(self, conversation_id: int, after_id: int = 0):
        stmt = (
            self.scoped_select()
            .where(Message.conversation_id == conversation_id, Message.id > after_id)
            .order_by(Message.id.asc())
        )
        return (await self.session.execute(stmt)).scalars().all()
