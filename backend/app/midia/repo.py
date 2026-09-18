import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.midia.modelos import Midia
from app.plataforma.banco import agora


async def por_hash(sessao: AsyncSession, cliente_id: uuid.UUID, hash_sha256: str) -> Midia | None:
    return await sessao.scalar(
        select(Midia).where(Midia.cliente_id == cliente_id, Midia.hash_sha256 == hash_sha256)
    )


async def grava(sessao: AsyncSession, midia: Midia) -> Midia:
    """Dois turnos lendo o mesmo arquivo ao mesmo tempo: fica o primeiro registro."""
    await sessao.execute(
        insert(Midia)
        .values(
            id=midia.id or uuid.uuid4(),
            cliente_id=midia.cliente_id,
            hash_sha256=midia.hash_sha256,
            tipo_mime=midia.tipo_mime,
            tamanho_bytes=midia.tamanho_bytes,
            caminho_arquivo=midia.caminho_arquivo,
            resultado=midia.resultado,
            metadados=midia.metadados or {},
            criado_em=agora(),
        )
        .on_conflict_do_nothing(index_elements=["cliente_id", "hash_sha256"])
    )
    gravada = await por_hash(sessao, midia.cliente_id, midia.hash_sha256)
    assert gravada is not None
    return gravada


async def com_arquivo_antigo(sessao: AsyncSession, limite: datetime, maximo: int = 500) -> list[Midia]:
    """Mídia cujo arquivo já passou do prazo no disco e ainda não foi apagado."""
    return list(
        await sessao.scalars(
            select(Midia)
            .where(Midia.criado_em < limite, Midia.arquivo_apagado_em.is_(None))
            .order_by(Midia.criado_em)
            .limit(maximo)
        )
    )
