"""检索（T032）：dense-only 语义检索（本环境 sparse 停用）。

Qdrant dense 向量最近邻，强制 tenant_id payload 过滤；返回 top_k 命中与最高余弦分
（供转人工阈值判定，research R-02）。混合 sparse+RRF 架构保留，换网络恢复 embedding.py 即可。
"""
from qdrant_client import models as qm

from app.core.config import get_settings
from app.core.tenant import current_tenant_id
from app.db.base import async_session_factory
from app.infra.qdrant_client import DENSE, get_qdrant
from app.repositories.knowledge import KnowledgeRepository
from app.services import embedding


async def hybrid_search(query: str, top_k: int = 5) -> dict:
    settings = get_settings()
    tid = current_tenant_id()
    client = get_qdrant()
    coll = settings.qdrant_collection

    dense = (await embedding.dense_embed([query]))[0]
    flt = qm.Filter(
        must=[qm.FieldCondition(key="tenant_id", match=qm.MatchValue(value=tid))]
    )
    res = await client.query_points(
        collection_name=coll,
        query=dense,
        using=DENSE,
        query_filter=flt,
        limit=top_k,
        with_payload=True,
    )
    points = res.points
    top_score = float(points[0].score) if points else 0.0
    ids = [int(p.id) for p in points]

    hits: list[dict] = []
    if ids:
        async with async_session_factory() as session:
            items = await KnowledgeRepository(session).by_ids(ids)
        by_id = {it.id: it for it in items}
        for pid in ids:
            it = by_id.get(pid)
            if it:
                hits.append(
                    {"id": it.id, "title": it.title, "content": it.content, "lang": it.lang}
                )
    return {"hits": hits, "top_score": top_score}
