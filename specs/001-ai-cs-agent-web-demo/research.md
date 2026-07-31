# Phase 0 研究：AI 客服 Agent 平台 — Web Demo

**日期**: 2026-07-29　**规格**: [spec.md](./spec.md)　**计划**: [plan.md](./plan.md)

每条：Decision（结论）/ Rationale（理由）/ Alternatives（备选）。所有条目均无遗留 NEEDS CLARIFICATION。

---

## R-01 混合检索与重排（Qdrant）

- **Decision**：用 Qdrant `Query API` 单请求内组合 dense 向量与 sparse 向量，使用内置 RRF（Reciprocal Rank Fusion）融合两路结果；embedding 走 LLM 网关的多语言 embedding 模型（如 bge-m3 / text-embedding-3 系列，网关侧可切）；sparse 用 Qdrant 支持的 BM25/SPLADE 风格稀疏向量或本地 `fastembed` 生成。demo 重排先只用 RRF；预留交叉编码器 reranker 作为可配开关（默认关，避免额外重服务）。
- **Rationale**：单请求融合最省往返、无需独立检索融合层；RRF 对「语义+关键词」双路稳健且零训练；多语言 embedding 满足中/英并为阿/乌预留。契合「一键起、别上重框架」。
- **Alternatives**：① 独立 Elasticsearch 做关键词——增部署负担，弃；② 仅 dense——关键词精确匹配（如产品名/错误码）召回差；③ 上线即接 cross-encoder reranker——demo 阶段收益不抵延迟与部署成本。

## R-02 转人工「答不出」判据（对齐澄清 Q1）

- **Decision**：判据实现为 `domain/routing.py` 纯函数 `should_escalate(retrieval, llm_signal, user_intent) -> EscalateReason | None`。混合信号：(a) 检索最高相关分 < `bot_config.retrieval_threshold`；**或** (b) LLM 按结构化输出返回 `need_human=true`；**或** (c) 用户显式意图「转人工/talk to a human」。任一命中即转。阈值与提示词由 `bot_config` 承载，可租户级配置。
- **Rationale**：纯函数 → 可单测、可复现 SC-004；判据脱离 LangGraph → 满足「领域逻辑不依赖编排框架」。
- **Alternatives**：① 仅阈值——召回好而生成差漏判；② 仅 LLM 自评——阈值漂移、难测。均在 clarify 阶段否决。

## R-03 LangGraph 图与流式（对齐共识决策 4/13）

- **Decision**：图为线性带一处分支：`ingest → noise_filter →（噪音命中?→ canned_reply 终止）→ retrieve → grade →（escalate?→ handoff 终止 | generate 流式终止）`；**不设独立 `rerank` 节点**——RRF 融合与可选 cross-encoder 重排都属 `services/retrieval.py` 的内部实现细节，不外化为图节点（避免节点空转与职责重复）；`tool` 节点作为 grade 后的占位分支存在但 demo 不接线。用 `graph.astream_events(v2)` 捕获 `on_chat_model_stream` 事件把 token 逐块交给 `chat_service` → WS。**不使用** LangGraph checkpointer；会话多轮上下文由 `chat_service` 从 MySQL 读取后注入 state。
- **Rationale**：astream_events 是 LangGraph 官方流式 token 出口；不用 checkpointer 避免把持久化语义绑死在编排层，保留替换余地（可退化为普通函数管道）。
- **Alternatives**：① 用 checkpointer 做会话记忆——领域耦合、迁移成本高；② 自研状态机不用 LangGraph——放弃共识既定的可视化/可组合收益。

## R-04 实时通道与多实例扇出（对齐澄清 Q3、共识决策 3）

- **Decision**：进程内 `ws_manager` 维护 `conversation_id → {WebSocket}` 注册；跨实例经 Redis Pub/Sub 频道 `rt:{tenant_id}:conv:{conversation_id}` 广播，每实例订阅并向本地连接扇出。在线坐席态存**按租户分片**的 Redis `SET rt:{tenant_id}:agents:online`（与行级隔离主张一致）。demo 单实例即可跑通，Redis 通道保证水平扩展不改协议。
- **Rationale**：MySQL 为事实源、Redis 只做易失的实时/在线态，恢复从 MySQL 回读——直接落实澄清 Q3。
- **Alternatives**：① 纯内存无 Redis——多实例不可扩、坐席态丢失；② 全走 DB 轮询——延迟高、打不到 2s。

