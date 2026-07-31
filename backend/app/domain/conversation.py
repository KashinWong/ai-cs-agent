"""会话状态机纯函数（data-model.md）。非法转移抛 InvalidTransition，可单测（T046）。

枚举取值与 db.models.ConversationStatus 一致，但本模块保持零 ORM 依赖。
"""
from __future__ import annotations

from enum import Enum


class ConvStatus(str, Enum):
    ai = "ai"
    pending_human = "pending_human"
    human = "human"
    closed = "closed"


class ConvEvent(str, Enum):
    escalate = "escalate"          # 判据命中 / 用户要人工
    claim = "claim"                # 坐席接管
    switch_to_ai = "switch_to_ai"  # 坐席切回 AI
    close = "close"                # 结束会话


class InvalidTransition(Exception):
    pass


_TABLE: dict[tuple[ConvStatus, ConvEvent], ConvStatus] = {
    (ConvStatus.ai, ConvEvent.escalate): ConvStatus.pending_human,
    (ConvStatus.ai, ConvEvent.claim): ConvStatus.human,          # 坐席主动接管 AI 会话
    (ConvStatus.ai, ConvEvent.close): ConvStatus.closed,
    (ConvStatus.pending_human, ConvEvent.claim): ConvStatus.human,
    (ConvStatus.pending_human, ConvEvent.close): ConvStatus.closed,
    (ConvStatus.human, ConvEvent.switch_to_ai): ConvStatus.ai,
    (ConvStatus.human, ConvEvent.close): ConvStatus.closed,
}


def transition(current: ConvStatus, event: ConvEvent) -> ConvStatus:
    key = (current, event)
    if key not in _TABLE:
        raise InvalidTransition(f"cannot apply {event.value} from {current.value}")
    return _TABLE[key]


def ai_may_answer(status: ConvStatus) -> bool:
    """不变量：仅 ai 态允许引擎自动应答；human/pending_human 时 AI 不得抢答（FR-005）。"""
    return status == ConvStatus.ai
