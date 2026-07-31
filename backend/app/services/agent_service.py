"""坐席会话操作（T056）：claim / reply / set_mode / close，全部经状态机流转。"""
from app.core.tenant import current_tenant_id
from app.db.base import async_session_factory
from app.db.models import ConversationStatus, MessageSource
from app.domain.conversation import ConvEvent, ConvStatus, transition
from app.realtime.ws_manager import envelope, ws_manager
from app.repositories.conversation import ConversationRepository
from app.repositories.message import MessageRepository


class NotFound(Exception):
    pass


class AlreadyClaimed(Exception):
    pass


class Forbidden(Exception):
    pass


async def claim(conversation_id: int, agent_id: int) -> None:
    tenant_id = current_tenant_id()
    async with async_session_factory() as session:
        crepo = ConversationRepository(session)
        conv = await crepo.get(conversation_id)
        if conv is None:
            raise NotFound()
        if (
            conv.status == ConversationStatus.human
            and conv.assigned_agent_id not in (None, agent_id)
        ):
            raise AlreadyClaimed()
        new = transition(ConvStatus(conv.status.value), ConvEvent.claim)
        await crepo.set_status(
            conversation_id, ConversationStatus(new.value), assigned_agent_id=agent_id
        )
        await session.commit()
    await ws_manager.broadcast(
        tenant_id, conversation_id, envelope("mode_changed", {"mode": "human"})
    )


async def reply(conversation_id: int, agent_id: int, content: str, lang: str = "zh") -> int:
    tenant_id = current_tenant_id()
    async with async_session_factory() as session:
        crepo = ConversationRepository(session)
        conv = await crepo.get(conversation_id)
        if conv is None:
            raise NotFound()
        if conv.status != ConversationStatus.human or conv.assigned_agent_id != agent_id:
            raise Forbidden()
        msg = await MessageRepository(session).append(
            conversation_id, MessageSource.agent, content, lang=lang
        )
        await crepo.touch(conversation_id)
        await session.commit()
        mid = msg.id
    await ws_manager.broadcast(
        tenant_id,
        conversation_id,
        envelope("agent_message", {"message_id": mid, "content": content, "source": "agent"}),
    )
    return mid


async def set_mode(conversation_id: int, agent_id: int, mode: str) -> None:
    tenant_id = current_tenant_id()
    async with async_session_factory() as session:
        crepo = ConversationRepository(session)
        conv = await crepo.get(conversation_id)
        if conv is None:
            raise NotFound()
        if mode == "ai":
            new = transition(ConvStatus(conv.status.value), ConvEvent.switch_to_ai)
            await crepo.set_status(
                conversation_id, ConversationStatus(new.value), assigned_agent_id=None
            )
        else:  # 切到人工=接管
            await claim(conversation_id, agent_id)
            return
        await session.commit()
    await ws_manager.broadcast(
        tenant_id, conversation_id, envelope("mode_changed", {"mode": mode})
    )


async def close(conversation_id: int, agent_id: int) -> None:
    async with async_session_factory() as session:
        crepo = ConversationRepository(session)
        conv = await crepo.get(conversation_id)
        if conv is None:
            raise NotFound()
        new = transition(ConvStatus(conv.status.value), ConvEvent.close)
        await crepo.set_status(conversation_id, ConversationStatus(new.value))
        await session.commit()
