"""Acesso ao banco da base de conhecimento. Toda consulta filtra `cliente_id`, e a busca também
filtra `agente_id` no `WHERE`: base de um agente nunca responde por outro (spec/usuarios.md)."""

import uuid
from typing import Any

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.conhecimento.modelos import Documento, Trecho
from app.plataforma.banco import agora


async def cria_documento(
    sessao: AsyncSession,
    cliente_id: uuid.UUID,
    agente_id: uuid.UUID,
    nome_arquivo: str,
    hash_sha256: str,
    tipo_mime: str,
    origem: str,
    caminho_arquivo: str = "",
) -> Documento:
    documento = Documento(
        cliente_id=cliente_id,
        agente_id=agente_id,
        nome_arquivo=nome_arquivo[:300],
        caminho_arquivo=caminho_arquivo[:500],
        hash_sha256=hash_sha256,
        tipo_mime=tipo_mime[:120],
        origem=origem,
    )
    sessao.add(documento)
    await sessao.commit()
    await sessao.refresh(documento)
    return documento


async def obter(
    sessao: AsyncSession, cliente_id: uuid.UUID, documento_id: uuid.UUID
) -> Documento | None:
    return await sessao.scalar(
        select(Documento).where(
            Documento.id == documento_id,
            Documento.cliente_id == cliente_id,
            Documento.removido_em.is_(None),
        )
    )


async def por_hash(
    sessao: AsyncSession, cliente_id: uuid.UUID, agente_id: uuid.UUID, hash_sha256: str
) -> Documento | None:
    return await sessao.scalar(
        select(Documento).where(
            Documento.cliente_id == cliente_id,
            Documento.agente_id == agente_id,
            Documento.hash_sha256 == hash_sha256,
            Documento.removido_em.is_(None),
        )
    )


async def listar(
    sessao: AsyncSession, cliente_id: uuid.UUID, agente_id: uuid.UUID
) -> list[Documento]:
    resultado = await sessao.scalars(
        select(Documento)
        .where(
            Documento.cliente_id == cliente_id,
            Documento.agente_id == agente_id,
            Documento.removido_em.is_(None),
        )
        .order_by(Documento.criado_em.desc())
    )
    return list(resultado)


async def marca(
    sessao: AsyncSession,
    cliente_id: uuid.UUID,
    documento_id: uuid.UUID,
    status: str,
    total_trechos: int = 0,
    erro: str = "",
) -> None:
    await sessao.execute(
        update(Documento)
        .where(Documento.id == documento_id, Documento.cliente_id == cliente_id)
        .values(status=status, total_trechos=total_trechos, erro=erro[:1000])
    )
    await sessao.commit()


async def grava_trechos(
    sessao: AsyncSession, documento: Documento, trechos: list[tuple[str, list[float]]]
) -> None:
    """Troca os trechos do documento pelos novos, numa transação só."""
    await sessao.execute(delete(Trecho).where(Trecho.documento_id == documento.id))
    sessao.add_all(
        [
            Trecho(
                cliente_id=documento.cliente_id,
                agente_id=documento.agente_id,
                documento_id=documento.id,
                ordem=ordem,
                texto=texto,
                embedding=vetor,
            )
            for ordem, (texto, vetor) in enumerate(trechos)
        ]
    )
    await sessao.commit()


async def remove(sessao: AsyncSession, cliente_id: uuid.UUID, documento: Documento) -> None:
    """Exclusão lógica do documento, e os trechos saem de verdade: eles são só cópia do arquivo."""
    await sessao.execute(delete(Trecho).where(Trecho.documento_id == documento.id))
    documento.removido_em = agora()
    documento.total_trechos = 0
    await sessao.commit()


async def busca(
    sessao: AsyncSession,
    cliente_id: uuid.UUID,
    agente_id: uuid.UUID,
    vetor: list[float],
    quantos: int = 5,
) -> list[dict[str, Any]]:
    """Os trechos mais próximos da pergunta, deste agente e deste cliente. Nunca de outro."""
    distancia = Trecho.embedding.cosine_distance(vetor).label("distancia")
    linhas = await sessao.execute(
        select(Trecho.texto, Documento.nome_arquivo, distancia)
        .join(Documento, Documento.id == Trecho.documento_id)
        .where(
            Trecho.cliente_id == cliente_id,
            Trecho.agente_id == agente_id,
            Documento.removido_em.is_(None),
        )
        .order_by(distancia)
        .limit(quantos)
    )
    return [
        {"texto": texto, "documento": nome, "distancia": float(d)} for texto, nome, d in linhas
    ]
