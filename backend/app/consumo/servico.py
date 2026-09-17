import uuid
from datetime import timedelta
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.clientes import repo as clientes_repo
from app.consumo import repo
from app.plataforma.banco import agora


class NaoEncontrado(LookupError):
    pass


async def relatorio(
    sessao: AsyncSession,
    dias: int,
    cliente_id: uuid.UUID | None = None,
    agente_id: uuid.UUID | None = None,
) -> dict[str, Any]:
    """Consumo por agente e últimas falhas. Sem cliente, a instalação inteira (visão do operador)."""
    desde = agora() - timedelta(days=dias)
    if cliente_id is None:
        agentes, falhas = await repo.consumo_de_todos_os_clientes(sessao, desde)
    else:
        if await clientes_repo.obter(sessao, cliente_id) is None:
            raise NaoEncontrado("empresa não encontrada")
        agentes, falhas = await repo.consumo(sessao, cliente_id, desde, agente_id)
    return {"dias": dias, "desde": desde, "agentes": agentes, "falhas": falhas}
