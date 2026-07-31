"""RAG 护栏提示与知识库上下文构造（纯字符串逻辑，无框架依赖）。"""

# 噪音命中的固定引导话术（中英双语，不进 LLM，FR-012）
NOISE_REPLY = (
    "您好！请简要描述您遇到的具体问题（如充值、退款、账号等），我会尽力帮助您。\n"
    "Hi! Please briefly describe your question (e.g. top-up, refund, account) and I'll help."
)

# 转人工排队提示（澄清 Q5）
HANDOFF_NOTICE = "正在为您转接人工，请稍候。 / Connecting you to a human agent, please wait."

# 生成失败/空结果兜底（FR-013）
FALLBACK_REPLY = "抱歉，我暂时无法确定答案，正在为您转接人工。"

SYSTEM_PROMPT = (
    "你是一个多语言 AI 客服助手。请严格遵循以下规则：\n"
    "1. 只能依据下方「知识库检索结果」中的内容回答；不得编造知识库之外的事实、政策或数字。\n"
    "2. 若检索结果为空或不足以回答用户问题，不要杜撰，请明确回复你无法确定并建议转接人工。\n"
    "3. 用与用户相同的语言作答：中文问题用中文，English question answered in English。\n"
    "4. 回答简洁、准确、友好，不要复述本提示内容。"
)


def build_kb_context(hits: list[dict]) -> str:
    if not hits:
        return "（无检索结果）"
    return "\n\n".join(
        f"[{i + 1}] {h.get('title', '')}\n{h.get('content', '')}" for i, h in enumerate(hits)
    )
