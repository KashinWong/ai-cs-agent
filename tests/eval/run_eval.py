"""评测集批量执行与命中率统计（T043b）。

针对每条评测问题走一次 REST webhook 入站，读取会话内 AI/system 回复，判定：
  - expect_human 的题：是否触发转人工（status=pending_human 或 system handoff）；
  - expect_kb 的题：AI 回答是否包含期望知识条目关键片段。
输出中/英各自「正确率」，供 test_retrieval_accuracy.py 断言 >= 90%（SC-002）。

需 docker compose 起服务 + 有效 LLM 网关。用法：
  AI_CS_BASE=http://localhost:8000 WEBHOOK_TOKEN=xxx python3 tests/eval/run_eval.py
"""
import os
import time
from pathlib import Path

import httpx
import yaml

BASE = os.environ.get("AI_CS_BASE", "http://localhost:8000")
WEBHOOK_TOKEN = os.environ.get("WEBHOOK_TOKEN", "")
HERE = Path(__file__).resolve().parent


def _login() -> str:
    r = httpx.post(
        f"{BASE}/api/v1/auth/login",
        json={
            "username": os.environ.get("SEED_AGENT_USERNAME", "agent"),
            "password": os.environ.get("SEED_AGENT_PASSWORD", "agent123"),
        },
        timeout=10,
    )
    r.raise_for_status()
    return r.json()["token"]


def _ask(token: str, ext_id: str, text: str) -> dict:
    r = httpx.post(
        f"{BASE}/api/v1/channels/webhook/{WEBHOOK_TOKEN}",
        json={"external_user_id": ext_id, "text": text},
        timeout=60,
    )
    r.raise_for_status()
    conv_id = r.json()["conversation_id"]
    time.sleep(0.5)
    msgs = httpx.get(
        f"{BASE}/api/v1/conversations/{conv_id}/messages",
        headers={"Authorization": f"Bearer {token}"},
        timeout=10,
    ).json()
    conv = httpx.get(
        f"{BASE}/api/v1/conversations",
        headers={"Authorization": f"Bearer {token}"},
        timeout=10,
    ).json()
    status = next((c["status"] for c in conv if c["id"] == conv_id), "ai")
    return {"messages": msgs, "status": status}


def _judge(row: dict, result: dict) -> bool:
    escalated = result["status"] == "pending_human" or any(
        m["source"] == "system" for m in result["messages"]
    )
    if row.get("expect_human"):
        return escalated
    ai_text = " ".join(m["content"] for m in result["messages"] if m["source"] == "ai")
    frag = str(row.get("expect_kb", "")).lower()
    return (not escalated) and frag in ai_text.lower()


def run(dataset: str, token: str) -> tuple[int, int]:
    rows = yaml.safe_load((HERE / dataset).read_text(encoding="utf-8"))
    ok = 0
    for i, row in enumerate(rows):
        res = _ask(token, f"eval-{dataset}-{i}", row["q"])
        passed = _judge(row, res)
        ok += int(passed)
        print(f"  [{'PASS' if passed else 'FAIL'}] {row['q']}")
    return ok, len(rows)


def main() -> dict:
    if not WEBHOOK_TOKEN:
        raise SystemExit("WEBHOOK_TOKEN required")
    token = _login()
    report = {}
    for ds in ("dataset_zh.yaml", "dataset_en.yaml"):
        print(f"== {ds} ==")
        ok, total = run(ds, token)
        rate = ok / total if total else 0.0
        report[ds] = rate
        print(f"== {ds}: {ok}/{total} = {rate:.0%} ==")
    return report


if __name__ == "__main__":
    print(main())
