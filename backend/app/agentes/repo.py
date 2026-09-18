import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agentes.modelos import Agente


async def criar(sessao: AsyncSession, agente: Agente) -> Agente:
    sessao.add(agente)
    await sessao.flush()
    return agente


async def obter(sessao: AsyncSession, cliente_id: uuid.UUID, agente_id: uuid.UUID) -> Agente | None:
    return await sessao.scalar(
        select(Agente).where(
            Agente.cliente_id == cliente_id,
            Agente.id == agente_id,
            Agente.removido_em.is_(None),
        )
    )


async def por_slug(sessao: AsyncSession, cliente_id: uuid.UUID, slug: str) -> Agente | None:
    """Pelo slug, dentro do cliente: é o que aparece na URL da página pública de privacidade."""
    return await sessao.scalar(
        select(Agente).where(
            Agente.cliente_id == cliente_id, Agente.slug == slug, Agente.ativo.is_(True)
        )
    )


async def slug_existe(sessao: AsyncSession, cliente_id: uuid.UUID, slug: str) -> bool:
    return (
        await sessao.scalar(
            select(Agente.id).where(Agente.cliente_id == cliente_id, Agente.slug == slug)
        )
        is not None
    )


async def listar(sessao: AsyncSession, cliente_id: uuid.UUID) -> list[Agente]:
    resultado = await sessao.scalars(
        select(Agente)
        .where(Agente.cliente_id == cliente_id, Agente.removido_em.is_(None))
        .order_by(Agente.nome)
    )
    return list(resultado)


async def listar_de_todos_os_clientes(sessao: AsyncSession) -> list[Agente]:
    """Só para o menu do operador, que administra a instalação inteira."""
    resultado = await sessao.scalars(
        select(Agente).where(Agente.removido_em.is_(None)).order_by(Agente.cliente_id, Agente.nome)
    )
    return list(resultado)


async def ativo_por_token(sessao: AsyncSession, token_hash: str) -> Agente | None:
    """Única busca sem cliente_id: é ela que descobre o cliente a partir da URL do webhook."""
    return await sessao.scalar(
        select(Agente).where(
            Agente.token_webhook_hash == token_hash,
            Agente.ativo.is_(True),
            Agente.removido_em.is_(None),
        )
    )
