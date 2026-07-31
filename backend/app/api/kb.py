"""知识条目管理 API（T072）：写操作在请求内同步向量 upsert/删除（SC-006）。"""
from fastapi import APIRouter, Depends, File, Form, Query, UploadFile
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_session, require_agent
from app.core.tenant import TenantContext
from app.db.models import VectorStatus
from app.domain.md_import import parse_markdown_faq
from app.repositories.knowledge import KnowledgeRepository
from app.services import indexer

router = APIRouter()


class KBItemBody(BaseModel):
    title: str
    content: str
    lang: str = "zh"
    meta: dict | None = None


def _dto(it) -> dict:
    return {
        "id": it.id,
        "title": it.title,
        "content": it.content,
        "lang": it.lang,
        "vector_status": it.vector_status.value,
        "meta": it.meta_json,
    }


@router.get("/kb/items")
async def list_items(
    lang: str | None = Query(None),
    ctx: TenantContext = Depends(require_agent),
    session: AsyncSession = Depends(get_session),
):
    rows = await KnowledgeRepository(session).list_items(lang)
    return [_dto(r) for r in rows]


@router.post("/kb/items", status_code=201)
async def create_item(
    body: KBItemBody,
    ctx: TenantContext = Depends(require_agent),
    session: AsyncSession = Depends(get_session),
):
    it = await KnowledgeRepository(session).add(
        title=body.title,
        content=body.content,
        lang=body.lang,
        meta_json=body.meta or {},
        vector_status=VectorStatus.pending,
    )
    await session.commit()
    item_id = it.id
    try:
        await indexer.index_items([item_id])
    except Exception:  # noqa: BLE001 - 失败留 index_worker 回填
        pass
    return {"id": item_id}


@router.put("/kb/items/{item_id}")
async def update_item(
    item_id: int,
    body: KBItemBody,
    ctx: TenantContext = Depends(require_agent),
    session: AsyncSession = Depends(get_session),
):
    await KnowledgeRepository(session).update_by_id(
        item_id,
        title=body.title,
        content=body.content,
        lang=body.lang,
        meta_json=body.meta or {},
        vector_status=VectorStatus.pending,
    )
    await session.commit()
    try:
        await indexer.index_items([item_id])
    except Exception:  # noqa: BLE001
        pass
    return {"ok": True}


@router.delete("/kb/items/{item_id}")
async def delete_item(
    item_id: int,
    ctx: TenantContext = Depends(require_agent),
    session: AsyncSession = Depends(get_session),
):
    await KnowledgeRepository(session).delete_by_id(item_id)
    await session.commit()
    try:
        await indexer.delete_item(item_id)
    except Exception:  # noqa: BLE001
        pass
    return {"ok": True}


@router.post("/kb/import", status_code=201)
async def import_markdown(
    file: UploadFile = File(...),
    lang: str = Form("zh"),
    category: str = Form(""),
    ctx: TenantContext = Depends(require_agent),
    session: AsyncSession = Depends(get_session),
):
    """按 Markdown 标题切分批量导入 FAQ；每条落库并同步向量索引（SC-006）。"""
    raw = (await file.read()).decode("utf-8", errors="replace")
    parsed = parse_markdown_faq(raw)
    if not parsed:
        return {"imported": 0, "items": [], "note": "未解析到任何带标题的条目"}

    repo = KnowledgeRepository(session)
    meta = {"category": category, "source": file.filename} if category else {"source": file.filename}
    new_ids: list[int] = []
    for p in parsed:
        it = await repo.add(
            title=p.title,
            content=p.content,
            lang=lang,
            meta_json=meta,
            vector_status=VectorStatus.pending,
        )
        new_ids.append(it.id)
    await session.commit()

    indexed = 0
    try:
        await indexer.index_items(new_ids)
        indexed = len(new_ids)
    except Exception:  # noqa: BLE001 - 失败留 index_worker 回填
        pass

    return {
        "imported": len(new_ids),
        "indexed": indexed,
        "ids": new_ids,
        "titles": [p.title for p in parsed],
    }
