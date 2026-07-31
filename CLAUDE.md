# ai-cs-agent — 项目上下文

> AI 客服 Agent 平台：独立部署、可开源的多租户 AI 客服 SaaS。
> 当前里程碑：自包含 web demo（端到端跑通 提问 → 检索 → 流式回答 → 转人工 → 坐席接管）。

## 关键文档

- 需求共识：`docs/00-设计共识.md`（13 项已锁定决策 + MVP 边界）
- 当前 feature：`specs/001-ai-cs-agent-web-demo/`

<!-- SPECKIT START -->
**Active Plan**: [specs/001-ai-cs-agent-web-demo/plan.md](specs/001-ai-cs-agent-web-demo/plan.md)

| 工件 | 路径 |
|---|---|
| Spec | `specs/001-ai-cs-agent-web-demo/spec.md` |
| Plan | `specs/001-ai-cs-agent-web-demo/plan.md` |
| Research (Phase 0) | `specs/001-ai-cs-agent-web-demo/research.md` |
| Data Model (Phase 1) | `specs/001-ai-cs-agent-web-demo/data-model.md` |
| REST 契约 | `specs/001-ai-cs-agent-web-demo/contracts/rest-api.md` |
| WebSocket 契约 | `specs/001-ai-cs-agent-web-demo/contracts/websocket.md` |
| Quickstart / 验收 | `specs/001-ai-cs-agent-web-demo/quickstart.md` |
| Tasks | `specs/001-ai-cs-agent-web-demo/tasks.md` |
| 规格质量清单 | `specs/001-ai-cs-agent-web-demo/checklists/requirements.md` |
<!-- SPECKIT END -->

## 技术栈（已锁定）

- **后端**：Python 3.11+ / uv / FastAPI（REST + WebSocket）
- **存储**：MySQL 8（会话与消息**持久事实源**）、Redis 7（实时 Pub/Sub + 在线态）、Qdrant（向量，混合检索 dense+sparse+RRF）
- **LLM**：OpenAI 兼容网关（new-api），chat 与 embedding 同源
- **编排**：LangGraph — **约束在 `backend/app/engine/` 薄层**，`domain/` 为纯 Python 无框架依赖，保留可替换性
- **前端**：坐席工作台 React+TS+Vite SPA；widget 极简可内嵌 bundle
- **部署**：docker-compose 一键起（mysql/redis/qdrant/api/worker/前端）

## 工程约束

- 所有业务表带 `tenant_id`；租户由中间件经 ContextVar 注入，仓储层**强制**追加过滤（严禁在 handler 手写租户条件）
- 领域判据（噪音识别、转人工判定、会话状态机）必须是**纯函数**，可单测、不依赖 LangGraph
- 检索零命中 / 生成失败必须稳定降级到转人工或兜底话术，**绝不杜撰、绝不报错崩溃**
- 反对投机性重构；不引入超出当前里程碑需要的框架
