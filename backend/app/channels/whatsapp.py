"""WhatsApp 渠道适配器骨架（共识决策 9，仅骨架不接通，T084）。"""
from app.channels.base import ChannelAdapter, InboundMessage


class WhatsAppAdapter(ChannelAdapter):
    def normalize_inbound(self, payload: dict) -> InboundMessage:  # pragma: no cover
        raise NotImplementedError("whatsapp adapter is a skeleton (on-demand)")

    async def deliver_outbound(self, external_user_id: str, content: str) -> None:  # pragma: no cover
        raise NotImplementedError("whatsapp adapter is a skeleton (on-demand)")
