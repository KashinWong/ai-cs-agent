# 任务清单：AI 客服 Agent 平台 — 自包含 Web Demo

**Feature 目录**: `specs/001-ai-cs-agent-web-demo`
**创建日期**: 2026-07-29
**状态**: Tasks（待 `/speckit-implement`）
**输入工件**: [spec.md](./spec.md) · [plan.md](./plan.md) · [research.md](./research.md) · [data-model.md](./data-model.md) · [contracts/rest-api.md](./contracts/rest-api.md) · [contracts/websocket.md](./contracts/websocket.md) · [quickstart.md](./quickstart.md)

> 本项目无 `.specify/templates/tasks-template.md`，按 spec-kit 标准结构生成，与 spec/plan 阶段处理方式一致。

## 约定

- **格式**：`- [ ] TaskID [P?] [Story?] 描述（含文件路径）`
- **[P]**：可与同组其他 [P] 任务并行（不同文件、无未完成依赖）
- **[USn]**：归属的用户故事；Setup / Foundational / Polish 阶段无故事标签
- **路径**：均为仓库根（`p_549568b9f0/`）下的项目相对路径
- **测试策略**：spec 未要求 TDD，故仅在领域纯函数与端到端验收处安排测试任务（这两处是 SC-004/SC-007 可复现的关键）

---

## Phase 1：Setup（仓库骨架与工具链）

**目标**：`git clone` 后具备可构建的空骨架与一键起编排的外壳。

- [X] T001 按 plan.md「项目结构」创建目录骨架（`backend/app/{core,db,domain,engine,engine/nodes,services,repositories,channels,realtime,infra,workers,api}/`、`backend/seeds/`、`frontend/{widget,agent-console}/`、`scripts/`、`tests/{unit,integration,e2e,eval}/`），每个 Python 包含 `__init__.py`（修复 C3：补 `channels/`、`workers/`、`engine/nodes/`，正式引入 `infra/`）
- [X] T002 [P] 创建 `pyproject.toml`（uv 管理，Python 3.11+），声明依赖：fastapi、uvicorn[standard]、sqlalchemy[asyncio]、aiomysql、alembic、redis、qdrant-client、langgraph、langchain-openai、pydantic-settings、argon2-cffi、python-jose、fastembed、pytest、pytest-asyncio、httpx、ruff
- [X] T003 [P] 创建 `.env.example`：`LLM_GATEWAY_BASE_URL`、`LLM_GATEWAY_API_KEY`、`LLM_CHAT_MODEL`、`LLM_EMBEDDING_MODEL`、`MYSQL_DSN`、`REDIS_URL`、`QDRANT_URL`、`SEED_AGENT_USERNAME`、`SEED_AGENT_PASSWORD`、`JWT_SECRET`（对齐 quickstart.md「仅需填网关两项」）
- [X] T004 [P] 创建 `ruff.toml` 与 `pytest.ini`（asyncio_mode=auto），配置 lint/format 与测试发现路径
- [X] T005 创建 `docker-compose.yml`：服务 `mysql`(8.0)、`redis`(7)、`qdrant`、`api`、`worker`、`agent-console`，各基础设施带 healthcheck，`api` 用 `depends_on: condition: service_healthy`（research R-10，FR-014）
- [X] T006 [P] 创建 `backend/Dockerfile`（uv 安装依赖 + 非 root 运行）
- [X] T007 [P] 初始化 `frontend/widget/`：Vite + TS 极简 bundle 配置，产物可 `<script>` 内嵌（research R-08）
- [X] T008 [P] 初始化 `frontend/agent-console/`：Vite + React + TS SPA 脚手架，配置 `/api` 与 `/ws` 代理

**检查点**：`docker compose config` 校验通过；`uv sync` 成功；两个前端 `npm run build` 产出空壳页面。

---

## Phase 2：Foundational（阻塞所有用户故事的前置）

**⚠️ 本阶段全部完成前，任何用户故事都无法开工。**

