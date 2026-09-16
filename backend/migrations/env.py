import asyncio

from alembic import context
from sqlalchemy.ext.asyncio import create_async_engine

from app.modelos import Base
from app.plataforma.config import config

alvo = Base.metadata


def _executa(conexao) -> None:  # type: ignore[no-untyped-def]
    context.configure(connection=conexao, target_metadata=alvo, compare_type=True)
    with context.begin_transaction():
        context.run_migrations()


async def _online() -> None:
    motor = create_async_engine(config().database_url)
    async with motor.connect() as conexao:
        await conexao.run_sync(_executa)
    await motor.dispose()


asyncio.run(_online())
