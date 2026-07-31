from app.db.models import KnowledgeItem, VectorStatus
from app.repositories.base import TenantScopedRepository


class KnowledgeRepository(TenantScopedRepository[KnowledgeItem]):
    model = KnowledgeItem

    async def list_items(self, lang: str | None = None):
        stmt = self.scoped_select()
        if lang:
            stmt = stmt.where(KnowledgeItem.lang == lang)
        stmt = stmt.order_by(KnowledgeItem.id.desc())
        return (await self.session.execute(stmt)).scalars().all()

    async def by_ids(self, ids: list[int]):
        if not ids:
            return []
        stmt = self.scoped_select().where(KnowledgeItem.id.in_(ids))
        return (await self.session.execute(stmt)).scalars().all()

    async def set_vector_status(self, id_: int, status: VectorStatus) -> None:
        await self.update_by_id(id_, vector_status=status)