- [X] T009 实现 `backend/app/core/config.py`：pydantic-settings 读取 `.env`，暴露 `Settings` 单例（DB/Redis/Qdrant/LLM 网关/JWT/seed 配置）
- [X] T010 [P] 实现 `backend/app/core/logging.py`：结构化 JSON 日志 + `trace_id` ContextVar，供全链路排查
- [X] T011 实现 `backend/app/db/base.py`：SQLAlchemy 2.x async engine、`async_session_factory`、`Base` 声明基类（research R-07）
- [X] T012 实现 `backend/app/db/models.py`：按 data-model.md 定义全部 9 张表 ORM 模型（`tenant`、`channel`、`knowledge_item`、`bot_config`、`agent`、`contact`、`conversation`、`message`、`tool`），业务表统一带 `tenant_id` 且置于索引首列，`conversation` 建 `(tenant_id, status, last_activity_at)` 复合索引
- [X] T013 初始化 Alembic 于 `backend/app/db/migrations/` 并生成首版迁移（对应 T012 全部表与索引）
- [X] T014 实现 `backend/app/core/tenant.py`：`tenant_ctx` ContextVar + ASGI 中间件；令牌载荷解析（坐席/管理端）与 channel token 反查（widget/webhook）两条注入路径（research R-05，FR-010）
- [X] T015 实现 `backend/app/repositories/base.py`：`TenantScopedRepository` 基类，所有 `select/update/delete` **强制**追加 `WHERE tenant_id = tenant_ctx.get()`，写入自动填充 `tenant_id`；上下文缺失时抛错而非放行（SC-007）
- [X] T016 [P] 实现 `backend/app/core/security.py`：argon2 口令哈希/校验 + 会话令牌签发/校验（载荷含 `agent_id` + `tenant_id`，research R-06）
- [X] T017 [P] 实现 `backend/app/infra/redis_client.py`：连接池 + 健康探测 + Pub/Sub 客户端工厂
- [X] T018 [P] 实现 `backend/app/infra/qdrant_client.py`：客户端封装 + 启动时确保 collection 存在（dense + sparse 双向量配置，payload 含 `tenant_id`/`lang`/`kb_id`，research R-01）
- [X] T019 [P] 实现 `backend/app/infra/llm_gateway.py`：OpenAI 兼容客户端封装（chat 流式 + embedding），base_url/api_key 来自配置，模型名可切
- [X] T020 实现 `backend/app/api/deps.py`：DB session、当前租户、当前坐席、各 infra 客户端的依赖注入
- [X] T021 实现 `backend/app/main.py`：FastAPI 应用装配、lifespan 管理连接池、注册 tenant 中间件与路由、CORS
- [X] T022 [P] 实现 `backend/app/api/health.py`：`GET /api/v1/health` 汇总 MySQL/Redis/Qdrant/LLM 网关可达性（quickstart 冒烟用）
- [X] T023 实现 `scripts/seed.py`：读取 `backend/seeds/faq_bilingual.yaml` 作为双语 FAQ 数据源，幂等写入 `default` 租户、默认坐席（`.env` 可覆盖）、`widget` 与 `webhook` 两个 channel（生成 token）、默认 `bot_config`、中/英双语泛例 FAQ 知识条目并触发向量索引（SC-001）
- [X] T023a [P] 编写 `backend/seeds/faq_bilingual.yaml`：租户中立的通用泛例 FAQ（账号/密码/退款/配送/联系方式等），中英各 ≥ 15 条，字段含 `lang`/`title`/`content`/`meta`（spec 决策 11、12）
- [X] T024 编写 `backend/entrypoint.sh`：启动时依次执行 Alembic 迁移 → seed（幂等）→ uvicorn，并在 `docker-compose.yml` 中挂接
- [X] T025 [P] 搭建 `tests/conftest.py`：测试 DB/Redis/Qdrant fixture、租户上下文 fixture、httpx AsyncClient fixture

**检查点**：`docker compose up -d` 后所有服务 healthy，`GET /api/v1/health` 全绿，seed 数据可在 MySQL 中查到。

---

## Phase 3：User Story 1 — 用户提问获得 AI 流式回答（P1）

