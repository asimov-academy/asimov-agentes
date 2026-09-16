import uuid

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.conversas.modelos import Contato, Conversa, Mensagem
from app.plataforma.banco import agora


async def contato_do_canal(
    sessao: AsyncSession,
    cliente_id: uuid.UUID,
    agente_id: uuid.UUID,
    id_externo: str,
    nome: str | None,
    telefone: str | None,
) -> Contato:
    instrucao = (
        insert(Contato)
        .values(
            id=uuid.uuid4(),
            cliente_id=cliente_id,
            agente_id=agente_id,
            id_externo=id_externo,
            nome=nome,
            telefone=telefone,
            criado_em=agora(),
            ultima_mensagem_em=agora(),
        )
        .on_conflict_do_update(
            index_elements=["agente_id", "id_externo"],
            set_={"ultima_mensagem_em": agora(), "nome": nome, "telefone": telefone},
            where=Contato.cliente_id == cliente_id,
        )
        .returning(Contato.id)
    )
    contato_id = await sessao.scalar(instrucao)
    contato = await sessao.scalar(
        select(Contato)
        .where(Contato.cliente_id == cliente_id, Contato.id == contato_id)
        .execution_options(populate_existing=True)
    )
    assert contato is not None
    return contato


async def conversa_do_canal(
    sessao: AsyncSession,
    cliente_id: uuid.UUID,
    agente_id: uuid.UUID,
    contato_id: uuid.UUID,
    id_externo: str,
) -> Conversa:
    instrucao = (
        insert(Conversa)
        .values(
            id=uuid.uuid4(),
            cliente_id=cliente_id,
            agente_id=agente_id,
            contato_id=contato_id,
            id_externo=id_externo,
            status="agente",
            criado_em=agora(),
            atualizado_em=agora(),
        )
        .on_conflict_do_update(
            index_elements=["agente_id", "id_externo"],
            set_={"atualizado_em": agora()},
            where=Conversa.cliente_id == cliente_id,
        )
        .returning(Conversa.id)
    )
    conversa_id = await sessao.scalar(instrucao)
    conversa = await obter_conversa(sessao, cliente_id, conversa_id)
    assert conversa is not None
    return conversa


async def conversa_por_externo(
    sessao: AsyncSession, cliente_id: uuid.UUID, agente_id: uuid.UUID, id_externo: str
) -> Conversa | None:
    return await sessao.scalar(
        select(Conversa).where(
            Conversa.cliente_id == cliente_id,
            Conversa.agente_id == agente_id,
            Conversa.id_externo == id_externo,
        )
    )


async def obter_conversa(
    sessao: AsyncSession, cliente_id: uuid.UUID, conversa_id: uuid.UUID
) -> Conversa | None:
    return await sessao.scalar(
        select(Conversa)
        .where(Conversa.cliente_id == cliente_id, Conversa.id == conversa_id)
        .execution_options(populate_existing=True)
    )


async def grava_mensagem(sessao: AsyncSession, mensagem: Mensagem) -> bool:
    """False quando a mensagem já existia (reentrega do webhook)."""
    valores = {
        c.key: getattr(mensagem, c.key)
        for c in Mensagem.__table__.columns
        if getattr(mensagem, c.key, None) is not None
    }
    valores.setdefault("id", uuid.uuid4())
    valores.setdefault("criado_em", agora())
    instrucao = (
        insert(Mensagem)
        .values(**valores)
        .on_conflict_do_nothing(
            index_elements=["conversa_id", "id_externo"],
            index_where=Mensagem.id_externo.is_not(None),
        )
        .returning(Mensagem.id)
    )
    return await sessao.scalar(instrucao) is not None


async def ultimas_mensagens(
    sessao: AsyncSession, cliente_id: uuid.UUID, conversa_id: uuid.UUID, limite: int = 40
) -> list[Mensagem]:
    resultado = await sessao.scalars(
        select(Mensagem)
        .where(Mensagem.cliente_id == cliente_id, Mensagem.conversa_id == conversa_id)
        .order_by(Mensagem.criado_em.desc())
        .limit(limite)
    )
    return list(reversed(list(resultado)))
