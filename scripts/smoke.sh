#!/usr/bin/env bash
# 冒烟：health / 坐席登录 / webhook 投递（quickstart.md 冒烟命令，T093）。
set -euo pipefail

BASE="${AI_CS_BASE:-http://localhost:8000}"
USER="${SEED_AGENT_USERNAME:-agent}"
PASS="${SEED_AGENT_PASSWORD:-agent123}"

echo "[smoke] health"
curl -fsS "$BASE/api/v1/health" || echo "(health degraded — 检查 LLM 网关配置)"
echo

echo "[smoke] login"
TOKEN=$(curl -fsS -X POST "$BASE/api/v1/auth/login" \
  -H 'Content-Type: application/json' \
  -d "{\"username\":\"$USER\",\"password\":\"$PASS\"}" | python3 -c 'import sys,json;print(json.load(sys.stdin)["token"])')
echo "[smoke] token acquired: ${TOKEN:0:12}..."

echo "[smoke] pending conversations"
curl -fsS "$BASE/api/v1/conversations?status=pending_human" \
  -H "Authorization: Bearer $TOKEN"
echo

if [ -n "${WEBHOOK_TOKEN:-}" ]; then
  echo "[smoke] webhook inbound"
  curl -fsS -X POST "$BASE/api/v1/channels/webhook/$WEBHOOK_TOKEN" \
    -H 'Content-Type: application/json' \
    -d '{"external_user_id":"smoke-u1","text":"how do I reset my password"}'
  echo
fi

echo "[smoke] done"
