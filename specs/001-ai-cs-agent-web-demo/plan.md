# 实现计划：AI 客服 Agent 平台 — 自包含 Web Demo

**Feature 目录**: `specs/001-ai-cs-agent-web-demo`
**代号**: ai-cs-agent（web demo 里程碑）
**创建日期**: 2026-07-29
**状态**: Plan（已生成设计工件，待 `/speckit-tasks`）
**规格**: [spec.md](./spec.md)
**上游共识**: `docs/00-设计共识.md`（13 项已锁定决策）

> 说明：本项目无 `.specify/` 脚手架、无 `constitution.md`、无 plan 模板。按 spec-kit 标准结构直接落地本计划及 Phase 0/1 工件（research.md / data-model.md / contracts/ / quickstart.md），与 spec.md 的处理方式一致。

---

## 技术上下文（Technical Context）

| 维度 | 决策 | 来源 |
|---|---|---|
| 语言 / 运行时 | Python 3.11+ | 共识决策 2 |
| 依赖 / 打包 | uv | 共识决策 2 |
| Web 框架 | FastAPI（ASGI，原生 WebSocket + REST） | 共识决策 2/3 |
| 关系存储 | MySQL 8（会话与消息的**持久事实源**） | 澄清 Q3 |
| 缓存 / 实时 | Redis 7（Pub/Sub 广播 + 在线态 + WS 扇出） | 澄清 Q3 |
| 向量库 | Qdrant（混合检索：dense 向量 + sparse/关键词 + 重排） | 共识决策 5 |
| LLM / Embedding | OpenAI 兼容网关（new-api），可切 deepseek/claude/gemini | 共识决策 2 |
| 编排 | LangGraph（约束在 `engine/` 薄层，领域逻辑不依赖） | 共识决策 13 |
| ORM / 迁移 | SQLAlchemy 2.x (async) + Alembic | 派生选型（见 research.md R-07） |
| 坐席前端 | React + TS + Vite SPA（独立目录 `frontend/agent-console`） | 共识决策 8 |
| widget 前端 | 轻量原生/Preact 单文件，可内嵌 `<script>`（`frontend/widget`） | 派生选型（见 research.md R-08） |
| 部署 | docker-compose 一键起（api / worker / mysql / redis / qdrant / frontends） | 共识决策 5/10 |
| 目标平台 | 本地 / 单机 Linux；开源单机 = 一个默认租户 | 共识决策 6 |
| 性能目标 | 流式首字符 < 2s；坐席回复实时 < 2s（本地） | SC-003 / SC-005 |
| 规模假设 | demo 级：并发会话数十、知识条目数百；非生产 SLA | spec 假设 |

**无遗留 NEEDS CLARIFICATION**：spec 的 5 项澄清 + 共识 13 项已覆盖全部架构级未决项；派生技术细节在 `research.md` 收敛。

---

## Constitution Check（宪法门禁）

无 `.specify/memory/constitution.md`。改用 CLAUDE.md 与共识文档中的既定工程原则作为门禁：

| 原则（来自 CLAUDE.md / 共识） | 计划是否满足 | 说明 |
|---|---|---|
| 反对投机性重构、别上重框架 | ✅ | LangGraph 仅约束在 `engine/` 薄层，`domain/` 为纯 Python 无框架依赖，可整层替换 |
| 跑通真实需求优先 | ✅ | Phase 划分以「P1 端到端闭环」为第一可交付，P2/P3 增量 |
| 单人可维护 | ✅ | 分层清晰、依赖倒置；一键 compose 起全栈 |
| 避免重蹈「未验证即上线」 | ✅ | quickstart.md 定义可录屏验收；转人工为安全阀，检索零命中稳定降级 |
| 开源易部署 | ✅ | 全依赖 compose 内置，无外部托管；仅 LLM 网关需一个 base_url+key |

**门禁结论**：通过，无未证成违规。

---

## 项目结构（Project Structure）