**故事目标**：widget 提中/英问题 → 混合检索 → 流式逐字回答，首字符 < 2s。
**独立验证**：seed FAQ 已在库，打开 `/widget` 问「怎么重置密码」与「how do I reset my password」，两次均检索命中并流式作答。
**覆盖**：FR-001、FR-002、FR-003、FR-015 / SC-002、SC-003

- [X] T026 [P] [US1] 实现 `backend/app/repositories/knowledge.py`：知识条目 CRUD + `vector_status` 流转（继承 T015 基类）
- [X] T027 [P] [US1] 实现 `backend/app/repositories/conversation.py`：创建/按 id 取/更新 `status`、`last_activity_at`、`assigned_agent_id`
- [X] T028 [P] [US1] 实现 `backend/app/repositories/message.py`：追加消息、按 `conversation_id` 时间序分页读取（`after_id` 增量）
- [X] T029 [P] [US1] 实现 `backend/app/repositories/contact.py`：按 `(channel_id, external_id)` upsert 联系人
- [X] T030 [US1] 实现 `backend/app/services/embedding.py`：调用网关生成 dense 向量 + 用 fastembed 生成 sparse 向量（research R-01）
- [X] T031 [US1] 实现 `backend/app/services/indexer.py`：知识条目 **同步** upsert/delete 到 Qdrant（point id = `knowledge_item_id`，payload 带 `tenant_id`），并回写 `vector_status`（`pending→indexed`，失败置 `stale`）。demo 规模不引入消息队列（修复 C6）
- [X] T032 [US1] 实现 `backend/app/services/retrieval.py`：Qdrant Query API 单请求内 dense + sparse 双路 + 内置 RRF 融合，强制 `tenant_id` payload 过滤，返回 `top_k` 及最高相关分（FR-002，research R-01）
- [X] T033 [P] [US1] 实现 `backend/app/domain/prompt.py`：system prompt 护栏模板（「仅依据检索到的知识作答，无依据时输出 `need_human=true`」）+ 结构化输出 schema（FR-003）
- [X] T034 [US1] 实现 `backend/app/engine/state.py`：LangGraph state 定义（`tenant_id`/`conversation_id`/`user_text`/`history`/`retrieval`/`decision`/`answer`）
- [X] T035 [US1] 实现 `backend/app/engine/nodes/retrieve.py`：调用 T032 填充 state 的检索结果
- [X] T036 [US1] 实现 `backend/app/engine/nodes/generate.py`：基于检索依据 + 历史流式生成回答（走 T019 网关）
- [X] T037 [US1] 实现 `backend/app/engine/graph.py`：装配线性图 `ingest → retrieve → generate`（噪音/评级分支在 US2 接线，节点位先留），编译为可复用 graph 实例
- [X] T038 [US1] 实现 `backend/app/services/chat_service.py`：从 MySQL 读会话历史注入 state、调用 `graph.astream_events(v2)` 捕获 `on_chat_model_stream` 逐块产出、生成结束后落库 `message(source=ai)`（research R-03，**不使用 checkpointer**）
- [X] T039 [US1] 实现 `backend/app/realtime/ws_manager.py`：进程内 `conversation_id → {WebSocket}` 注册/注销与本地扇出（research R-04）
- [X] T040 [US1] 实现 `backend/app/api/ws_widget.py`：`/ws/widget` 端点，按 contracts/websocket.md 实现握手（`channel_token` 反查租户）、入站 `user_message`/`resume`/`ping`、出站 `conversation`/`history`/`ai_token`/`ai_done`/`error`（FR-001、FR-015）。入站 `request_human` 在 US2 的 T044a 接线
- [X] T041 [US1] 实现 `frontend/widget/src/ws-client.ts`：WS 连接、重连退避、消息信封收发
- [X] T042 [US1] 实现 `frontend/widget/src/app.ts` 与 `index.html`：输入框、消息列表、`ai_token` 增量拼接渲染（流式可见）、`conversation_id` 存 localStorage 供刷新恢复
- [X] T043 [US1] 编写 `tests/integration/test_us1_rag_stream.py`：seed FAQ → WS 发中/英问题 → 断言收到 `ai_token` 序列且首块延迟 < 2s、`ai_done` 内容命中知识条目（SC-003）
- [X] T043a [US1] 建立 `tests/eval/dataset_zh.yaml` 与 `tests/eval/dataset_en.yaml`：中/英各 ≥ 20 条评测问题，每条标注期望命中的 `knowledge_item` 标识与是否应转人工（覆盖同义改写、口语化、错别字、知识库外问题）
- [X] T043b [US1] 编写 `tests/eval/run_eval.py` 与 `tests/eval/test_retrieval_accuracy.py`：批量跑评测集，统计「正确检索 + 正确作答」比例与转人工准确率，输出报告并在比例 < 90% 时断言失败（SC-002 门禁，直面「未验证即上线」教训）

