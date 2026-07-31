"""渠道适配器抽象（T080）：inbound 归一化 / outbound 投递。"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class InboundMessage:
    external_user_id: str
    text: str
    lang: str | None = None
    metadata: dict | None = None


class ChannelAdapter(ABC):
    @abstractmethod
    def normalize_inbound(self, payload: dict) -> InboundMessage:
        ...

    @abstractmethod
    async def deliver_outbound(self, external_user_id: str, content: str) -> None:
        ...
