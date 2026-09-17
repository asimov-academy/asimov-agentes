import uuid
from datetime import datetime
from typing import Any

import structlog
from sqlalchemy import Select, and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agentes.modelos import Agente
from app.clientes.modelos import Cliente
from app.consumo.modelos import Falha, Turno
from app.conversas.modelos import Conversa
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


def _consumo_por_agente(desde: datetime) -> Select[Any]:
    """Uma linha por agente. Leitura de mídia e resumo de handoff somam tokens e custo, não turnos."""
    return (
        select(
            Turno.cliente_id,
            Cliente.nome.label("cliente"),
            Conversa.agente_id,
            Agente.nome.label("agente"),
            func.count().filter(Turno.funcao == "resposta").label("turnos"),
            func.count().label("chamadas"),
            func.coalesce(func.sum(Turno.tokens_entrada), 0).label("tokens_entrada"),
            func.coalesce(func.sum(Turno.tokens_saida), 0).label("tokens_saida"),
            func.coalesce(func.sum(Turno.custo_estimado), 0).label("custo_estimado"),
            func.count().filter(Turno.custo_estimado.is_(None)).label("sem_custo"),
        )
        .join(Conversa, and_(Conversa.id == Turno.conversa_id, Conversa.cliente_id == Turno.cliente_id))
        .join(Agente, and_(Agente.id == Conversa.agente_id, Agente.cliente_id == Turno.cliente_id))
        .join(Cliente, Cliente.id == Turno.cliente_id)
        .where(Turno.criado_em >= desde)
        .group_by(Turno.cliente_id, Cliente.nome, Conversa.agente_id, Agente.nome)
        .order_by(Cliente.nome, Agente.nome)
    )


def _ultimas_falhas(desde: datetime, limite: int) -> Select[Any]:
    return (
        select(
            Falha.criado_em,
            Falha.tipo,
            Falha.detalhe,
            Falha.cliente_id,
            Cliente.nome.label("cliente"),
            Falha.agente_id,
            Agente.nome.label("agente"),
        )
        .outerjoin(Cliente, Cliente.id == Falha.cliente_id)
        .outerjoin(Agente, and_(Agente.id == Falha.agente_id, Agente.cliente_id == Falha.cliente_id))
        .where(Falha.criado_em >= desde)
        .order_by(Falha.criado_em.desc())
        .limit(limite)
    )


async def consumo(
    sessao: AsyncSession,
    cliente_id: uuid.UUID,
    desde: datetime,
    agente_id: uuid.UUID | None = None,
    limite_falhas: int = 10,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    turnos = _consumo_por_agente(desde).where(Turno.cliente_id == cliente_id)
    falhas = _ultimas_falhas(desde, limite_falhas).where(Falha.cliente_id == cliente_id)
    if agente_id is not None:
        turnos = turnos.where(Conversa.agente_id == agente_id)
        falhas = falhas.where(Falha.agente_id == agente_id)
    return await _linhas(sessao, turnos), await _linhas(sessao, falhas)


async def consumo_de_todos_os_clientes(
    sessao: AsyncSession, desde: datetime, limite_falhas: int = 10
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Só para o menu do operador, que administra a instalação inteira. Inclui falhas sem cliente."""
    return (
        await _linhas(sessao, _consumo_por_agente(desde)),
        await _linhas(sessao, _ultimas_falhas(desde, limite_falhas)),
    )


async def _linhas(sessao: AsyncSession, consulta: Select[Any]) -> list[dict[str, Any]]:
    return [dict(linha._mapping) for linha in await sessao.execute(consulta)]
