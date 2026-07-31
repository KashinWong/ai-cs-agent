from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.core.config import get_settings


class Base(DeclarativeBase):
    pass


_settings = get_settings()
engine = create_async_engine(
    _settings.mysql_dsn,
    pool_pre_ping=True,
    pool_recycle=1800,
    future=True,
)
async_session_factory = async_sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)
