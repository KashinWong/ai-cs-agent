import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import (
    auth,
    bot_config,
    channels,
    conversations,
    health,
    kb,
    tenants,
    webhook,
    widget,
    ws_agent,
    ws_widget,
)
from app.core.logging import configure_logging
from app.core.tenant import TenantMiddleware
from app.infra import qdrant_client, redis_client
from app.realtime import pubsub


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging(logging.INFO)
    try:
        await qdrant_client.ensure_collection()
    except Exception as exc:  # 启动期 Qdrant 未就绪不阻塞 API
        logging.getLogger("startup").warning("qdrant ensure_collection failed: %s", exc)
    sub_task = asyncio.create_task(pubsub.run_subscriber())
    yield
    sub_task.cancel()
    await redis_client.close()


app = FastAPI(title="ai-cs-agent", lifespan=lifespan)
app.add_middleware(TenantMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix="/api/v1")
app.include_router(widget.router, prefix="/api/v1")
app.include_router(auth.router, prefix="/api/v1")
app.include_router(conversations.router, prefix="/api/v1")
app.include_router(kb.router, prefix="/api/v1")
app.include_router(channels.router, prefix="/api/v1")
app.include_router(tenants.router, prefix="/api/v1")
app.include_router(bot_config.router, prefix="/api/v1")
app.include_router(webhook.router, prefix="/api/v1")
app.include_router(ws_widget.router)
app.include_router(ws_agent.router)
