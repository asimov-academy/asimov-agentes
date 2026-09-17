import uuid

from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.handoff.modelos import Handoff
from app.plataforma.banco import agora


async def aberto(
    sessao: AsyncSession, cliente_id: uuid.UUID, conversa_id: uuid.UUID
) -> Handoff | None:
    return await sessao.scalar(
        select(Handoff).where(
            Handoff.cliente_id == cliente_id,
            Handoff.conversa_id == conversa_id,
            Handoff.retomado_em.is_(None),
        )
    )


async def da_conversa(
    sessao: AsyncSession, cliente_id: uuid.UUID, conversa_id: uuid.UUID
) -> list[Handoff]:
    return list(
        await sessao.scalars(
            select(Handoff)
            .where(Handoff.cliente_id == cliente_id, Handoff.conversa_id == conversa_id)
            .order_by(Handoff.iniciado_em)
        )
    )


async def abre(sessao: AsyncSession, handoff: Handoff) -> bool:
    """False quando a conversa já tinha handoff aberto."""
    instrucao = (
        insert(Handoff)
        .values(
            id=handoff.id or uuid.uuid4(),
            cliente_id=handoff.cliente_id,
            agente_id=handoff.agente_id,
            conversa_id=handoff.conversa_id,
            motivo=handoff.motivo,
            resumo=handoff.resumo,
            codigo=handoff.codigo,
            destino=handoff.destino,
            iniciado_em=agora(),
            retomar_em=handoff.retomar_em,
        )
        .on_conflict_do_nothing(
            index_elements=["conversa_id"], index_where=Handoff.retomado_em.is_(None)
        )
        .returning(Handoff.id)
    )
    return await sessao.scalar(instrucao) is not None


async def fecha(
    sessao: AsyncSession, cliente_id: uuid.UUID, conversa_id: uuid.UUID, por: str
) -> bool:
    """False quando não havia handoff aberto."""
    fechado = await sessao.scalar(
        update(Handoff)
        .where(
            Handoff.cliente_id == cliente_id,
            Handoff.conversa_id == conversa_id,
            Handoff.retomado_em.is_(None),
        )
        .values(retomado_em=agora(), retomado_por=por)
        .returning(Handoff.id)
    )
    return fechado is not None