```
ai-cs-agent/                            # 独立仓库根（共识决策 13：新建独立仓库）
├── docker-compose.yml                  # 一键起：api/worker/mysql/redis/qdrant/frontends
├── .env.example                        # LLM 网关 base_url/key、DB/Redis/Qdrant 连接
├── pyproject.toml                      # uv 管理
├── backend/
│   ├── Dockerfile
│   ├── entrypoint.sh                   # 启动：迁移 → seed → uvicorn
│   ├── app/
│   │   ├── main.py                     # FastAPI 应用装配、lifespan（DB/Redis/Qdrant 连接池）
│   │   ├── core/
│   │   │   ├── config.py               # pydantic-settings 读取 .env
│   │   │   ├── tenant.py               # 租户上下文（ContextVar）+ 注入中间件
│   │   │   ├── security.py             # argon2 口令 + JWT 会话令牌
│   │   │   └── logging.py              # 结构化日志 + trace_id
│   │   ├── db/
│   │   │   ├── base.py                 # async engine / session factory
│   │   │   ├── models.py               # SQLAlchemy ORM（全表带 tenant_id）
│   │   │   └── migrations/             # Alembic
│   │   ├── domain/                     # 纯领域层（零外部框架依赖）
│   │   │   ├── entities.py             # dataclass 领域实体（Conversation/Message/EscalateReason…）
│   │   │   ├── conversation.py         # 会话状态机（纯函数）
│   │   │   ├── routing.py              # classify_noise / should_escalate / detect_human_intent（纯函数）
│   │   │   └── prompt.py               # RAG 护栏提示 + need_human 结构化输出 schema
│   │   ├── repositories/               # 各聚合的 MySQL 仓储（均继承 TenantScopedRepository）
│   │   │   ├── base.py                 # 强制 tenant_id 过滤的基类
│   │   │   ├── knowledge.py / conversation.py / message.py / contact.py / agent.py
│   │   ├── infra/                      # 外部系统适配（无业务逻辑）
│   │   │   ├── llm_gateway.py          # OpenAI 兼容客户端（chat 流式 + embeddings）
│   │   │   ├── redis_client.py         # 连接池 + Pub/Sub 工厂
│   │   │   └── qdrant_client.py        # collection 初始化 + 客户端封装
│   │   ├── engine/                     # LangGraph 薄层（可替换）
│   │   │   ├── state.py                # GraphState TypedDict
│   │   │   ├── nodes/                  # ingest / noise_filter / retrieve / generate / grade / handoff / tool(占位)
│   │   │   └── graph.py                # 图装配（不设独立 rerank 节点；RRF 属 retrieval 内部）
│   │   ├── channels/
│   │   │   ├── base.py                 # Channel 适配器抽象
│   │   │   ├── webhook.py              # 通用 Webhook 归一化
│   │   │   ├── widget.py               # WS widget 通道适配（可选薄壳）
│   │   │   ├── feishu.py / whatsapp.py / telegram.py   # 适配器骨架（仅 NotImplementedError）
│   │   ├── realtime/
│   │   │   ├── pubsub.py               # Redis 频道 publish/subscribe（rt:{tenant}:conv:{id} 等）
│   │   │   └── ws_manager.py           # WS 连接注册 + 跨实例广播
│   │   ├── services/                   # 应用服务：编排 domain+repo+engine+realtime
│   │   │   ├── embedding.py / indexer.py / retrieval.py
│   │   │   ├── chat_service.py         # 入站消息 → 引擎 → 落库 → 推流
│   │   │   ├── handoff_service.py      # 转人工 / 接管 / AI↔人工切换
│   │   │   └── agent_service.py        # 坐席会话操作（claim/reply/mode/close）
│   │   ├── workers/
│   │   │   └── index_worker.py         # 周期性回填 vector_status=pending/stale 的向量
│   │   └── api/
│   │       ├── deps.py                 # DB session / 当前租户 / 当前坐席 / infra 客户端注入
│   │       ├── health.py               # GET /api/v1/health
│   │       ├── auth.py                 # POST /api/v1/auth/login
│   │       ├── conversations.py        # 会话列表/详情/接管/回复/切换/结束
│   │       ├── kb.py / channels.py / tenants.py / bot_config.py   # 管理端 CRUD
│   │       ├── webhook.py              # POST /api/v1/channels/webhook/{token}
│   │       ├── ws_widget.py            # WS: /ws/widget
│   │       └── ws_agent.py             # WS: /ws/agent
│   └── seeds/
│       └── faq_bilingual.yaml          # 中/英双语泛例 FAQ 种子（≥15 条/语）
├── scripts/
│   ├── seed.py                         # 幂等写入 default 租户/坐席/渠道/bot_config/FAQ
│   └── smoke.sh                        # health / webhook / 登录冒烟
├── tests/
│   ├── conftest.py
│   ├── unit/                           # domain 纯函数（噪音/判据/状态机）
│   ├── integration/                    # 端到端闭环 + 隔离 + 降级
│   ├── eval/                           # SC-002 评测集与 ≥90% 门禁
│   └── e2e/                            # SC-008 完整演示链路
└── frontend/
    ├── widget/                         # 用户 widget（轻量 TS bundle，可 <script> 内嵌）
    └── agent-console/                  # 坐席工作台 React+TS+Vite SPA
```

