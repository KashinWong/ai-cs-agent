from app.db.models import Contact
from app.repositories.base import TenantScopedRepository


class ContactRepository(TenantScopedRepository[Contact]):
    model = Contact

    async def upsert(self, channel_id: int, external_id: str, display_name: str | None = None):
        stmt = self.scoped_select().where(
            Contact.channel_id == channel_id, Contact.external_id == external_id
        )
        row = (await self.session.execute(stmt)).scalar_one_or_none()
        if row:
            return row
        return await self.add(
            channel_id=channel_id, external_id=external_id, display_name=display_name
        )
