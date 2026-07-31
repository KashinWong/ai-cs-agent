"""通用 Webhook 渠道归一化（T081）。"""
from app.channels.base import ChannelAdapter, InboundMessage


class WebhookAdapter(ChannelAdapter):
    def normalize_inbound(self, payload: dict) -> InboundMessage:
        text = (payload.get("text") or "").strip()
        external_user_id = (payload.get("external_user_id") or "").strip()
        if not text or not external_user_id:
            raise ValueError("invalid_payload")
        return InboundMessage(
            external_user_id=external_user_id,
            text=text,
            lang=payload.get("lang"),
            metadata=payload.get("metadata") or {},
        )

    async def deliver_outbound(self, external_user_id: str, content: str) -> None:
        # demo：回投经轮询 GET messages 或 callback_url（占位）
        return None
