"""知识条目向量索引：dense-only upsert/delete 到 Qdrant，并回写 vector_status（T031）。

本环境走网关 embedding；sparse 路径停用（见 services/embedding.py 说明）。
"""
from qdrant_client import models as qm

from app.core.config import get_settings
from app.core.tenant import current_tenant_id
from app.db.base import async_session_factory
from app.db.models import VectorStatus
from app.infra.qdrant_client import DENSE, get_qdrant
from app.repositories.knowledge import KnowledgeRepository
from app.services import embedding


async def index_items(ids: list[int]) -> None:
    settings = get_settings()
    tid = current_tenant_id()
    async with async_session_factory() as session:
        repo = KnowledgeRepository(session)
        items = await repo.by_ids(ids)
        if not items:
            return
        texts = [f"{it.title}\n{it.content}" for it in items]
        dense = await embedding.dense_embed(texts)
        points = []
        for it, dvec in zip(items, dense):
            points.append(
                qm.PointStruct(
                    id=it.id,
                    vector={DENSE: dvec},
                    payload={
                        "tenant_id": tid,
                        "lang": it.lang,
                        "title": it.title,
                        "kb_id": it.kb_id,
                    },
                )
            )
        await get_qdrant().upsert(settings.qdrant_collection, points=points)
        for it in items:
            await repo.set_vector_status(it.id, VectorStatus.indexed)
        await session.commit()


async def delete_item(id_: int) -> None:
    settings = get_settings()
    await get_qdrant().delete(
        settings.qdrant_collection, points_selector=qm.PointIdsList(points=[id_])
    )
