# 契约：REST API（管理端 / 坐席工作台 / 认证 / Webhook）

所有 REST 走 `/api/v1`。鉴权：坐席端携带 `Authorization: Bearer <session_token>`（载荷含 tenant_id+agent_id）；管理端 demo 复用坐席令牌。租户由令牌或 URL token 决定，不接受 body 传 tenant_id。错误体统一 `{ "error": { "code": str, "message": str } }`。

---

## 健康检查

### GET /api/v1/health
无需鉴权。汇总各依赖可达性，供 `docker compose up` 后的就绪判定与冒烟脚本使用。
响应 200：
```json
{ "status": "ok", "deps": { "mysql": "ok", "redis": "ok", "qdrant": "ok", "llm_gateway": "ok" } }
```
任一依赖不可达时返回 503，`status="degraded"` 且对应 dep 为 `"error"`。

---

## 认证

### POST /api/v1/auth/login
请求：`{ "username": str, "password": str }`
响应 200：`{ "token": str, "agent": { "id": int, "display_name": str }, "tenant": { "slug": str } }`
错误：401 `invalid_credentials`

---

## 管理端配置（US4）

### 知识条目
- `GET  /api/v1/kb/items?lang=&q=&page=` → 列表（仅当前租户）
- `POST /api/v1/kb/items` body `{ title, content, lang, meta? }` → 201，触发异步向量 upsert（`vector_status=pending→indexed`）
- `PUT  /api/v1/kb/items/{id}` → 更新并重建向量
- `DELETE /api/v1/kb/items/{id}` → 删除并移除向量

### 渠道
- `GET  /api/v1/channels`
- `POST /api/v1/channels` body `{ type, config? }` → 返回含生成的 `token`
- `PATCH /api/v1/channels/{id}` `{ enabled?, config? }`

### 租户（单机默认租户；多租户预留）
- `GET  /api/v1/tenant` → 当前租户信息
- `POST /api/v1/tenants` → **默认禁用**：受 `ENABLE_TENANT_PROVISIONING` 开关控制（默认 false），关闭时返回 403 `provisioning_disabled`

### bot 配置
- `GET  /api/v1/bot-config`
- `PUT  /api/v1/bot-config` `{ model?, system_prompt?, retrieval_threshold?, top_k? }`

---

## 坐席工作台（US2/US3）

### GET /api/v1/conversations?status=&page=
响应：`[{ id, status, lang, last_activity_at, unread, assigned_agent_id, preview }]`
> 列表实时增量另经 WS（见 websocket.md `agent` 流）；本接口为初次加载与分页。

### GET /api/v1/conversations/{id}/messages?after_id=
响应：`[{ id, source, content, lang, created_at, meta }]`（时间序，`source` 标注用户/AI/坐席/system）

### POST /api/v1/conversations/{id}/claim
坐席接管。前置 `status=pending_human`（或 `ai` 主动接管）。→ `status=human`, `assigned_agent_id=当前坐席`；AI 停答。幂等：已被他人接管返回 409 `already_claimed`。

### POST /api/v1/conversations/{id}/reply
body `{ content, lang? }` → 落 `message(source=agent)` 并经 WS 实时推给用户（FR-006，SC-005 < 2s）。前置 `status=human` 且归属当前坐席，否则 403。

### POST /api/v1/conversations/{id}/mode
body `{ mode: "ai" | "human" }` → AI↔人工切换（FR-007）。切回 `ai` 后引擎恢复应答。

### POST /api/v1/conversations/{id}/close → `status=closed`

---

## 通用 Webhook 入站（US5）

### POST /api/v1/channels/webhook/{token}
由 `token` 反查租户与渠道（research R-05）。
请求（归一化前的通用信封）：
```json
{ "external_user_id": "str", "text": "str", "lang": "zh|en|...(可选)", "metadata": {} }
```
处理：创建/续接 `contact` 与 `conversation` → 走同一引擎链路（噪音→检索→生成/转人工）。
响应 202：`{ "conversation_id": int, "accepted": true }`
错误：
- 404 `channel_not_found`（token 无效）
- 400 `invalid_payload`（缺 text/external_user_id）
- 校验失败绝不产生脏会话（FR-011）。

> 回投：demo 通过轮询 `GET .../messages` 或 webhook 渠道配置的 `callback_url`（占位）取回 AI/坐席回复。