> 说明：本结构为 tasks.md 落盘后回写的权威结构（2026-07-29 analyze 修订）。与原稿差异：新增 `infra/`（原 `llm/` 并入）、`channels/` 顶层化（适配器去 `adapters/` 子目录）、`engine/nodes/` 由单文件改包、`workers/` 内置、`tests/` 提到根。以本表为准。

**结构决策**：后端单体（modular monolith）——demo 规模不引入微服务；`worker` 在 compose 里独立成服务以示可拆分，代码同仓。依赖方向严格单向：`api → services → {domain, repositories, engine, realtime}`，`domain` 零外部依赖。

---

## Phase 0：研究与选型

详见 [research.md](./research.md)。核心收敛：

- **R-01 混合检索**：Qdrant Query API（dense + sparse 双向量 + 内置 fusion/RRF），关键词走 sparse（BM25 风格）避免额外服务；重排 demo 阶段先用 RRF 融合，reranker 交叉编码器留可选开关。
- **R-02 转人工判据落点**：判据为 `domain/routing.py` 纯函数，engine 节点仅调用；阈值经 bot_config 可配。
- **R-03 LangGraph 流式**：用 `astream_events` 透传 token 到 WS；不使用 LangGraph checkpointer 做持久化（避免领域耦合），持久化由 `chat_service` 显式落 MySQL。图链路 `ingest → noise_filter → retrieve → grade → handoff|generate`，不设独立 `rerank` 节点（RRF 属检索内部）。
- **R-04 实时扇出**：单实例内存 WS manager + Redis Pub/Sub 兜底多实例；demo 单实例够用，Redis 通道预留水平扩展。
- **R-05 租户注入**：ASGI 中间件解析 header/令牌 → `ContextVar`；仓储层统一在 query 追加 `tenant_id` 过滤。

## Phase 1：设计与契约

- 领域模型与落库结构 → [data-model.md](./data-model.md)
- 接口契约（REST + WebSocket + Webhook）→ [contracts/](./contracts/)
- 一键起与可录屏验收流程 → [quickstart.md](./quickstart.md)

---

## Phase 2：任务规划取向（供 /speckit-tasks 参考，本命令不生成 tasks.md）

任务将按**用户故事优先级纵切**，每片可独立交付并演示：

1. **基座**：仓库骨架、compose、配置、DB 迁移、租户中间件、种子 FAQ。
2. **US1（P1）**：知识库 upsert + 混合检索 + LangGraph RAG + widget WS 流式。
3. **US2（P1）**：转人工判据 + 待接管队列 + 坐席接管/回复 + 双向实时 + AI↔人工切换。
4. **US3（P2）**：坐席工作台会话列表实时刷新 + 历史查看。
5. **US4（P2）**：管理端三张配置 CRUD + 隔离验证。
6. **US5（P3）**：通用 Webhook 入站 + 归一化 + 错误校验。
7. **横切**：噪音规则前置、零命中降级、断线恢复、tool 节点占位、集成测试与录屏脚本。

---

## 复杂度与风险跟踪

| 风险 | 缓解 | 对应工件 |
|---|---|---|
| LangGraph 渗入领域逻辑 | 判据/状态机在 domain，engine 仅装配与 IO | data-model.md 状态机 / research.md R-02/R-03 |
| Qdrant 部署负担 | compose 内置，healthcheck 就绪门禁 | quickstart.md / docker-compose |
| 实时前端工作量大 | widget 极简、工作台先列表+详情+接管三件套 | contracts/websocket.md |
| 噪音 76% 成本 | 规则前置短路，命中不进 LLM | domain/routing.py / FR-012 |
| 多语言检索未验 | demo 仅中/英；embedding 选多语言模型预留 | research.md R-01 |
