import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import func, or_, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import set_committed_value

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
    canal: str,
) -> Conversa:
    instrucao = (
        insert(Conversa)
        .values(
            id=uuid.uuid4(),
            cliente_id=cliente_id,
            agente_id=agente_id,
            contato_id=contato_id,
            id_externo=id_externo,
            canal=canal,
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


async def marca_respondido(
    sessao: AsyncSession, cliente_id: uuid.UUID, conversa_id: uuid.UUID, ate: datetime
) -> None:
    await sessao.execute(
        update(Conversa)
        .where(Conversa.cliente_id == cliente_id, Conversa.id == conversa_id)
        .values(respondido_ate=func.greatest(func.coalesce(Conversa.respondido_ate, ate), ate))
    )


async def muda_status(
    sessao: AsyncSession, cliente_id: uuid.UUID, conversa_id: uuid.UUID, status: str
) -> None:
    """`agente` ou `humano`."""
    await sessao.execute(
        update(Conversa)
        .where(Conversa.cliente_id == cliente_id, Conversa.id == conversa_id)
        .values(status=status, atualizado_em=agora())
    )


async def tem_entrada_pendente(
    sessao: AsyncSession, cliente_id: uuid.UUID, conversa_id: uuid.UUID
) -> bool:
    """Fala do contato que nenhum turno respondeu ainda.

    Serve para a reentrega do canal recuperar um agendamento perdido: a mensagem está gravada, a
    deduplicação diz que não é nova, e sem isto ela ficaria sem turno para sempre (auditoria de
    2026-09-18, A01).
    """
    respondido = (
        select(Conversa.respondido_ate).where(Conversa.id == conversa_id).scalar_subquery()
    )
    achou = await sessao.scalar(
        select(Mensagem.id)
        .where(
            Mensagem.cliente_id == cliente_id,
            Mensagem.conversa_id == conversa_id,
            Mensagem.direcao == "entrada",
            Mensagem.autor == "contato",
            or_(respondido.is_(None), Mensagem.criado_em > respondido),
        )
        .limit(1)
    )
    return achou is not None


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


async def mensagens_do_turno(
    sessao: AsyncSession,
    cliente_id: uuid.UUID,
    conversa_id: uuid.UUID,
    respondido_ate: datetime | None,
    historico: int = 40,
    teto_pendentes: int = 200,
) -> tuple[list[Mensagem], bool]:
    """Histórico recente mais tudo o que chegou depois da última resposta.

    O limite do histórico é de contexto, e cortava junto as falas ainda não respondidas: numa
    rajada de mais de 40 mensagens o agente deixava de ver as primeiras e o marcador passava por
    cima delas (auditoria de 2026-09-18, A09). O segundo valor diz se a rajada passou do teto.
    """
    if respondido_ate is None:
        # Conversa que nenhum turno respondeu ainda: tudo o que está lá é pendente, e o limite de
        # histórico cortaria as primeiras falas justamente na rajada que criou a conversa.
        tudo = await ultimas_mensagens(sessao, cliente_id, conversa_id, teto_pendentes + 1)
        return tudo[-teto_pendentes:], len(tudo) > teto_pendentes

    depois = list(
        reversed(
            list(
                await sessao.scalars(
                    select(Mensagem)
                    .where(
                        Mensagem.cliente_id == cliente_id,
                        Mensagem.conversa_id == conversa_id,
                        Mensagem.criado_em > respondido_ate,
                    )
                    .order_by(Mensagem.criado_em.desc())
                    .limit(teto_pendentes + 1)
                )
            )
        )
    )
    excedeu = len(depois) > teto_pendentes
    depois = depois[-teto_pendentes:]
    antes = list(
        reversed(
            list(
                await sessao.scalars(
                    select(Mensagem)
                    .where(
                        Mensagem.cliente_id == cliente_id,
                        Mensagem.conversa_id == conversa_id,
                        Mensagem.criado_em <= respondido_ate,
                    )
                    .order_by(Mensagem.criado_em.desc())
                    .limit(historico)
                )
            )
        )
    )
    return antes + depois, excedeu


async def registra_leitura_de_midia(
    sessao: AsyncSession,
    cliente_id: uuid.UUID,
    mensagem: Mensagem,
    anexo: dict[str, Any],
    texto_extraido: str | None,
    midia_id: uuid.UUID | None,
) -> None:
    await sessao.execute(
        update(Mensagem)
        .where(Mensagem.cliente_id == cliente_id, Mensagem.id == mensagem.id)
        .values(anexo=anexo, texto_extraido=texto_extraido, midia_id=midia_id)
    )
    for campo, valor in (("anexo", anexo), ("texto_extraido", texto_extraido), ("midia_id", midia_id)):
        set_committed_value(mensagem, campo, valor)


async def obter_contato(
    sessao: AsyncSession, cliente_id: uuid.UUID, contato_id: uuid.UUID
) -> Contato | None:
    return await sessao.scalar(
        select(Contato).where(Contato.cliente_id == cliente_id, Contato.id == contato_id)
    )
