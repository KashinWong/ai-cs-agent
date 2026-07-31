"""周期性回填 worker（T076）：扫描 vector_status IN (pending, stale) 的条目重建向量。

覆盖 kb 同步 upsert 失败与批量导入场景。可缺省运行；compose worker 服务启动。
"""
import asyncio

from sqlalchemy import select

from app.core.logging import configure_logging, get_logger
from app.core.tenant import bind_tenant
from app.db.base import async_session_factory
from app.db.models import KnowledgeItem, VectorStatus
from app.infra import qdrant_client
from app.services import indexer

_log = get_logger("index_worker")
INTERVAL_SECONDS = 15


async def _scan_once() -> int:
    async with async_session_factory() as session:
        rows = (
            await session.execute(
                select(KnowledgeItem.id, KnowledgeItem.tenant_id).where(
                    KnowledgeItem.vector_status.in_(
                        [VectorStatus.pending, VectorStatus.stale]
                    )
                )
            )
        ).all()
    by_tenant: dict[int, list[int]] = {}
    for item_id, tenant_id in rows:
        by_tenant.setdefault(tenant_id, []).append(item_id)
    total = 0
    for tenant_id, ids in by_tenant.items():
        bind_tenant(tenant_id)
        try:
            await indexer.index_items(ids)
            total += len(ids)
        except Exception as exc:  # noqa: BLE001
            _log.warning("reindex failed for tenant %s: %s", tenant_id, exc)
    return total


async def main() -> None:
    configure_logging()
    try:
        await qdrant_client.ensure_collection()
    except Exception as exc:  # noqa: BLE001
        _log.warning("ensure_collection failed: %s", exc)
    _log.info("index_worker started (interval=%ss)", INTERVAL_SECONDS)
    while True:
        try:
            n = await _scan_once()
            if n:
                _log.info("reindexed %s items", n)
        except Exception as exc:  # noqa: BLE001
            _log.warning("scan error: %s", exc)
        await asyncio.sleep(INTERVAL_SECONDS)


if __name__ == "__main__":
    asyncio.run(main())
