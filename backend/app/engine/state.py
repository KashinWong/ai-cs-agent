from typing import Any, TypedDict


class GraphState(TypedDict, total=False):
    tenant_id: int
    conversation_id: int
    user_text: str
    lang: str
    history: list[dict[str, Any]]
    bot: dict[str, Any]
    hits: list[dict[str, Any]]
    top_score: float
    answer: str
    need_human: bool
    escalate_reason: str | None
    noise: bool