**检查点**：US1 可独立演示——widget 中/英问答均流式作答。

---

## Phase 4：User Story 2 — 答不出触发转人工并由坐席接管（P1）

**故事目标**：噪音短路、低置信转人工、坐席接管并双向实时对话、AI↔人工切换。
**独立验证**：问知识库覆盖不到的问题 → widget 显示转接提示；坐席登录接管并回复 → 用户侧 < 2s 收到并标注「人工」。
**覆盖**：FR-004、FR-005、FR-006、FR-007、FR-012 / SC-004、SC-005
**依赖**：Phase 3（复用会话/消息仓储与 ws_manager）

- [X] T044 [US2] 实现 `backend/app/domain/routing.py::classify_noise(text) -> bool`：**纯函数**规则集（空/超短 <2 有效字符、纯标点符号、纯 emoji、中英问候语白名单）（FR-012，research R-09）
- [X] T044a [US2] 在 `backend/app/api/ws_widget.py` 接线入站 `request_human` 事件：直接调用 `handoff_service` 转 `pending_human`，不经检索/LLM；同时在 `backend/app/domain/routing.py` 实现 `detect_human_intent(text) -> bool`（中英「转人工/人工客服/talk to a human/speak to an agent」等模式），作为 `should_escalate` 的 `user_intent` 信号（FR-004，spec US2 验收场景 2）
- [X] T045 [US2] 在 `backend/app/domain/routing.py` 增加 `should_escalate(retrieval, llm_signal, user_intent) -> EscalateReason | None`：**纯函数**三信号取或（检索最高分 < `bot_config.retrieval_threshold` / LLM `need_human=true` / 用户显式转人工意图）（FR-004，research R-02）
- [X] T046 [P] [US2] 实现 `backend/app/domain/entities.py`（dataclass 领域实体：`Conversation`/`Message`/`RetrievalResult`/`EscalateReason`，纯 Python 无 ORM 依赖）与 `backend/app/domain/conversation.py::transition(current, event) -> next`：会话状态机纯函数，非法转移抛领域错误；不变量「`human`/`pending_human` 时 AI 不得应答」（data-model.md 状态机，修复 C9）
- [X] T047 [P] [US2] 编写 `tests/unit/test_domain_routing.py` 与 `tests/unit/test_domain_conversation.py`：覆盖噪音判别、三种升级信号、全部合法/非法状态转移（SC-004 可复现基础）
- [X] T048 [US2] 实现 `backend/app/engine/nodes/noise_filter.py`：命中 `classify_noise` 则短路返回固定引导话术，**不进检索/LLM**
- [X] T049 [US2] 实现 `backend/app/engine/nodes/grade.py`：调用 `should_escalate` 决策，输出 `escalate` 或 `generate` 分支信号；`tool` 分支占位存在但不接线（FR-016）
- [X] T050 [US2] 更新 `backend/app/engine/graph.py`：接线为 `ingest → noise_filter →(命中)canned_reply | retrieve → grade →(escalate)handoff | generate`（research R-03）。**不设独立 `rerank` 节点**——RRF 融合属 T032 检索服务内部实现细节；可选 cross-encoder 重排作为 `retrieval.py` 内默认关闭的开关（修复 C5）
- [X] T051 [US2] 实现 `backend/app/services/handoff_service.py`：转 `pending_human`、落 `system` 提示消息、推送 `handoff` 事件（notice=「正在为您转接人工，请稍候」）、无坐席在线时保持排队不自动关闭（澄清 Q5）
- [X] T052 [US2] 实现 `backend/app/realtime/pubsub.py`：Redis 频道 `rt:{tenant}:conv:{id}` 与 `rt:{tenant}:agents` 的 publish/subscribe（research R-04）
- [X] T053 [US2] 改造 `backend/app/realtime/ws_manager.py`：订阅 Redis 频道并向本地连接扇出，实现跨实例广播；坐席在线态写入**按租户分片**的 Redis SET `rt:{tenant}:agents:online`（修复 C7，与 FR-010 隔离主张对齐）
- [X] T054 [P] [US2] 实现 `backend/app/repositories/agent.py`：按 `(tenant_id, username)` 查坐席
- [X] T055 [US2] 实现 `backend/app/api/auth.py`：`POST /api/v1/auth/login` 校验口令并签发会话令牌，失败返回 401 `invalid_credentials`（contracts/rest-api.md）
- [X] T056 [US2] 实现 `backend/app/services/agent_service.py`：`claim`（前置状态校验 + 幂等，已被他人接管抛 `already_claimed`）、`reply`、`set_mode`、`close`，全部经 T046 状态机流转
- [X] T057 [US2] 实现 `backend/app/api/conversations.py` 的 `POST /{id}/claim`：→ `status=human`、`assigned_agent_id` 落定、AI 停答，冲突返回 409（FR-005）
- [X] T058 [US2] 在 `backend/app/api/conversations.py` 实现 `POST /{id}/reply`：落 `message(source=agent)` 并经 pubsub 推 `agent_message`，非归属坐席返回 403（FR-006、SC-005）
- [X] T059 [US2] 在 `backend/app/api/conversations.py` 实现 `POST /{id}/mode` 与 `POST /{id}/close`：AI↔人工切换即时生效并推 `mode_changed`（FR-007）
- [X] T060 [US2] 实现 `backend/app/api/ws_agent.py`：`/ws/agent` 端点，Bearer 令牌握手、`subscribe`/`unsubscribe`/`ping`（在线态刷新）
- [X] T061 [US2] 更新 `frontend/widget/src/app.ts`：渲染 `noise_reply`、`handoff` 转接提示、`agent_message`（标注来源「人工」）、`mode_changed`
- [X] T062 [US2] 实现 `frontend/agent-console/src/pages/Login.tsx` 与 `src/api/client.ts`：登录并持久化令牌，注入 `Authorization` 头
- [X] T063 [US2] 实现 `frontend/agent-console/src/pages/Inbox.tsx` 最小可用版：待接管会话 + 接管按钮 + 回复输入框 + AI/人工切换
- [X] T064 [US2] 编写 `tests/integration/test_us2_handoff.py`：不可答问题 100% 触发转人工、噪音短路不调用 LLM、坐席接管后 AI 停答、坐席回复 < 2s 到达用户侧（SC-004、SC-005）

