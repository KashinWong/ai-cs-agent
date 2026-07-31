"""噪音前置节点（T048）：命中即短路，answer 置固定话术，不进检索/LLM。"""
from app.domain.prompt import NOISE_REPLY
from app.domain.routing import classify_noise
from app.engine.state import GraphState


async def noise_filter_node(state: GraphState) -> dict:
    if classify_noise(state["user_text"]):
        return {"noise": True, "answer": NOISE_REPLY}
    return {"noise": False}
