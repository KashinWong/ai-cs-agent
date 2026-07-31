# Phase 1 领域模型与落库结构

**日期**: 2026-07-29　**规格**: [spec.md](./spec.md)　**计划**: [plan.md](./plan.md)

原则：所有业务表带 `tenant_id`（BIGINT/CHAR，索引首列）；仓储层强制注入过滤（research R-05）。会话与消息以 MySQL 为**持久事实源**（澄清 Q3）。向量存 Qdrant，文本+元数据存 MySQL，经 `knowledge_item_id` 逻辑关联。

---

## 实体关系

```
tenant (1) ──< channel
           ──< knowledge_item
           ──< bot_config
           ──< agent
           ──< contact
           ──< conversation ──< message
           ──< tool (占位)
conversation >── channel / contact / agent(可空)
message >── conversation
```

---

## 表结构

### tenant（租户/工作区）
| 列 | 类型 | 约束/说明 |
|---|---|---|
| id | BIGINT PK | 自增 |
| slug | VARCHAR(64) | 唯一；单机默认 `default` |
| name | VARCHAR(128) | |
| created_at / updated_at | DATETIME | |

### channel（渠道接入配置）
| 列 | 类型 | 说明 |
|---|---|---|
| id | BIGINT PK | |
| tenant_id | BIGINT FK | 索引 |
| type | ENUM(`widget`,`webhook`,`feishu`,`whatsapp`,`telegram`) | 后三仅骨架 |
| token | VARCHAR(64) | 唯一；widget/webhook 入站鉴权与租户反查 |
| config_json | JSON | 通道特定配置 |
| enabled | BOOL | |

### knowledge_item（知识条目）
| 列 | 类型 | 说明 |
|---|---|---|
| id | BIGINT PK | |
| tenant_id | BIGINT FK | 索引 |
| kb_id | BIGINT | 所属知识库（demo 可单库）|
| lang | VARCHAR(8) | `zh`/`en`/… |
| title | VARCHAR(256) | |
| content | TEXT | 检索命中后的回答依据 |
| meta_json | JSON | 标签/分类/来源 |
| vector_status | ENUM(`pending`,`indexed`,`stale`) | 与 Qdrant 同步态 |
| updated_at | DATETIME | |

> Qdrant：collection `kb_{tenant_id}` 或统一 collection + payload `tenant_id` 过滤；point id = `knowledge_item_id`，payload 含 `lang/title/kb_id`；dense + sparse 双向量。

### bot_config（应答配置）
| 列 | 类型 | 说明 |
|---|---|---|
| id | BIGINT PK | |
| tenant_id | BIGINT FK | |
| model | VARCHAR(64) | 网关模型名 |
| system_prompt | TEXT | 含护栏「仅依据知识库、否则 need_human」 |
| retrieval_threshold | FLOAT | 转人工检索分阈值（research R-02）|
| top_k | INT | 检索召回数 |
| enabled | BOOL | |

### agent（坐席）
| 列 | 类型 | 说明 |
|---|---|---|
| id | BIGINT PK | |
| tenant_id | BIGINT FK | |
| username | VARCHAR(64) | 租户内唯一 |
| password_hash | VARCHAR(255) | argon2/bcrypt |
| display_name | VARCHAR(128) | |

### contact（外部用户映射）
| 列 | 类型 | 说明 |
|---|---|---|
| id | BIGINT PK | |
| tenant_id | BIGINT FK | |
| channel_id | BIGINT FK | |
| external_id | VARCHAR(128) | 渠道内用户标识；widget 匿名则用会话内 uuid |
| display_name | VARCHAR(128) | 可空 |

### conversation（会话）
| 列 | 类型 | 说明 |
|---|---|---|
| id | BIGINT PK | |
| tenant_id | BIGINT FK | 索引 |
| channel_id | BIGINT FK | |
| contact_id | BIGINT FK | |
| status | ENUM(`ai`,`pending_human`,`human`,`closed`) | 状态机见下 |
| assigned_agent_id | BIGINT FK NULL | 接管坐席 |
| lang | VARCHAR(8) | 主要语言 |
| last_activity_at | DATETIME | 列表排序 |
| created_at | DATETIME | |

索引：`(tenant_id, status, last_activity_at)` 支撑工作台列表实时查询。

### message（消息）
| 列 | 类型 | 说明 |
|---|---|---|
| id | BIGINT PK | |
| tenant_id | BIGINT FK | 索引 |
| conversation_id | BIGINT FK | 索引 `(conversation_id, id)` |
| source | ENUM(`user`,`ai`,`agent`,`system`) | FR-006 来源标注 |
| content | TEXT | |
| lang | VARCHAR(8) | |
| meta_json | JSON | 检索命中项、noise 命中、escalate 原因等可观测信息 |
| created_at | DATETIME(3) | 毫秒序 |

### tool（占位，第二期）
| 列 | 类型 | 说明 |
|---|---|---|
| id | BIGINT PK | |
| tenant_id | BIGINT FK | |
| name | VARCHAR(64) | |
| schema_json | JSON | function schema 占位，MVP 不执行 |

---

## 会话状态机（`domain/conversation.py`）

```
         user msg / noise-miss
  (new) ───────────────► ai
    ai ──escalate(判据命中/用户要人工)──► pending_human
    ai ──user idle/close──► closed
 pending_human ──agent 接管──► human
 human ──agent 切回 AI──► ai
 human ──agent 结束──► closed
 pending_human ──（无坐席）──► pending_human（保持排队 + 用户提示，澄清 Q5）
```

**不变量**：
- `status=human` 时引擎**不得**自动应答（FR-005/边界）。
- `status=pending_human` 时 AI 停答，等待接管；无坐席仅排队不自动关闭（Q5）。
- 状态转移是纯函数 `transition(current, event) -> next | Error`，非法转移抛领域错误，可单测。

---

## 校验规则（来自需求）

- FR-001：同一 `conversation` 内 message 时间序即多轮上下文来源。
- FR-003/FR-013：`ai` 消息生成前必须有检索依据；零命中 → 不生成 `ai` 内容，转 `pending_human` 或兜底 `system` 话术。
- FR-010/SC-007：任何跨 `tenant_id` 的读写在仓储层被过滤阻断。
- FR-015：widget 重连按 `conversation_id` 从 message 表回读历史。