**检查点**：**MVP 完成** —— US1+US2 构成 SC-008 可一次性录屏的完整链路。

---

## Phase 5：User Story 3 — 坐席工作台会话监看与切换（P2）

**故事目标**：多会话实时列表、状态与未读、完整历史查看。
**独立验证**：制造多个并发会话，工作台列表实时刷新、状态正确、点击可看全历史。
**覆盖**：FR-008 / 支撑 SC-008 演示完整度
**依赖**：Phase 4

- [X] T065 [P] [US3] 在 `backend/app/api/conversations.py` 实现 `GET /api/v1/conversations?status=&page=`：按 `(tenant_id, status, last_activity_at)` 索引排序返回列表与 `preview`
- [X] T066 [P] [US3] 在 `backend/app/api/conversations.py` 实现 `GET /api/v1/conversations/{id}/messages?after_id=`：时间序历史，每条带 `source` 标注
- [X] T067 [US3] 扩展 `backend/app/realtime/pubsub.py` 与 `ws_agent.py`：推送 `conversation_upserted`、`new_message`、`pending_count`（contracts/websocket.md）
- [X] T068 [US3] 实现 `frontend/agent-console/src/hooks/useAgentSocket.ts`：`/ws/agent` 连接、事件分发、断线重连
- [X] T069 [US3] 扩展 `frontend/agent-console/src/pages/Inbox.tsx`：会话列表按状态分组 + 未读徽标 + 待接管计数，随 WS 事件实时更新（无需刷新）
- [X] T070 [US3] 实现 `frontend/agent-console/src/pages/ConversationDetail.tsx`：完整消息历史（用户/AI/坐席/system 视觉区分）+ 接管/切换/结束操作区
- [ ] T071 [US3] 编写 `tests/integration/test_us3_console_realtime.py`：并发会话下列表实时增量与未读计数正确

