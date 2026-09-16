from sqlalchemy.ext.asyncio import AsyncSession

from app.clientes import repo
from app.clientes.modelos import Cliente
from app.plataforma.textos import slug


class ClienteJaExiste(ValueError):
    pass


async def criar_cliente(sessao: AsyncSession, nome: str) -> Cliente:
    nome = nome.strip()
    if not nome:
        raise ValueError("nome do cliente vazio")
    s = slug(nome)
    if await repo.slug_existe(sessao, s):
        raise ClienteJaExiste(f"já existe cliente com o identificador {s!r}")
    cliente = await repo.criar(sessao, nome, s)
    await sessao.commit()
    return cliente
