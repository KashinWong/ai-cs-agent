# ai-cs-agent

独立部署、可开源的多租户 **AI 客服 Agent 平台**。当前里程碑：自包含 web demo，端到端跑通「用户提问 → 混合检索知识库 → AI 流式回答 → 转人工 → 坐席接管」。

设计与验收细节见 `specs/001-ai-cs-agent-web-demo/`（spec / plan / research / data-model / contracts / quickstart / tasks）。

## 一键起

```bash
cp .env.example .env    # 仅需填 LLM_GATEWAY_BASE_URL / LLM_GATEWAY_API_KEY
docker compose up -d
```

- Widget demo：http://localhost:8080/widget
- 坐席工作台：http://localhost:8080/console
- API：http://localhost:8000/api/v1

默认坐席（seed）：`agent / agent123`（可在 `.env` 覆盖）。

## 本地开发

```bash
uv sync                 # 安装后端依赖
uv run pytest tests/unit    # 领域纯函数单测
```

## 架构一览

- 后端：Python 3.11 / FastAPI（REST + WebSocket）
- 存储：MySQL（会话/消息持久事实源）、Redis（实时 Pub/Sub + 在线态）、Qdrant（混合检索 dense+sparse+RRF）
- 引擎：LangGraph 薄层编排，领域判据（噪音/转人工/状态机）为纯函数
- 前端：坐席工作台 React+TS+Vite；用户 widget 轻量可内嵌
