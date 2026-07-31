from contextvars import ContextVar
from dataclasses import dataclass

from starlette.types import ASGIApp, Receive, Scope, Send

from app.core.security import decode_token


@dataclass
class TenantContext:
    tenant_id: int
    agent_id: int | None = None


_ctx: ContextVar[TenantContext | None] = ContextVar("tenant_context", default=None)


def bind_tenant(tenant_id: int, agent_id: int | None = None) -> None:
    """由 WS / webhook handler 在按 channel token 反查租户后显式绑定。"""
    _ctx.set(TenantContext(tenant_id=tenant_id, agent_id=agent_id))


def get_tenant_context() -> TenantContext | None:
    return _ctx.get()


def current_tenant_id() -> int:
    ctx = _ctx.get()
    if ctx is None:
        raise PermissionError("tenant context not bound")
    return ctx.tenant_id


def current_agent_id() -> int | None:
    ctx = _ctx.get()
    return ctx.agent_id if ctx else None


class TenantMiddleware:
    """纯 ASGI 中间件：从 Bearer JWT 解析 tenant_id/agent_id 并写入 ContextVar。

    channel-token 路径（widget/webhook）不带 JWT，由各自 handler 调用 bind_tenant。
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] not in ("http", "websocket"):
            await self.app(scope, receive, send)
            return
        token_ctx = _ctx.set(None)
        try:
            headers = dict(scope.get("headers") or [])
            auth = headers.get(b"authorization", b"").decode()
            if auth.lower().startswith("bearer "):
                payload = decode_token(auth[7:])
                if payload:
                    _ctx.set(
                        TenantContext(
                            tenant_id=int(payload["tenant_id"]),
                            agent_id=int(payload["agent_id"]),
                        )
                    )
            await self.app(scope, receive, send)
        finally:
            _ctx.reset(token_ctx)
