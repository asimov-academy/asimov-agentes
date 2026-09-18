import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.clientes.modelos import Cliente


async def criar(sessao: AsyncSession, nome: str, slug: str) -> Cliente:
    cliente = Cliente(nome=nome, slug=slug)
    sessao.add(cliente)
    await sessao.flush()
    return cliente


async def obter(sessao: AsyncSession, cliente_id: uuid.UUID) -> Cliente | None:
    return await sessao.scalar(
        select(Cliente).where(Cliente.id == cliente_id, Cliente.removido_em.is_(None))
    )


async def por_slug(sessao: AsyncSession, slug: str) -> Cliente | None:
    """Pelo slug, que é o que aparece na URL da página pública de privacidade."""
    return await sessao.scalar(
        select(Cliente).where(Cliente.slug == slug, Cliente.removido_em.is_(None))
    )


async def slug_existe(sessao: AsyncSession, slug: str) -> bool:
    return await sessao.scalar(select(Cliente.id).where(Cliente.slug == slug)) is not None


async def listar(sessao: AsyncSession) -> list[Cliente]:
    """Visão do operador: ele administra todos os clientes da instalação."""
    resultado = await sessao.scalars(
        select(Cliente).where(Cliente.removido_em.is_(None)).order_by(Cliente.nome)
    )
    return list(resultado)
