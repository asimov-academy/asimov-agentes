import uuid

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.agentes import repo as agentes_repo
from app.clientes import repo
from app.clientes.modelos import Cliente
from app.plataforma.banco import agora
from app.plataforma.textos import slug

log = structlog.get_logger()


class ClienteJaExiste(ValueError):
    pass


class NaoEncontrado(LookupError):
    pass


class ClienteComAgentes(ValueError):
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


async def remover_cliente(sessao: AsyncSession, cliente_id: uuid.UUID, confirmacao: str) -> None:
    """Exclusão lógica, só sem agentes: remover agente é o que desliga webhook e credenciais."""
    cliente = await repo.obter(sessao, cliente_id)
    if cliente is None:
        raise NaoEncontrado("empresa não encontrada")
    if slug(confirmacao) != cliente.slug:
        raise ValueError(f"confirmação não confere: digite o nome da empresa, {cliente.nome}")
    if await agentes_repo.listar(sessao, cliente_id):
        raise ClienteComAgentes("a empresa ainda tem agentes; remova os agentes antes")
    # Slug liberado para uma empresa nova com o mesmo nome.
    cliente.slug = f"{cliente.slug}~removido-{cliente.id.hex[:8]}"
    cliente.ativo = False
    cliente.removido_em = agora()
    await sessao.commit()
    log.info("cliente_removido", cliente_id=str(cliente.id))
