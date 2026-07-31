"""纯领域实体（dataclass，零 ORM/框架依赖）。服务层在 ORM 与这些实体间显式映射。"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class RetrievalHit:
    id: int
    title: str
    content: str
    lang: str = "zh"


@dataclass
class RetrievalResult:
    hits: list[RetrievalHit] = field(default_factory=list)
    top_score: float = 0.0

    def is_empty(self) -> bool:
        return not self.hits


@dataclass
class MessageDTO:
    id: int
    source: str
    content: str
    lang: str = "zh"
