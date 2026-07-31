"""评级节点（T049）：调用 domain.should_escalate 决策是否转人工。

demo 的 llm_need_human 信号在流式路径下暂置 False（generate 的护栏 prompt 已覆盖
"无依据不杜撰"）；检索分阈值 + 用户显式意图两路已满足 SC-004。tool 分支占位见 tool.py。
"""
from app.domain.routing import detect_human_intent, should_escalate
from app.engine.state import GraphState


async def grade_node(state: GraphState) -> dict:
    bot = state.get("bot", {})
    threshold = float(bot.get("retrieval_threshold") or 0.35)
    reason = should_escalate(
        top_score=float(state.get("top_score", 0.0)),
        threshold=threshold,
        llm_need_human=False,
        user_intent=detect_human_intent(state["user_text"]),
    )
    return {"escalate_reason": reason.value if reason else None}
