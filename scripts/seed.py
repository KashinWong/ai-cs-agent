"""幂等 seed：default 租户 / 默认坐席 / widget+webhook 渠道 / bot_config / 双语 FAQ。

可重复执行；已存在则跳过。读取 backend/seeds/faq_bilingual.yaml 作为 FAQ 数据源。
"""
import asyncio
import secrets
from pathlib import Path

import yaml
from sqlalchemy import select

from app.core.config import get_settings
from app.core.security import hash_password
from app.db.base import async_session_factory
from app.db import models as m

SEED_FILE = Path(__file__).resolve().parent.parent / "backend" / "seeds" / "faq_bilingual.yaml"


async def _get_or_create_tenant(session) -> m.Tenant:
    row = (await session.execute(select(m.Tenant).where(m.Tenant.slug == "default"))).scalar_one_or_none()
    if row:
        return row
    row = m.Tenant(slug="default", name="Default Workspace")
    session.add(row)
    await session.flush()
    return row


async def _ensure_agent(session, tenant_id: int) -> None:
    s = get_settings()
    exists = (
        await session.execute(
            select(m.Agent).where(m.Agent.tenant_id == tenant_id, m.Agent.username == s.seed_agent_username)
        )
    ).scalar_one_or_none()
    if exists:
        return
    session.add(
        m.Agent(
            tenant_id=tenant_id,
            username=s.seed_agent_username,
            password_hash=hash_password(s.seed_agent_password),
            display_name="Demo Agent",
        )
    )


async def _ensure_channel(session, tenant_id: int, ctype: m.ChannelType) -> None:
    exists = (
        await session.execute(
            select(m.Channel).where(m.Channel.tenant_id == tenant_id, m.Channel.type == ctype)
        )
    ).scalar_one_or_none()
    if exists:
        return
    session.add(
        m.Channel(tenant_id=tenant_id, type=ctype, token=secrets.token_urlsafe(24), config_json={}, enabled=True)
    )


async def _ensure_bot_config(session, tenant_id: int) -> None:
    s = get_settings()
    exists = (
        await session.execute(select(m.BotConfig).where(m.BotConfig.tenant_id == tenant_id))
    ).scalar_one_or_none()
    if exists:
        return
    from app.domain.prompt import SYSTEM_PROMPT

    session.add(
        m.BotConfig(
            tenant_id=tenant_id,
            model=s.llm_chat_model,
            system_prompt=SYSTEM_PROMPT,
            retrieval_threshold=s.default_retrieval_threshold,
            top_k=s.default_top_k,
            enabled=True,
        )
    )


async def _ensure_faq(session, tenant_id: int) -> list[int]:
    count = len(
        (await session.execute(select(m.KnowledgeItem).where(m.KnowledgeItem.tenant_id == tenant_id))).scalars().all()
    )
    if count:
        return []
    items = yaml.safe_load(SEED_FILE.read_text(encoding="utf-8"))
    new_ids: list[int] = []
    for it in items:
        obj = m.KnowledgeItem(
            tenant_id=tenant_id,
            kb_id=1,
            lang=it.get("lang", "zh"),
            title=it["title"],
            content=it["content"],
            meta_json=it.get("meta", {}),
            vector_status=m.VectorStatus.pending,
        )
        session.add(obj)
        await session.flush()
        new_ids.append(obj.id)
    return new_ids


async def main() -> None:
    async with async_session_factory() as session:
        tenant = await _get_or_create_tenant(session)
        await _ensure_agent(session, tenant.id)
        await _ensure_channel(session, tenant.id, m.ChannelType.widget)
        await _ensure_channel(session, tenant.id, m.ChannelType.webhook)
        await _ensure_bot_config(session, tenant.id)
        new_ids = await _ensure_faq(session, tenant.id)
        await session.commit()

    # 向量索引（服务已就绪时执行；失败留给 index_worker 回填）
    if new_ids:
        try:
            from app.core.tenant import bind_tenant
            from app.services.indexer import index_items

            bind_tenant(tenant.id)
            await index_items(new_ids)
        except Exception as exc:  # noqa: BLE001
            print(f"[seed] vector index deferred to worker: {exc}")

    print("[seed] done")


if __name__ == "__main__":
    asyncio.run(main())
