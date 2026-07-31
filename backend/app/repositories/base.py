from typing import Any, Generic, TypeVar

from sqlalchemy import Select, delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.tenant import current_tenant_id

ModelT = TypeVar("ModelT")


class TenantScopedRepository(Generic[ModelT]):
    """所有读写强制追加 tenant_id 过滤/填充。上下文缺失时抛错而非放行（SC-007）。"""

    model: type[ModelT]

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    def _tid(self) -> int:
        return current_tenant_id()

    def scoped_select(self) -> Select:
        return select(self.model).where(self.model.tenant_id == self._tid())

    async def get(self, id_: int) -> ModelT | None:
        stmt = self.scoped_select().where(self.model.id == id_)
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def add(self, **kwargs: Any) -> ModelT:
        kwargs["tenant_id"] = self._tid()
        obj = self.model(**kwargs)
        self.session.add(obj)
        await self.session.flush()
        return obj

    async def update_by_id(self, id_: int, **values: Any) -> None:
        stmt = (
            update(self.model)
            .where(self.model.id == id_, self.model.tenant_id == self._tid())
            .values(**values)
        )
        await self.session.execute(stmt)

    async def delete_by_id(self, id_: int) -> None:
        stmt = delete(self.model).where(
            self.model.id == id_, self.model.tenant_id == self._tid()
        )
        await self.session.execute(stmt)
