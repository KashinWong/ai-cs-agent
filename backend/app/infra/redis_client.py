import redis.asyncio as redis

from app.core.config import get_settings

_pool: redis.Redis | None = None


def get_redis() -> redis.Redis:
    global _pool
    if _pool is None:
        _pool = redis.from_url(
            get_settings().redis_url, encoding="utf-8", decode_responses=True
        )
    return _pool


async def ping() -> bool:
    try:
        return bool(await get_redis().ping())
    except Exception:
        return False


async def close() -> None:
    global _pool
    if _pool is not None:
        await _pool.aclose()
        _pool = None
