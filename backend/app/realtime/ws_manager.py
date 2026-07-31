"""进程内 WebSocket 连接注册 + 本地扇出，叠加 Redis 跨实例广播（T039/T053/T067）。

- 用户流：conversation_id -> {ws}；send/broadcast。
- 坐席流：tenant_id -> {ws}；send_agents/notify_agents（工作台会话列表实时增量）。
MySQL 为事实源，Redis 仅承载易失的实时推送（澄清 Q3）。
"""
import time
from collections import defaultdict


def envelope(mtype: str, data: dict) -> dict:
    return {"type": mtype, "data": data, "ts": int(time.time() * 1000)}


class WSManager:
    def __init__(self) -> None:
        self._conns: dict[int, set] = defaultdict(set)
        self._agents: dict[int, set] = defaultdict(set)

    # ---- 用户 widget 连接 ----
    def register(self, conversation_id: int, ws) -> None:
        self._conns[conversation_id].add(ws)

    def unregister(self, conversation_id: int, ws) -> None:
        conns = self._conns.get(conversation_id)
        if not conns:
            return
        conns.discard(ws)
        if not conns:
            self._conns.pop(conversation_id, None)

    async def send(self, conversation_id: int, message: dict) -> None:
        dead = []
        for ws in list(self._conns.get(conversation_id, ())):
            try:
                await ws.send_json(message)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.unregister(conversation_id, ws)

    async def broadcast(self, tenant_id: int, conversation_id: int, message: dict) -> None:
        await self.send(conversation_id, message)
        try:
            from app.realtime import pubsub

            await pubsub.publish(f"rt:{tenant_id}:conv:{conversation_id}", message)
        except Exception:
            pass

    # ---- 坐席工作台连接 ----
    def register_agent(self, tenant_id: int, ws) -> None:
        self._agents[tenant_id].add(ws)

    def unregister_agent(self, tenant_id: int, ws) -> None:
        conns = self._agents.get(tenant_id)
        if not conns:
            return
        conns.discard(ws)
        if not conns:
            self._agents.pop(tenant_id, None)

    async def send_agents(self, tenant_id: int, message: dict) -> None:
        dead = []
        for ws in list(self._agents.get(tenant_id, ())):
            try:
                await ws.send_json(message)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.unregister_agent(tenant_id, ws)

    async def notify_agents(self, tenant_id: int, message: dict) -> None:
        await self.send_agents(tenant_id, message)
        try:
            from app.realtime import pubsub

            await pubsub.publish(f"rt:{tenant_id}:agents", message)
        except Exception:
            pass


ws_manager = WSManager()
