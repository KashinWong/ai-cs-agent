from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from app.domain.prompt import SYSTEM_PROMPT, build_kb_context
from app.engine.state import GraphState
from app.infra.llm_gateway import chat_model


async def generate_node(state: GraphState) -> dict:
    hits = state.get("hits", [])
    system = state.get("bot", {}).get("system_prompt") or SYSTEM_PROMPT
    context = build_kb_context(hits)
    messages = [SystemMessage(content=f"{system}\n\n知识库检索结果:\n{context}")]
    for h in state.get("history", []):
        src = h.get("source")
        if src == "user":
            messages.append(HumanMessage(content=h["content"]))
        elif src in ("ai", "agent"):
            messages.append(AIMessage(content=h["content"]))
    messages.append(HumanMessage(content=state["user_text"]))

    model = chat_model(streaming=True, model=state.get("bot", {}).get("model"))
    resp = await model.ainvoke(messages)
    return {"answer": resp.content}
