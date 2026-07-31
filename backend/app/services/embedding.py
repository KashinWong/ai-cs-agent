"""向量生成：dense 走 LLM 网关的 embedding 模型（本环境无法下载本地 fastembed 模型）。

本部署环境（GFW）无法从 HuggingFace/hf-mirror 拉取 fastembed 的 ONNX 模型，
故 dense embedding 改走网关（nova 多模态 embedding，3072 维，中英通吃）。
sparse/BM25 混合检索路径因同样原因在本环境停用；架构保留，换网络即可恢复。
"""
import httpx

from app.core.config import get_settings


async def dense_embed(texts: list[str]) -> list[list[float]]:
    settings = get_settings()
    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(
            f"{settings.llm_gateway_base_url.rstrip('/')}/embeddings",
            headers={"Authorization": f"Bearer {settings.llm_gateway_api_key}"},
            json={"model": settings.embedding_model, "input": texts},
        )
        resp.raise_for_status()
        data = resp.json()["data"]
        # 按 index 排序，保证与输入顺序一致
        data.sort(key=lambda r: r.get("index", 0))
        return [row["embedding"] for row in data]