---

## Phase 6：User Story 4 — 配置租户 / 知识库 / 接入渠道（P2）

**故事目标**：管理端维护三张配置，知识条目录入后可被检索命中。
**独立验证**：新增一条 FAQ → 1 分钟内 widget 提问命中；租户 A 数据在租户 B 上下文不可见。
**覆盖**：FR-009、FR-010 / SC-006、SC-007
**依赖**：Phase 3（indexer/retrieval）

- [X] T072 [P] [US4] 实现 `backend/app/api/kb.py`：知识条目 `GET/POST/PUT/DELETE /api/v1/kb/items`，写操作在请求内**同步**调用 T031 完成向量 upsert/删除（SC-006 要求 1 分钟内可命中，同步足够）
- [X] T073 [P] [US4] 实现 `backend/app/api/channels.py`：`GET/POST/PATCH /api/v1/channels`，创建时生成唯一 `token`
- [X] T074 [P] [US4] 实现 `backend/app/api/tenants.py`：`GET /api/v1/tenant` 当前租户信息；`POST /api/v1/tenants` 多租户创建**默认禁用**（受 `ENABLE_TENANT_PROVISIONING` 配置开关控制，默认 false，关闭时返回 403），避免越出本里程碑范围
- [X] T075 [P] [US4] 实现 `backend/app/api/bot_config.py`：`GET/PUT /api/v1/bot-config`（`model`/`system_prompt`/`retrieval_threshold`/`top_k`）
- [X] T076 [US4] 实现 `backend/app/workers/index_worker.py`：**周期性回填 worker**——扫描 `vector_status IN (pending, stale)` 的条目重建向量（覆盖 T031 同步失败与批量导入场景），在 compose `worker` 服务中按固定间隔运行；非在线写入路径的依赖（修复 C6）
- [ ] T077 [US4] 实现 `frontend/agent-console/src/pages/Admin/*`：知识条目列表/编辑、渠道管理、bot 配置三个最小表单页
- [ ] T078 [US4] 编写 `tests/integration/test_us4_tenant_isolation.py`：双租户数据交叉访问全部被阻断（含 REST、检索、WS 三条路径）（SC-007）
- [ ] T079 [US4] 编写 `tests/integration/test_us4_kb_freshness.py`：新增条目后 1 分钟内可被检索命中（SC-006）

---

## Phase 7：User Story 5 — 通用 Webhook 接入外部渠道（P3）

**故事目标**：外部渠道消息经同一引擎链路处理，非法投递不产生脏会话。
**独立验证**：curl POST 一条消息 → 创建会话并按 RAG/转人工处理；无效 token 返回 404 且库中无新会话。
**覆盖**：FR-011
**依赖**：Phase 4

- [X] T080 [US5] 实现 `backend/app/channels/base.py`：渠道适配器抽象接口（`normalize_inbound` / `deliver_outbound`）
- [X] T081 [US5] 实现 `backend/app/channels/webhook.py`：通用信封 `{external_user_id, text, lang?, metadata}` 归一化为内部消息
- [X] T082 [US5] 实现 `backend/app/api/webhook.py`：`POST /api/v1/channels/webhook/{token}`，token 反查租户与渠道，创建/续接 contact 与 conversation，交同一引擎处理，返回 202
- [X] T083 [US5] 在 `backend/app/api/webhook.py` 补齐校验与错误：404 `channel_not_found`、400 `invalid_payload`，**校验失败先于任何写库**以保证不产生脏会话（FR-011）
- [X] T084 [P] [US5] 创建 `backend/app/channels/{feishu,whatsapp,telegram}.py` 适配器骨架：仅实现接口签名并抛 `NotImplementedError`（共识决策 9，仅骨架不接通）
- [ ] T085 [US5] 编写 `tests/integration/test_us5_webhook.py`：合法投递走通链路、非法 token/缺字段返回预期错误且零脏数据

