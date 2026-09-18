from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.painel.modelos import UsuarioPainel
from app.plataforma.banco import agora


async def operador(sessao: AsyncSession) -> UsuarioPainel | None:
    return await sessao.scalar(select(UsuarioPainel).limit(1))


async def cria(sessao: AsyncSession, senha: str) -> UsuarioPainel:
    usuario = UsuarioPainel(senha=senha)
    sessao.add(usuario)
    await sessao.flush()
    return usuario


async def troca_senha(sessao: AsyncSession, usuario: UsuarioPainel, senha: str) -> None:
    usuario.senha = senha


async def marca_acesso(sessao: AsyncSession, usuario: UsuarioPainel) -> None:
    usuario.ultimo_acesso_em = agora()
