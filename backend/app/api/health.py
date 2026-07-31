from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.infra import llm_gateway, qdrant_client, redis_client
from app.db.base import engine
from sqlalchemy import text

router = APIRouter()


async def _mysql_ok() -> bool:
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


@router.get("/health")
async def health():
    deps = {
        "mysql": "ok" if await _mysql_ok() else "error",
        "redis": "ok" if await redis_client.ping() else "error",
        "qdrant": "ok" if await qdrant_client.ping() else "error",
        "llm_gateway": "ok" if await llm_gateway.ping() else "error",
    }
    status = "ok" if all(v == "ok" for v in deps.values()) else "degraded"
    code = 200 if status == "ok" else 503
    return JSONResponse(status_code=code, content={"status": status, "deps": deps})