---

## Phase 8：Polish & 横切关注点

- [X] T086 [P] 在 `backend/app/services/chat_service.py` 实现零命中/生成失败的统一降级：检索为空或知识库为空或网关异常 → 转人工或兜底话术，**绝不报错崩溃、绝不杜撰**（FR-013、SC-004）
- [X] T087 [P] 完善 `backend/app/api/ws_widget.py` 的 `resume` 语义：刷新/断线重连按 `conversation_id` 从 MySQL 回读全量历史并恢复上下文（FR-015）
- [X] T088 [P] 在 `backend/app/engine/nodes/tool.py` 落地 tool 节点占位：读取 `tool` 表 schema 但不执行，附注释说明第二期接入点（FR-016）
- [ ] T089 [P] 在 `frontend/widget/src/app.ts` 处理流式期间用户继续发消息的排队策略（前一条 `ai_done` 前入队，不并发打断）（spec 边界情况）
- [ ] T089a [P] 明确多标签页/多设备并发会话归属：同一 `contact` 复用同一活跃会话（`status != closed` 时按 `contact_id` 取最近活跃会话），多端经 Redis 频道同时收到同一会话事件；在 `backend/app/services/chat_service.py` 与 `backend/app/api/ws_widget.py` 落地（修复 C8，spec 边界情况）
- [ ] T090 [P] 处理超长输入与超出模型上下文：`chat_service` 截断历史 + 单条输入长度上限并给出友好提示（spec 边界情况）
- [ ] T091 [P] 全链路接入 `trace_id`：REST/WS 入口生成并透传至日志与 LLM 调用记录（T010）
- [X] T092 编写 `tests/e2e/test_full_demo_flow.py`：串起 quickstart.md 第 1→6 步（流式问答 → 噪音短路 → 转人工 → 接管回复 → 切回 AI → 刷新恢复），验证可一次性连续跑通（SC-008）
- [X] T093 编写 `scripts/smoke.sh`：health、webhook 投递、坐席登录三条冒烟命令（quickstart.md「冒烟命令」）
- [X] T094 [P] 编写 `README.md`：定位、架构图、一键起步骤、验收脚本、二次开发指引（开源可用性，SC-001）
- [X] T095 [P] 校准 `docker-compose.yml` healthcheck 与启动顺序，确保 `docker compose up -d` 后无需人工干预即可完成迁移+seed 并可用（FR-014、SC-001）
- [X] T096 [P] 补 `.github/workflows/ci.yml`：ruff lint + pytest（单元 + 集成）
- [ ] T097 复核全部 FR/SC 覆盖，更新 `specs/001-ai-cs-agent-web-demo/checklists/requirements.md` 勾选实现态

---

## 依赖关系图

```
Phase 1 Setup (T001-T008)
        ↓
Phase 2 Foundational (T009-T025)   ← 阻塞所有故事
        ↓
   ┌────┴─────────────────────────────┐
   ↓                                  ↓
Phase 3 US1 (T026-T043) ──────┐   Phase 6 US4 (T072-T079)
   ↓                          │   （依赖 T031/T032 索引与检索）
Phase 4 US2 (T044-T064)  ← MVP 终点
   ↓                    ↘
Phase 5 US3 (T065-T071)  Phase 7 US5 (T080-T085)
   ↓                    ↙
Phase 8 Polish (T086-T097)
```

**故事间独立性**：

- **US1** 完成后即可独立演示流式问答（无需 US2+）。
- **US2** 依赖 US1 的会话/消息仓储与 ws_manager，但其领域判据（T044-T047）可与 US1 并行开发。
- **US3** 是 US2 工作台的增强，US2 已含最小接管闭环。
- **US4** 只依赖 Phase 2 + US1 的索引/检索链路，可与 US2 并行。
- **US5** 依赖 US2 的完整引擎分支（噪音/转人工），最后接。

