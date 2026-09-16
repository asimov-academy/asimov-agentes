import uuid
from typing import Any

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.consumo.modelos import Falha, Turno
from app.plataforma.banco import fabrica_sessao

log = structlog.get_logger()


async def grava_turno(sessao: AsyncSession, turno: Turno) -> None:
    sessao.add(turno)
    await sessao.flush()


async def registra_falha(
    tipo: str,
    detalhe: dict[str, Any] | None = None,
    cliente_id: uuid.UUID | None = None,
    agente_id: uuid.UUID | None = None,
) -> None:
    """Sessão própria: a falha fica gravada mesmo quando a transação de quem chamou quebrou."""
    log.error("falha", tipo=tipo, cliente_id=str(cliente_id) if cliente_id else None)
    try:
        async with fabrica_sessao()() as sessao:
            sessao.add(
                Falha(tipo=tipo, detalhe=detalhe or {}, cliente_id=cliente_id, agente_id=agente_id)
            )
            await sessao.commit()
    except Exception as erro:
        log.error("falha_nao_gravada", tipo=tipo, erro=repr(erro))
