"""领域纯函数：噪音识别 / 用户转人工意图 / 转人工判据。零框架依赖，可单测（T044/T044a/T045）。"""
from __future__ import annotations

import re
from enum import Enum

# 问候语白名单（多语，去标点后精确匹配）
_GREETINGS = {
    "hi", "hii", "hello", "helo", "hey", "hiya", "yo", "heya",
    "你好", "您好", "在吗", "在么", "在不在", "有人吗", "有人在吗", "哈喽", "嗨", "你好呀",
    "مرحبا", "salam",
}

_EMOJI_RE = re.compile(
    "[\U0001F000-\U0001FAFF\U00002600-\U000027BF←-⇿⌀-⏿️‍]+"
)

# 有效字符：数字/拉丁/CJK/阿拉伯
_MEANINGFUL_RE = re.compile(r"[0-9A-Za-z一-鿿؀-ۿ]")

_HUMAN_INTENT_RE = re.compile(
    "|".join(
        [
            r"转人工", r"转\s*人工", r"人工客服", r"人工服务", r"要人工", r"找人工", r"真人",
            r"talk to (a |an )?(human|person|agent|representative)",
            r"speak (to|with) (a |an )?(human|person|agent|representative)",
            r"(real|live) (person|agent)", r"customer service (rep|agent|representative)",
        ]
    ),
    re.IGNORECASE,
)


def _strip(text: str) -> str:
    return (text or "").strip()


def classify_noise(text: str) -> bool:
    """是否为噪音消息（超短/纯符号/纯表情/问候语）。命中则不进检索/LLM（FR-012）。"""
    t = _strip(text)
    if len(t) < 2:
        return True
    if _EMOJI_RE.fullmatch(t):
        return True
    if not _MEANINGFUL_RE.search(t):
        return True
    normalized = re.sub(r"[\s\.,!?！？。，、~～·]+", "", t).lower()
    if normalized in _GREETINGS:
        return True
    return False


def detect_human_intent(text: str) -> bool:
    """用户是否显式请求人工（FR-004 的 user_intent 信号）。"""
    return bool(_HUMAN_INTENT_RE.search(_strip(text)))


class EscalateReason(str, Enum):
    user_requested = "user_requested"
    model_need_human = "model_need_human"
    low_confidence = "low_confidence"


def should_escalate(
    top_score: float,
    threshold: float,
    llm_need_human: bool,
    user_intent: bool,
) -> EscalateReason | None:
    """混合信号取或（research R-02）：任一命中即转人工，优先级 用户 > 模型 > 检索分。"""
    if user_intent:
        return EscalateReason.user_requested
    if llm_need_human:
        return EscalateReason.model_need_human
    if top_score < threshold:
        return EscalateReason.low_confidence
    return None