---

## 并行执行建议

**Phase 2 内可并行**：T010、T016、T017、T018、T019、T022、T025（不同文件、仅依赖 T009 配置）

**Phase 3 内可并行**：
- 第一批：T026、T027、T028、T029（四个仓储文件互不相干）
- 第二批：T033 可与 T030/T031/T032 服务链并行

**Phase 4 内可并行**：T046、T047、T054 与 T044/T045 并行（T044/T045 同文件需串行）

**Phase 6 内可并行**：T072、T073、T074、T075（四个独立 API 文件）

**跨故事并行**（团队 ≥2 人时）：Phase 2 完成后，一路做 US1→US2 主链，另一路做 US4 配置与管理端。

---

## 实施策略

### MVP 范围（建议第一个可交付）

**Phase 1 + Phase 2 + Phase 3 (US1) + Phase 4 (US2)** = T001-T064。

这一范围即满足 spec 的核心验收标准 SC-008「完整演示链路可一次性连续录屏」，是**本里程碑的最小可演示产品**。US3/US4/US5 均为增强。

### 增量交付顺序

1. **里程碑 A（MVP）**：T001-T064 → 录屏 quickstart 第 1→6 步
2. **里程碑 B**：+ Phase 5 (US3) → 坐席工作台可日常使用
3. **里程碑 C**：+ Phase 6 (US4) → 管理端自助配置，脱离 seed 脚本
4. **里程碑 D**：+ Phase 7 (US5) + Phase 8 → 渠道可扩展性验证 + 开源发布就绪

---

## 任务统计

| 阶段 | 任务数 | 任务区间 | 覆盖需求 |
|---|---|---|---|
| Phase 1 Setup | 8 | T001-T008 | FR-014 |
| Phase 2 Foundational | 18 | T009-T025（含 T023a） | FR-010 |
| Phase 3 US1 (P1) | 20 | T026-T043b | FR-001/002/003/015、SC-002/003 |
| Phase 4 US2 (P1) | 22 | T044-T064（含 T044a） | FR-004/005/006/007/012、SC-004/005 |
| Phase 5 US3 (P2) | 7 | T065-T071 | FR-008 |
| Phase 6 US4 (P2) | 8 | T072-T079 | FR-009/010、SC-006/007 |
| Phase 7 US5 (P3) | 6 | T080-T085 | FR-011 |
| Phase 8 Polish | 13 | T086-T097（含 T089a） | FR-013/016、SC-001/008 |
| **合计** | **102** | T001-T097 + 5 项补丁任务 | FR-001～016 全覆盖、SC-001～008 全覆盖 |

> 2026-07-29 analyze 后补丁：T023a（双语 FAQ 种子文件）、T043a/T043b（SC-002 评测集与 ≥90% 门禁）、T044a（`request_human` 入站接线）、T089a（多端会话归属）。

### 需求覆盖校验

| 需求 | 承载任务 |
|---|---|
| FR-001 | T038、T040、T042 |
| FR-002 | T032 |
| FR-003 | T033、T036 |
| FR-004 | T044a、T045、T049、T051 |
| FR-005 | T056、T057 |
| FR-006 | T058、T061 |
| FR-007 | T059 |
| FR-008 | T065、T066、T069、T070 |
| FR-009 | T072、T073、T074、T075、T077 |
| FR-010 | T014、T015、T078 |
| FR-011 | T082、T083 |
| FR-012 | T044、T048 |
| FR-013 | T086 |
| FR-014 | T005、T024、T095 |
| FR-015 | T040、T087 |
| FR-016 | T049、T088 |
| SC-001 | T023、T023a、T094、T095 |
| SC-002 | T043a、T043b |
| SC-003 | T038、T043 |
| SC-004 | T047、T064、T086 |
| SC-005 | T058、T064 |
| SC-006 | T076、T079 |
| SC-007 | T015、T078 |
| SC-008 | T092 |
