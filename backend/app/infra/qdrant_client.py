from qdrant_client import AsyncQdrantClient
from qdrant_client import models as qm

from app.core.config import get_settings

_client: AsyncQdrantClient | None = None

DENSE = "dense"
SPARSE = "sparse"  # 保留常量名以兼容架构；本环境不创建 sparse 向量


def get_qdrant() -> AsyncQdrantClient:
    global _client
    if _client is None:
        _client = AsyncQdrantClient(url=get_settings().qdrant_url)
    return _client


async def ensure_collection() -> None:
    settings = get_settings()
    client = get_qdrant()
    exists = await client.collection_exists(settings.qdrant_collection)
    if exists:
        return
    # dense-only（本环境 sparse 停用，见 services/embedding.py 说明）
    await client.create_collection(
        collection_name=settings.qdrant_collection,
        vectors_config={
            DENSE: qm.VectorParams(size=settings.embedding_dim, distance=qm.Distance.COSINE)
        },
    )


async def ping() -> bool:
    try:
        await get_qdrant().get_collections()
        return True
    except Exception:
        return False