## R-05 多租户行级隔离（对齐共识决策 6）

- **Decision**：ASGI 中间件从请求解析租户：管理端/坐席端由会话令牌载荷带 `tenant_id`；widget/webhook 由 channel 的 URL token 反查 `tenant_id`。解析结果存 `ContextVar`。所有 SQL 仓储在构造 query 时强制追加 `WHERE tenant_id = :ctx`；写入自动填充。开源单机启动时 seed 一个 `default` 租户。
- **Rationale**：中间件统一注入 + 仓储层强制过滤，避免每个 handler 手写租户条件导致漏网（SC-007 零泄漏）。
- **Alternatives**：① MySQL 原生 RLS——8.0 无行安全策略；② 每租户独立库/schema——违背「共库」决策、部署重。

## R-06 坐席认证（对齐澄清 Q4）

- **Decision**：`agents` 表存 `username` + `password_hash`（argon2）；`POST /auth/login` 校验后签发短期 **JWT** 会话令牌（HS256，密钥来自 `JWT_SECRET`，默认 8h 过期），载荷含 `agent_id` + `tenant_id`。单一预置默认坐席由 seed 写入。无自助注册、无 RBAC、无刷新令牌。
- **Rationale**：满足「非匿名但极简」；令牌自带租户，天然接入 R-05 注入。选 JWT 而非「不透明令牌 + Redis」，是因为 Redis 在本架构中被限定为易失的实时/在线态载体（澄清 Q3），不宜承担认证事实源。
- **Alternatives**：① 不透明令牌 + Redis 存储——与 Q3 的 Redis 职责边界冲突，弃；② OAuth/第三方 IdP——demo 过重；③ 纯匿名——不满足审计与归属。

## R-07 ORM 与迁移

- **Decision**：SQLAlchemy 2.x async（`asyncmy`/`aiomysql` 驱动）+ Alembic 迁移。
- **Rationale**：与 FastAPI async 栈一致；Alembic 迁移可纳入 compose 启动前置，保证 `docker compose up` 后表结构就绪（SC-001）。
- **Alternatives**：Tortoise/SQLModel——生态与迁移成熟度弱于 SQLAlchemy+Alembic。

## R-08 widget 前端形态

- **Decision**：widget 用极简技术（原生 TS 或 Preact 单包），产物为可 `<script>` 内嵌的独立 bundle，走 WS 连接；与坐席工作台（React+TS+Vite）分离目录、独立构建。
- **Rationale**：widget 要能嵌任意站点、体积小；工作台是复杂交互 SPA，两者诉求不同。
- **Alternatives**：widget 也用 React——体积与内嵌友好度差。

## R-09 噪音前置（对齐澄清 Q2、FR-012）

- **Decision**：`domain/routing.py::classify_noise(text) -> bool`：规则集=空/超短(<2 有效字符)、纯标点/符号、纯 emoji、问候语白名单（多语，中/英 hi/hello/你好/在吗…）。命中 → 直接返回固定引导话术，不进检索/LLM。
- **Rationale**：76% 噪音若全量进 LLM 成本不可接受；纯规则零成本、可单测。
- **Alternatives**：轻量分类模型——demo 阶段过度工程；不做——违背 FR-012。

## R-10 一键起编排

- **Decision**：`docker-compose.yml` 服务：`mysql`、`redis`、`qdrant`、`api`（含迁移+seed 的 entrypoint）、`worker`、`widget`、`agent-console`（构建为静态由 api 或 nginx 托管）。各依赖带 healthcheck，`api` `depends_on: condition: service_healthy`。`.env.example` 仅需填 LLM 网关 `base_url`/`api_key`。
- **Rationale**：落实 SC-001「未做额外手工配置即可跑通」。
- **Alternatives**：脚本手动拉起——违背「一键」承诺。
