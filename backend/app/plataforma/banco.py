import uuid
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from functools import lru_cache

from sqlalchemy import DateTime, MetaData
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from app.plataforma.config import config

NOMES = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


def agora() -> datetime:
    return datetime.now(UTC)


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NOMES)


class ComId:
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)


class ComCriacao:
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=agora)


@lru_cache
def motor() -> AsyncEngine:
    return create_async_engine(config().database_url, pool_pre_ping=True)


@lru_cache
def fabrica_sessao() -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(motor(), expire_on_commit=False)


async def sessao() -> AsyncIterator[AsyncSession]:
    """Dependência do FastAPI: uma sessão por requisição."""
    async with fabrica_sessao()() as s:
        yield s
