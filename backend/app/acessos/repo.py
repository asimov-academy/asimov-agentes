"""Sem `cliente_id` de propósito: o acesso do operador ao canal é da instalação (ver modelos.py)."""

from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.acessos.modelos import AcessoCanal
from app.plataforma import cripto
from app.plataforma.banco import agora


async def obter(sessao: AsyncSession, canal: str, endereco: str) -> dict[str, Any] | None:
    cifrado = await sessao.scalar(
        select(AcessoCanal.acesso_cifrado).where(
            AcessoCanal.canal == canal, AcessoCanal.endereco == endereco
        )
    )
    return cripto.decifra(cifrado) if cifrado else None


async def guardar(sessao: AsyncSession, canal: str, endereco: str, acesso: dict[str, Any]) -> None:
    cifrado = cripto.cifra(acesso)
    await sessao.execute(
        insert(AcessoCanal)
        .values(canal=canal, endereco=endereco, acesso_cifrado=cifrado, criado_em=agora(), atualizado_em=agora())
        .on_conflict_do_update(
            index_elements=["canal", "endereco"],
            set_={"acesso_cifrado": cifrado, "atualizado_em": agora()},
        )
    )


async def apagar(sessao: AsyncSession, canal: str, endereco: str) -> bool:
    resultado = await sessao.execute(
        delete(AcessoCanal)
        .where(AcessoCanal.canal == canal, AcessoCanal.endereco == endereco)
        .returning(AcessoCanal.id)
    )
    return resultado.first() is not None


async def listar(sessao: AsyncSession, canal: str) -> list[AcessoCanal]:
    return list(
        await sessao.scalars(
            select(AcessoCanal).where(AcessoCanal.canal == canal).order_by(AcessoCanal.endereco)
        )
    )
