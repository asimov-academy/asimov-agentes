"""Sem `cliente_id` de propósito: o acesso do operador ao canal é da instalação (ver modelos.py)."""

from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.acessos.modelos import AcessoCanal, ChaveProvedor
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


async def chaves_de_provedor(sessao: AsyncSession) -> dict[str, str]:
    """Provedor e chave em claro. Só `ia/chaves.py` chama: a chave nunca sai numa resposta."""
    linhas = await sessao.execute(select(ChaveProvedor.provedor, ChaveProvedor.chave_cifrada))
    return {provedor: cripto.decifra_texto(cifrada) for provedor, cifrada in linhas}


async def guardar_chave_de_provedor(sessao: AsyncSession, provedor: str, chave: str) -> None:
    cifrada = cripto.cifra_texto(chave)
    await sessao.execute(
        insert(ChaveProvedor)
        .values(provedor=provedor, chave_cifrada=cifrada, criado_em=agora(), atualizado_em=agora())
        .on_conflict_do_update(
            index_elements=["provedor"],
            set_={"chave_cifrada": cifrada, "atualizado_em": agora()},
        )
    )


async def apagar_chave_de_provedor(sessao: AsyncSession, provedor: str) -> bool:
    resultado = await sessao.execute(
        delete(ChaveProvedor).where(ChaveProvedor.provedor == provedor).returning(ChaveProvedor.id)
    )
    return resultado.first() is not None
