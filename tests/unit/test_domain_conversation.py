import pytest

from app.domain.conversation import (
    ConvEvent,
    ConvStatus,
    InvalidTransition,
    ai_may_answer,
    transition,
)


def test_ai_escalate_to_pending():
    assert transition(ConvStatus.ai, ConvEvent.escalate) == ConvStatus.pending_human


def test_pending_claim_to_human():
    assert transition(ConvStatus.pending_human, ConvEvent.claim) == ConvStatus.human


def test_ai_direct_claim_to_human():
    assert transition(ConvStatus.ai, ConvEvent.claim) == ConvStatus.human


def test_pending_auto_switch_back_to_ai():
    assert transition(ConvStatus.pending_human, ConvEvent.switch_to_ai) == ConvStatus.ai


def test_human_switch_back_to_ai():
    assert transition(ConvStatus.human, ConvEvent.switch_to_ai) == ConvStatus.ai


def test_human_close():
    assert transition(ConvStatus.human, ConvEvent.close) == ConvStatus.closed


@pytest.mark.parametrize(
    "current,event",
    [
        (ConvStatus.closed, ConvEvent.claim),
        (ConvStatus.closed, ConvEvent.escalate),
        (ConvStatus.ai, ConvEvent.switch_to_ai),
        (ConvStatus.pending_human, ConvEvent.escalate),
        (ConvStatus.human, ConvEvent.escalate),
    ],
)
def test_illegal_transitions_raise(current, event):
    with pytest.raises(InvalidTransition):
        transition(current, event)


def test_ai_may_answer_invariant():
    assert ai_may_answer(ConvStatus.ai)
    assert not ai_may_answer(ConvStatus.human)
    assert not ai_may_answer(ConvStatus.pending_human)
    assert not ai_may_answer(ConvStatus.closed)
