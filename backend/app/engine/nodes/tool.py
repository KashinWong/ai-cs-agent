"""工具调用节点占位（FR-016，T088）。

第二期接入点：读取 tenant 的 tool 表 function schema 并执行 HTTP/OpenAPI/MCP 调用。
MVP 不接线——本节点不被 graph 装配进活动路径，仅保留结构占位与接口签名。
"""
from app.engine.state import GraphState


async def tool_node(state: GraphState) -> dict:  # pragma: no cover - 第二期
    raise NotImplementedError("tool execution is reserved for phase 2")
