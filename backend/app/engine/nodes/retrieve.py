from app.engine.state import GraphState
from app.services import retrieval


async def retrieve_node(state: GraphState) -> dict:
    top_k = int(state.get("bot", {}).get("top_k") or 5)
    res = await retrieval.hybrid_search(state["user_text"], top_k=top_k)
    return {"hits": res["hits"], "top_score": res["top_score"]}
