from app.domain.routing import (
    EscalateReason,
    classify_noise,
    detect_human_intent,
    should_escalate,
)


class TestClassifyNoise:
    def test_greeting_zh(self):
        assert classify_noise("你好")
        assert classify_noise("在吗？")
        assert classify_noise("哈喽~")

    def test_greeting_en(self):
        assert classify_noise("hi")
        assert classify_noise("Hello!")

    def test_single_symbol_or_short(self):
        assert classify_noise("?")
        assert classify_noise("。")
        assert classify_noise("  ")
        assert classify_noise("")

    def test_pure_emoji(self):
        assert classify_noise("😀")
        assert classify_noise("👍👍")

    def test_real_question_not_noise(self):
        assert not classify_noise("怎么重置密码")
        assert not classify_noise("how do I reset my password")
        assert not classify_noise("充值没到账")


class TestHumanIntent:
    def test_zh(self):
        assert detect_human_intent("我要转人工")
        assert detect_human_intent("帮我转人工客服")

    def test_en(self):
        assert detect_human_intent("I want to talk to a human")
        assert detect_human_intent("speak with an agent please")

    def test_negative(self):
        assert not detect_human_intent("怎么重置密码")
        assert not detect_human_intent("how much is a refund")


class TestShouldEscalate:
    def test_user_requested_highest_priority(self):
        assert should_escalate(0.9, 0.35, False, True) == EscalateReason.user_requested

    def test_model_need_human(self):
        assert should_escalate(0.9, 0.35, True, False) == EscalateReason.model_need_human

    def test_low_confidence(self):
        assert should_escalate(0.1, 0.35, False, False) == EscalateReason.low_confidence

    def test_no_escalate(self):
        assert should_escalate(0.9, 0.35, False, False) is None
