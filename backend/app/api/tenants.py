"""租户 API（T074）：GET 当前租户；POST 创建默认禁用（超出本里程碑范围）。"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_session, require_agent
from app.core.config import get_settings
from app.core.tenant import TenantContext
from app.db.models import Tenant

router = APIRouter()


class TenantBody(BaseModel):
    slug: str
    name: str


@router.get("/tenant")
async def current_tenant(
    ctx: TenantContext = Depends(require_agent),
    session: AsyncSession = Depends(get_session),
):
    row = (
        await session.execute(select(Tenant).where(Tenant.id == ctx.tenant_id))
    ).scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail={"code": "not_found"})
    return {"id": row.id, "slug": row.slug, "name": row.name}


@router.post("/tenants", status_code=201)
async def create_tenant(
    body: TenantBody,
    ctx: TenantContext = Depends(require_agent),
    session: AsyncSession = Depends(get_session),
):
    if not get_settings().enable_tenant_provisioning:
        raise HTTPException(status_code=403, detail={"code": "provisioning_disabled"})
    t = Tenant(slug=body.slug, name=body.name)
    session.add(t)
    await session.commit()
    return {"id": t.id, "slug": t.slug}
