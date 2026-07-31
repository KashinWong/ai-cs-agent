from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    DateTime,
    Enum,
    Float,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ChannelType(str, enum.Enum):
    widget = "widget"
    webhook = "webhook"
    feishu = "feishu"
    whatsapp = "whatsapp"
    telegram = "telegram"


class VectorStatus(str, enum.Enum):
    pending = "pending"
    indexed = "indexed"
    stale = "stale"


class ConversationStatus(str, enum.Enum):
    ai = "ai"
    pending_human = "pending_human"
    human = "human"
    closed = "closed"


class MessageSource(str, enum.Enum):
    user = "user"
    ai = "ai"
    agent = "agent"
    system = "system"


class Tenant(Base):
    __tablename__ = "tenant"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    slug: Mapped[str] = mapped_column(String(64), unique=True)
    name: Mapped[str] = mapped_column(String(128))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )


class Channel(Base):
    __tablename__ = "channel"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    tenant_id: Mapped[int] = mapped_column(BigInteger, index=True)
    type: Mapped[ChannelType] = mapped_column(Enum(ChannelType))
    token: Mapped[str] = mapped_column(String(64), unique=True)
    config_json: Mapped[dict] = mapped_column(JSON, default=dict)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)


class KnowledgeItem(Base):
    __tablename__ = "knowledge_item"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    tenant_id: Mapped[int] = mapped_column(BigInteger, index=True)
    kb_id: Mapped[int] = mapped_column(BigInteger, default=1)
    lang: Mapped[str] = mapped_column(String(8), default="zh")
    title: Mapped[str] = mapped_column(String(256))
    content: Mapped[str] = mapped_column(Text)
    meta_json: Mapped[dict] = mapped_column(JSON, default=dict)
    vector_status: Mapped[VectorStatus] = mapped_column(
        Enum(VectorStatus), default=VectorStatus.pending
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )


class BotConfig(Base):
    __tablename__ = "bot_config"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    tenant_id: Mapped[int] = mapped_column(BigInteger, index=True)
    model: Mapped[str] = mapped_column(String(64))
    system_prompt: Mapped[str] = mapped_column(Text)
    retrieval_threshold: Mapped[float] = mapped_column(Float, default=0.35)
    top_k: Mapped[int] = mapped_column(Integer, default=5)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)


class Agent(Base):
    __tablename__ = "agent"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    tenant_id: Mapped[int] = mapped_column(BigInteger, index=True)
    username: Mapped[str] = mapped_column(String(64))
    password_hash: Mapped[str] = mapped_column(String(255))
    display_name: Mapped[str] = mapped_column(String(128))
    __table_args__ = (Index("ix_agent_tenant_username", "tenant_id", "username", unique=True),)


class Contact(Base):
    __tablename__ = "contact"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    tenant_id: Mapped[int] = mapped_column(BigInteger, index=True)
    channel_id: Mapped[int] = mapped_column(BigInteger)
    external_id: Mapped[str] = mapped_column(String(128))
    display_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    __table_args__ = (
        Index("ix_contact_channel_external", "tenant_id", "channel_id", "external_id", unique=True),
    )


class Conversation(Base):
    __tablename__ = "conversation"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    tenant_id: Mapped[int] = mapped_column(BigInteger, index=True)
    channel_id: Mapped[int] = mapped_column(BigInteger)
    contact_id: Mapped[int] = mapped_column(BigInteger)
    status: Mapped[ConversationStatus] = mapped_column(
        Enum(ConversationStatus), default=ConversationStatus.ai
    )
    assigned_agent_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    lang: Mapped[str] = mapped_column(String(8), default="zh")
    last_activity_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    __table_args__ = (
        Index("ix_conv_tenant_status_activity", "tenant_id", "status", "last_activity_at"),
    )


class Message(Base):
    __tablename__ = "message"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    tenant_id: Mapped[int] = mapped_column(BigInteger, index=True)
    conversation_id: Mapped[int] = mapped_column(BigInteger)
    source: Mapped[MessageSource] = mapped_column(Enum(MessageSource))
    content: Mapped[str] = mapped_column(Text)
    lang: Mapped[str] = mapped_column(String(8), default="zh")
    meta_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    __table_args__ = (Index("ix_msg_conv_id", "conversation_id", "id"),)


class Tool(Base):
    __tablename__ = "tool"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    tenant_id: Mapped[int] = mapped_column(BigInteger, index=True)
    name: Mapped[str] = mapped_column(String(64))
    schema_json: Mapped[dict] = mapped_column(JSON, default=dict)
