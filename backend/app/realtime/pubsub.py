"""Redis Pub/Sub 跨实例广播（T052/T067/R-04）。

频道：
  rt:{tenant}:conv:{id}  用户流 -> ws_manager.send(conv_id)
  rt:{tenant}:agents     坐席流 -> ws_manager.send_agents(tenant_id)
每条消息带 _origin=实例 id；订阅者跳过自身来源，避免与本地 send 重复投递。
demo 单实例下等价于纯本地扇出。
"""
import json
import uuid

from app.core.logging import get_logger
from app.infra.redis_client import get_redis

INSTANCE_ID = uuid.uuid4().hex
_log = get_logger("pubsub")


async def publish(channel: str, env: dict) -> None:
    payload = json.dumps({**env, "_origin": INSTANCE_ID}, ensure_ascii=False)
    await get_redis().publish(channel, payload)


async def run_subscriber() -> None:
    ps = get_redis().pubsub()
    await ps.psubscribe("rt:*:conv:*", "rt:*:agents")
    async for msg in ps.listen():
        if msg.get("type") != "pmessage":
            continue
        try:
            env = json.loads(msg["data"])
            if env.get("_origin") == INSTANCE_ID:
                continue
            env.pop("_origin", None)
            channel = msg["channel"]
            from app.realtime.ws_manager import ws_manager

            if channel.endswith(":agents"):
                tenant_id = int(channel.split(":")[1])
                await ws_manager.send_agents(tenant_id, env)
            else:
                conv_id = int(channel.rsplit(":", 1)[1])
                await ws_manager.send(conv_id, env)
        except Exception as exc:  # noqa: BLE001
            _log.warning("pubsub forward failed: %s", exc)
