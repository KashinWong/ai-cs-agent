# 契约：WebSocket（用户 widget 流式 + 坐席实时）

两类 WS 端点，消息统一 JSON 信封：`{ "type": str, "data": {...}, "ts": epoch_ms }`。

---

## 1. 用户 widget：`/ws/widget?channel_token=&conversation_id?=&contact_key?=`

握手：由 `channel_token` 反查租户+渠道（research R-05）。首连无 `conversation_id` 则新建；带则按 id 校验归属并**从 MySQL 回读历史**（FR-015 断线/刷新恢复）。

### 客户端 → 服务端
| type | data | 说明 |
|---|---|---|
| `user_message` | `{ text, lang? }` | 用户提问 |
| `request_human` | `{}` | 显式转人工，服务端直接转 `pending_human` 不经检索/LLM（FR-004，实现见 tasks T044a）|
| `resume` | `{ conversation_id }` | 重连后恢复；服务端回 `history` |
| `ping` | `{}` | 保活 |

### 服务端 → 客户端
| type | data | 说明 |
|---|---|---|
| `conversation` | `{ id, status }` | 建立/恢复会话 |
| `history` | `{ messages: [...] }` | 恢复时全量历史（源自 MySQL）|
| `ai_token` | `{ message_id, delta }` | **流式** token 增量（SC-003 首块 < 2s，research R-03）|
| `ai_done` | `{ message_id, content }` | 本条 AI 回答结束 |
| `noise_reply` | `{ content }` | 噪音命中的固定话术（FR-012，未进 LLM）|
| `handoff` | `{ status: "pending_human", notice }` | 转人工中，notice=「正在为您转接人工，请稍候」（澄清 Q5）|
| `agent_message` | `{ message_id, content, source: "agent" }` | 坐席回复实时下发（FR-006，SC-005 < 2s）|
| `mode_changed` | `{ mode }` | AI↔人工切换通知 |
| `error` | `{ code, message }` | |

流式时序：`user_message` →（噪音?→`noise_reply`）｜（`ai_token`×N → `ai_done`）｜（低置信→`handoff`）。

---

## 2. 坐席实时：`/ws/agent`（Bearer 令牌握手，载荷带 tenant_id+agent_id）

用于工作台会话列表实时增量与新消息提醒（US3），避免轮询。

### 服务端 → 客户端
| type | data | 说明 |
|---|---|---|
| `conversation_upserted` | `{ id, status, last_activity_at, unread, preview }` | 新会话/状态变化/新消息触发列表刷新 |
| `new_message` | `{ conversation_id, message: {...} }` | 已打开会话的新消息（用户/AI）|
| `pending_count` | `{ count }` | 待接管计数徽标 |

### 客户端 → 服务端
| type | data | 说明 |
|---|---|---|
| `subscribe` | `{ conversation_id }` | 打开某会话，接收其 `new_message` |
| `unsubscribe` | `{ conversation_id }` | |
| `ping` | `{}` | 兼在线态刷新（Redis online set）|

> 广播实现：服务端在落库后 publish 到 Redis `rt:{tenant}:conv:{id}`（用户流）与 `rt:{tenant}:agents`（坐席流），各实例订阅后向本地 WS 扇出（research R-04）。坐席回复/接管/切换在 REST 处理成功后即触发对应 WS 事件，保证双向 < 2s。
