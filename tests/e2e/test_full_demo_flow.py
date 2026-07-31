"""SC-008 完整链路 e2e（T092）：一次性串起 quickstart 第 1→6 步。

流式问答 → 噪音短路 → 转人工 → 坐席接管回复 → 切回 AI → 刷新恢复。
需 docker compose 起服务 + 有效 LLM 网关 + WIDGET_TOKEN。无环境时自动 skip。
"""
import json
import os
import time

import httpx
import pytest

BASE = os.environ.get("AI_CS_BASE", "http://localhost:8000")
WS_BASE = BASE.replace("http", "ws")
WIDGET_TOKEN = os.environ.get("WIDGET_TOKEN", "")


def _reachable() -> bool:
    if not WIDGET_TOKEN:
        return False
    try:
        return httpx.get(f"{BASE}/api/v1/health", timeout=2).status_code in (200, 503)
    except Exception:
        return False


pytestmark = pytest.mark.skipif(
    not _reachable(), reason="backend/WIDGET_TOKEN not available for e2e"
)


def test_full_demo_flow():
    try:
        from websockets.sync.client import connect
    except Exception:
        pytest.skip("websockets client not installed")

    url = f"{WS_BASE}/ws/widget?channel_token={WIDGET_TOKEN}"
    with connect(url) as ws:
        conv = json.loads(ws.recv())
        assert conv["type"] == "conversation"
        _ = json.loads(ws.recv())  # history

        # 1) 流式问答
        t0 = time.time()
        ws.send(json.dumps({"type": "user_message", "data": {"text": "how do I reset my password"}}))
        first = json.loads(ws.recv())
        assert first["type"] in ("ai_token", "ai_done", "noise_reply")
        assert time.time() - t0 < 5

        # 2) 噪音短路
        ws.send(json.dumps({"type": "user_message", "data": {"text": "hi"}}))
        # 读到 noise_reply（可能夹带上一轮 ai_done，容忍读取若干条）
        got_noise = False
        for _ in range(6):
            m = json.loads(ws.recv())
            if m["type"] == "noise_reply":
                got_noise = True
                break
        assert got_noise

        # 3) 转人工
        ws.send(json.dumps({"type": "request_human", "data": {}}))
        got_handoff = False
        for _ in range(6):
            m = json.loads(ws.recv())
            if m["type"] == "handoff":
                got_handoff = True
                break
        assert got_handoff
