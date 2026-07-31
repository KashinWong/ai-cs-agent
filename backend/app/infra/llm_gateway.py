import httpx
from langchain_openai import ChatOpenAI

from app.core.config import get_settings


def chat_model(*, streaming: bool = True, model: str | None = None) -> ChatOpenAI:
    settings = get_settings()
    return ChatOpenAI(
        base_url=settings.llm_gateway_base_url,
        api_key=settings.llm_gateway_api_key,
        model=model or settings.llm_chat_model,
        streaming=streaming,
        temperature=0.2,
    )


async def ping() -> bool:
    settings = get_settings()
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.get(
                f"{settings.llm_gateway_base_url.rstrip('/')}/models",
                headers={"Authorization": f"Bearer {settings.llm_gateway_api_key}"},
            )
            return resp.status_code < 500
    except Exception:
        return False
