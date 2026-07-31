# Quickstart：一键起与可录屏验收

**目标**：落实 SC-001（未做额外手工配置即可跑通）与 SC-008（完整链路一次性连续录屏）。

---

## 前置

- Docker + Docker Compose
- 一个 OpenAI 兼容 LLM 网关的 `base_url` 与 `api_key`（含 chat 与 embedding 能力）

## 启动

```bash
cp .env.example .env          # 仅需填 LLM_GATEWAY_BASE_URL / LLM_GATEWAY_API_KEY
docker compose up -d          # 起 mysql/redis/qdrant/api/worker/widget/agent-console
# api entrypoint 自动执行 Alembic 迁移 + seed（default 租户 + 双语 FAQ + 默认坐席）
docker compose ps            # 等所有 healthcheck 变 healthy
```

默认端点（compose 暴露）：
- Widget demo 页：`http://localhost:8080/widget`
- 坐席工作台：`http://localhost:8080/console`
- API：`http://localhost:8000/api/v1`
- Qdrant：`localhost:6333`　MySQL：`localhost:3306`　Redis：`localhost:6379`

默认坐席（seed）：`agent / agent123`（`.env` 可覆盖）。

---

## 可录屏验收脚本（对应 SC-008 完整链路）

1. **AI 流式问答（US1 / SC-002/003）**
   - 打开 `/widget`，中文问「怎么重置密码」→ 观察答案**流式逐字**出现，首字符 < 2s。
   - 英文问「how do I reset my password」→ 返回等价英文答案。
2. **噪音短路（FR-012）**
   - 发「hi」/「?」/ 单个 emoji → 立即返回固定引导话术，无 LLM 延迟。
3. **转人工（US2 / SC-004）**
   - 问一个知识库覆盖不到的问题（如「帮我查订单 X 的物流」）→ widget 显示「正在为您转接人工，请稍候」，会话转 `pending_human`。
   - 或直接发「转人工」→ 立即转接。
4. **坐席接管与实时回复（US2/US3 / SC-005）**
   - 另开 `/console` 用默认坐席登录 → 待接管列表出现该会话（实时，无需刷新）。
   - 点击接管 → 会话转 `human`，AI 停答。
   - 坐席发一条回复 → 切回 widget，用户侧 < 2s 收到，标注来源「人工」。
5. **AI↔人工切换（FR-007）**
   - 坐席在该会话点「切回 AI」→ 用户后续提问重新由 AI 应答。
6. **断线恢复（FR-015）**
   - 刷新 widget 页面 → 历史消息与会话上下文完整恢复（源自 MySQL）。
7. **配置生效（US4 / SC-006）**
   - 工作台/管理端新增一条 FAQ → 1 分钟内 widget 提问可命中该新条目。
8. **隔离（SC-007，可选演示）**
   - 以第二租户令牌访问 → 看不到租户 A 的任何会话/知识。

以上 1→6 可一次性连续录屏，无需重启服务或跳步（SC-008）。

---

## 冒烟命令（脚本化验证，供 CI/自测）

```bash
# 健康检查
curl -s localhost:8000/api/v1/health
# Webhook 入站（US5）
curl -s -X POST localhost:8000/api/v1/channels/webhook/$WEBHOOK_TOKEN \
  -H 'Content-Type: application/json' \
  -d '{"external_user_id":"u1","text":"how do I reset my password"}'
# 坐席登录
curl -s -X POST localhost:8000/api/v1/auth/login -d '{"username":"agent","password":"agent123"}'
```
