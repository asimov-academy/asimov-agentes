"""Acesso ao banco do funil. Todo método recebe `cliente_id` e filtra por ele, sem exceção."""

import uuid
from decimal import Decimal
from typing import Any

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.conversas.modelos import Contato
from app.oportunidades.modelos import EtapaFunil, Etiqueta, Oportunidade, OportunidadeEtiqueta

# Etapas


async def etapas(sessao: AsyncSession, cliente_id: uuid.UUID) -> list[EtapaFunil]:
    return list(
        await sessao.scalars(
            select(EtapaFunil)
            .where(EtapaFunil.cliente_id == cliente_id)
            .order_by(EtapaFunil.ordem, EtapaFunil.nome)
        )
    )


async def etapa(sessao: AsyncSession, cliente_id: uuid.UUID, etapa_id: uuid.UUID) -> EtapaFunil | None:
    return await sessao.scalar(
        select(EtapaFunil).where(EtapaFunil.cliente_id == cliente_id, EtapaFunil.id == etapa_id)
    )


async def cria_etapa(sessao: AsyncSession, etapa: EtapaFunil) -> EtapaFunil:
    sessao.add(etapa)
    await sessao.flush()
    return etapa


async def apaga_etapa(sessao: AsyncSession, cliente_id: uuid.UUID, etapa_id: uuid.UUID) -> bool:
    resultado = await sessao.execute(
        delete(EtapaFunil)
        .where(EtapaFunil.cliente_id == cliente_id, EtapaFunil.id == etapa_id)
        .returning(EtapaFunil.id)
    )
    return resultado.first() is not None


async def quantas_na_etapa(sessao: AsyncSession, cliente_id: uuid.UUID, etapa_id: uuid.UUID) -> int:
    return await sessao.scalar(
        select(func.count())
        .select_from(Oportunidade)
        .where(Oportunidade.cliente_id == cliente_id, Oportunidade.etapa_id == etapa_id)
    ) or 0


# Etiquetas


async def etiquetas(sessao: AsyncSession, cliente_id: uuid.UUID) -> list[Etiqueta]:
    return list(
        await sessao.scalars(
            select(Etiqueta).where(Etiqueta.cliente_id == cliente_id).order_by(Etiqueta.nome)
        )
    )


async def cria_etiqueta(sessao: AsyncSession, etiqueta: Etiqueta) -> Etiqueta:
    sessao.add(etiqueta)
    await sessao.flush()
    return etiqueta


async def apaga_etiqueta(sessao: AsyncSession, cliente_id: uuid.UUID, etiqueta_id: uuid.UUID) -> bool:
    resultado = await sessao.execute(
        delete(Etiqueta)
        .where(Etiqueta.cliente_id == cliente_id, Etiqueta.id == etiqueta_id)
        .returning(Etiqueta.id)
    )
    return resultado.first() is not None


async def etiquetas_por_id(
    sessao: AsyncSession, cliente_id: uuid.UUID, ids: list[uuid.UUID]
) -> list[Etiqueta]:
    """Só as que são desta empresa: id de etiqueta de outra empresa simplesmente não volta."""
    if not ids:
        return []
    return list(
        await sessao.scalars(
            select(Etiqueta).where(Etiqueta.cliente_id == cliente_id, Etiqueta.id.in_(ids))
        )
    )


# Oportunidades


async def oportunidades(sessao: AsyncSession, cliente_id: uuid.UUID) -> list[dict[str, Any]]:
    """O quadro inteiro de uma empresa, com o contato e as etiquetas de cada cartão."""
    linhas = (
        await sessao.execute(
            select(Oportunidade, Contato.nome, Contato.telefone)
            .outerjoin(Contato, Contato.id == Oportunidade.contato_id)
            .where(Oportunidade.cliente_id == cliente_id)
            .order_by(Oportunidade.ordem, Oportunidade.criado_em)
        )
    ).all()

    ligacoes = (
        await sessao.execute(
            select(OportunidadeEtiqueta.oportunidade_id, OportunidadeEtiqueta.etiqueta_id)
            .join(Oportunidade, Oportunidade.id == OportunidadeEtiqueta.oportunidade_id)
            .where(Oportunidade.cliente_id == cliente_id)
        )
    ).all()
    das_etiquetas: dict[uuid.UUID, list[uuid.UUID]] = {}
    for oportunidade_id, etiqueta_id in ligacoes:
        das_etiquetas.setdefault(oportunidade_id, []).append(etiqueta_id)

    return [
        {
            "oportunidade": o,
            "contato_nome": nome,
            "contato_telefone": telefone,
            "etiquetas": das_etiquetas.get(o.id, []),
        }
        for o, nome, telefone in linhas
    ]


async def obter(
    sessao: AsyncSession, cliente_id: uuid.UUID, oportunidade_id: uuid.UUID
) -> Oportunidade | None:
    return await sessao.scalar(
        select(Oportunidade).where(
            Oportunidade.cliente_id == cliente_id, Oportunidade.id == oportunidade_id
        )
    )


async def cria(sessao: AsyncSession, oportunidade: Oportunidade) -> Oportunidade:
    sessao.add(oportunidade)
    await sessao.flush()
    return oportunidade


async def apaga(sessao: AsyncSession, cliente_id: uuid.UUID, oportunidade_id: uuid.UUID) -> bool:
    resultado = await sessao.execute(
        delete(Oportunidade)
        .where(Oportunidade.cliente_id == cliente_id, Oportunidade.id == oportunidade_id)
        .returning(Oportunidade.id)
    )
    return resultado.first() is not None


async def troca_etiquetas(
    sessao: AsyncSession, oportunidade_id: uuid.UUID, etiqueta_ids: list[uuid.UUID]
) -> None:
    await sessao.execute(
        delete(OportunidadeEtiqueta).where(
            OportunidadeEtiqueta.oportunidade_id == oportunidade_id
        )
    )
    for etiqueta_id in etiqueta_ids:
        sessao.add(
            OportunidadeEtiqueta(oportunidade_id=oportunidade_id, etiqueta_id=etiqueta_id)
        )


async def proxima_ordem(sessao: AsyncSession, cliente_id: uuid.UUID, etapa_id: uuid.UUID) -> int:
    ultima = await sessao.scalar(
        select(func.max(Oportunidade.ordem)).where(
            Oportunidade.cliente_id == cliente_id, Oportunidade.etapa_id == etapa_id
        )
    )
    return (ultima or 0) + 1


async def total_por_etapa(sessao: AsyncSession, cliente_id: uuid.UUID) -> dict[uuid.UUID, Decimal]:
    linhas = await sessao.execute(
        select(Oportunidade.etapa_id, func.coalesce(func.sum(Oportunidade.valor), 0))
        .where(Oportunidade.cliente_id == cliente_id)
        .group_by(Oportunidade.etapa_id)
    )
    return {etapa_id: total for etapa_id, total in linhas}
