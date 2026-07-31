"""initial schema

Revision ID: 0001_initial
Revises:
Create Date: 2026-07-29
"""
from alembic import op
import sqlalchemy as sa

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None

_channel_type = sa.Enum("widget", "webhook", "feishu", "whatsapp", "telegram", name="channeltype")
_vector_status = sa.Enum("pending", "indexed", "stale", name="vectorstatus")
_conv_status = sa.Enum("ai", "pending_human", "human", "closed", name="conversationstatus")
_msg_source = sa.Enum("user", "ai", "agent", "system", name="messagesource")


def upgrade():
    op.create_table(
        "tenant",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("slug", sa.String(64), nullable=False, unique=True),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_table(
        "channel",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("tenant_id", sa.BigInteger(), nullable=False, index=True),
        sa.Column("type", _channel_type, nullable=False),
        sa.Column("token", sa.String(64), nullable=False, unique=True),
        sa.Column("config_json", sa.JSON()),
        sa.Column("enabled", sa.Boolean(), server_default=sa.true()),
    )
    op.create_table(
        "knowledge_item",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("tenant_id", sa.BigInteger(), nullable=False, index=True),
        sa.Column("kb_id", sa.BigInteger(), server_default="1"),
        sa.Column("lang", sa.String(8)),
        sa.Column("title", sa.String(256), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("meta_json", sa.JSON()),
        sa.Column("vector_status", _vector_status, server_default="pending"),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_table(
        "bot_config",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("tenant_id", sa.BigInteger(), nullable=False, index=True),
        sa.Column("model", sa.String(64), nullable=False),
        sa.Column("system_prompt", sa.Text(), nullable=False),
        sa.Column("retrieval_threshold", sa.Float(), server_default="0.35"),
        sa.Column("top_k", sa.Integer(), server_default="5"),
        sa.Column("enabled", sa.Boolean(), server_default=sa.true()),
    )
    op.create_table(
        "agent",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("tenant_id", sa.BigInteger(), nullable=False, index=True),
        sa.Column("username", sa.String(64), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("display_name", sa.String(128), nullable=False),
    )
    op.create_index("ix_agent_tenant_username", "agent", ["tenant_id", "username"], unique=True)
    op.create_table(
        "contact",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("tenant_id", sa.BigInteger(), nullable=False, index=True),
        sa.Column("channel_id", sa.BigInteger(), nullable=False),
        sa.Column("external_id", sa.String(128), nullable=False),
        sa.Column("display_name", sa.String(128), nullable=True),
    )
    op.create_index(
        "ix_contact_channel_external", "contact", ["tenant_id", "channel_id", "external_id"], unique=True
    )
    op.create_table(
        "conversation",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("tenant_id", sa.BigInteger(), nullable=False, index=True),
        sa.Column("channel_id", sa.BigInteger(), nullable=False),
        sa.Column("contact_id", sa.BigInteger(), nullable=False),
        sa.Column("status", _conv_status, server_default="ai"),
        sa.Column("assigned_agent_id", sa.BigInteger(), nullable=True),
        sa.Column("lang", sa.String(8)),
        sa.Column("last_activity_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index(
        "ix_conv_tenant_status_activity", "conversation", ["tenant_id", "status", "last_activity_at"]
    )
    op.create_table(
        "message",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("tenant_id", sa.BigInteger(), nullable=False, index=True),
        sa.Column("conversation_id", sa.BigInteger(), nullable=False),
        sa.Column("source", _msg_source, nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("lang", sa.String(8)),
        sa.Column("meta_json", sa.JSON()),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index("ix_msg_conv_id", "message", ["conversation_id", "id"])
    op.create_table(
        "tool",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("tenant_id", sa.BigInteger(), nullable=False, index=True),
        sa.Column("name", sa.String(64), nullable=False),
        sa.Column("schema_json", sa.JSON()),
    )


def downgrade():
    for t in ["tool", "message", "conversation", "contact", "agent", "bot_config", "knowledge_item", "channel", "tenant"]:
        op.drop_table(t)
