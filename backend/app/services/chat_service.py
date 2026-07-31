"""应用服务：入站用户消息 → LangGraph 运行 → 落库/决策（T038 + US2 决策路由）。

返回结构化决策，由 ws_widget 据此发对应 envelope：
  {"kind": "noise", "content": str}
  {"kind": "escalate", "reason": str}
  {"kind": "ai", "message_id": int, "content": str}

持久化显式落 MySQL（事实源）；不使用 LangGraph checkpointer（research R-03）。
零命中/生成失败稳定降级（FR-013）：answer 为空时回兜底话术并转人工语义。
"""
from collections.abc import Awaitable, Callable

from sqlalchemy import select

from app.core.tenant import current_tenant_id
from app.db.base import async_session_factory
from app.db.models import BotConfig, MessageSource
from app.domain.prompt import FALLBACK_REPLY, NOISE_REPLY
from app.engine.graph import graph
from app.repositories.conversation import ConversationRepository
from app.repositories.message import MessageRepository

TokenSink = Callable[[str], Awaitable[None]]


async def _load_history(session, conversation_id: int) -> list[dict]:
    msgs = await MessageRepository(session).history(conversation_id)
    return [{"source": m.source.value, "content": m.content} for m in msgs]


async def _load_bot(session) -> dict:
    row = (
        await session.execute(
            select(BotConfig).where(BotConfig.tenant_id == current_tenant_id())
        )
    ).scalar_one_or_none()
    if not row:
        return {}
    return {
        "model": row.model,
        "top_k": row.top_k,
        "system_prompt": row.system_prompt,
        "retrieval_threshold": row.retrieval_threshold,
    }


async def run_turn(
    conversation_id: int, user_text: str, lang: str, on_token: TokenSink
) -> dict:
    async with async_session_factory() as session:
        history = await _load_history(session, conversation_id)
        bot = await _load_bot(session)

    state = {
        "conversation_id": conversation_id,
        "user_text": user_text,
        "lang": lang,
        "history": history,
        "bot": bot,
    }

    root_run_id = None
    final: dict = {}
    tokens: list[str] = []
    try:
        async for event in graph.astream_events(state, version="v2"):
            et = event["event"]
            if et == "on_chain_start" and root_run_id is None:
                root_run_id = event["run_id"]
            elif et == "on_chat_model_stream":
                chunk = event["data"]["chunk"]
                token = getattr(chunk, "content", "") or ""
                if token:
                    tokens.append(token)
                    await on_token(token)
            elif et == "on_chain_end" and event.get("run_id") == root_run_id:
                final = event["data"].get("output") or {}
    except Exception:  # noqa: BLE001 - 生成链路异常统一降级为转人工（FR-013）
        return {"kind": "escalate", "reason": "generation_error"}

    if final.get("noise"):
        content = final.get("answer") or NOISE_REPLY
        async with async_session_factory() as session:
            await MessageRepository(session).append(
                conversation_id, MessageSource.system, content, lang=lang, meta={"noise": True}
            )
            await ConversationRepository(session).touch(conversation_id)
            await session.commit()
        return {"kind": "noise", "content": content}

    if final.get("escalate_reason"):
        return {"kind": "escalate", "reason": final["escalate_reason"]}

    answer = (final.get("answer") or "".join(tokens)).strip()
    if not answer:
        # 生成为空视作无法作答 → 转人工，绝不杜撰（FR-013/SC-004）
        return {"kind": "escalate", "reason": "empty_answer", "fallback": FALLBACK_REPLY}

    async with async_session_factory() as session:
        msg = await MessageRepository(session).append(
            conversation_id, MessageSource.ai, answer, lang=lang
        )
        await ConversationRepository(session).touch(conversation_id)
        await session.commit()
        return {"kind": "ai", "message_id": msg.id, "content": answer}
