import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agentes.modelos import Agente
from app.clientes.modelos import Cliente
from app.consumo.modelos import Falha, Turno
from app.conversas.modelos import Contato, Conversa
from app.handoff.modelos import Handoff
from app.painel.modelos import UsuarioPainel
from app.plataforma.banco import agora


async def operador(sessao: AsyncSession) -> UsuarioPainel | None:
    return await sessao.scalar(select(UsuarioPainel).limit(1))


async def cria(sessao: AsyncSession, senha: str) -> UsuarioPainel:
    usuario = UsuarioPainel(senha=senha)
    sessao.add(usuario)
    await sessao.flush()
    return usuario


async def troca_senha(sessao: AsyncSession, usuario: UsuarioPainel, senha: str) -> None:
    usuario.senha = senha


async def marca_acesso(sessao: AsyncSession, usuario: UsuarioPainel) -> None:
    usuario.ultimo_acesso_em = agora()


# Visão geral
#
# Leituras do painel para a tela de abertura. Todas aceitam `cliente_id` opcional: sem ele, a
# instalação inteira. É uma das exceções já previstas no AGENTS.md (listagem global do operador),
# nunca dado de uma empresa pedido por outra: quem chama aqui é a sessão do operador, e quando o
# filtro vem preenchido a rota já conferiu que a empresa existe.


async def totais(
    sessao: AsyncSession,
    desde: datetime,
    cliente_id: uuid.UUID | None = None,
    ate: datetime | None = None,
) -> dict[str, Any]:
    """Os números dos cartões: conversas novas, turnos respondidos, custo e falhas no período.

    O `ate` existe para o serviço pedir o mesmo bloco do período anterior e o painel conseguir
    dizer se o número subiu ou desceu. Número sozinho não diz nada.
    """
    turnos = select(
        func.count().filter(Turno.funcao == "resposta").label("turnos"),
        func.coalesce(func.sum(Turno.custo_estimado), 0).label("custo"),
        func.count().filter(Turno.custo_estimado.is_(None)).label("sem_custo"),
    ).where(Turno.criado_em >= desde)
    conversas = select(func.count()).select_from(Conversa).where(Conversa.criado_em >= desde)
    falhas = select(func.count()).select_from(Falha).where(Falha.criado_em >= desde)
    if ate is not None:
        turnos = turnos.where(Turno.criado_em < ate)
        conversas = conversas.where(Conversa.criado_em < ate)
        falhas = falhas.where(Falha.criado_em < ate)
    if cliente_id is not None:
        turnos = turnos.where(Turno.cliente_id == cliente_id)
        conversas = conversas.where(Conversa.cliente_id == cliente_id)
        falhas = falhas.where(Falha.cliente_id == cliente_id)

    linha = (await sessao.execute(turnos)).one()
    return {
        "conversas": await sessao.scalar(conversas) or 0,
        "turnos": linha.turnos,
        "custo": Decimal(linha.custo),
        "custo_parcial": linha.sem_custo > 0,
        "falhas": await sessao.scalar(falhas) or 0,
    }


async def resolucao(
    sessao: AsyncSession, desde: datetime, cliente_id: uuid.UUID | None = None
) -> dict[str, int]:
    """Conversas do período e quantas delas precisaram de gente.

    É o número que o operador de fato quer saber do agente: de cada dez conversas, quantas ele
    fechou sozinho. Vira o ponteiro (gauge) da AXIS na tela.
    """
    conversas = select(func.count()).select_from(Conversa).where(Conversa.criado_em >= desde)
    com_gente = (
        select(func.count(func.distinct(Handoff.conversa_id)))
        .join(Conversa, Conversa.id == Handoff.conversa_id)
        .where(Conversa.criado_em >= desde)
    )
    if cliente_id is not None:
        conversas = conversas.where(Conversa.cliente_id == cliente_id)
        com_gente = com_gente.where(Handoff.cliente_id == cliente_id)
    return {
        "conversas": await sessao.scalar(conversas) or 0,
        "com_gente": await sessao.scalar(com_gente) or 0,
    }


async def serie_de_turnos(
    sessao: AsyncSession, desde: datetime, por: str, cliente_id: uuid.UUID | None = None
) -> list[dict[str, Any]]:
    """Turnos por hora (período de um dia) ou por dia. O gráfico de linha da Visão geral.

    O buraco de um dia sem turno é preenchido no serviço, não aqui: consulta não inventa linha.
    """
    # `AT TIME ZONE 'UTC'` antes de truncar: sem isso a fatia sai no fuso da sessão do Postgres e
    # o dia do gráfico deixa de bater com o dia que o serviço monta em Python.
    fatia = func.date_trunc(por, func.timezone("UTC", Turno.criado_em)).label("quando")
    consulta = (
        select(fatia, func.count().filter(Turno.funcao == "resposta").label("turnos"))
        .where(Turno.criado_em >= desde)
        .group_by(fatia)
        .order_by(fatia)
    )
    if cliente_id is not None:
        consulta = consulta.where(Turno.cliente_id == cliente_id)
    return [dict(linha._mapping) for linha in await sessao.execute(consulta)]


async def gasto_por_modelo(
    sessao: AsyncSession, desde: datetime, cliente_id: uuid.UUID | None = None
) -> list[dict[str, Any]]:
    """Quanto cada modelo custou no período, do maior para o menor. Inclui visão e transcrição."""
    consulta = (
        select(
            Turno.modelo,
            func.count().label("chamadas"),
            func.coalesce(func.sum(Turno.tokens_entrada + Turno.tokens_saida), 0).label("tokens"),
            func.coalesce(func.sum(Turno.custo_estimado), 0).label("custo"),
        )
        .where(Turno.criado_em >= desde)
        .group_by(Turno.modelo)
        .order_by(func.coalesce(func.sum(Turno.custo_estimado), 0).desc(), Turno.modelo)
    )
    if cliente_id is not None:
        consulta = consulta.where(Turno.cliente_id == cliente_id)
    return [dict(linha._mapping) for linha in await sessao.execute(consulta)]


async def handoffs_abertos(
    sessao: AsyncSession, cliente_id: uuid.UUID | None = None, maximo: int = 10
) -> list[dict[str, Any]]:
    """Conversas ainda com gente, o vencido primeiro. Sem texto de conversa: só quem, onde e desde
    quando. O resumo do handoff fica na tela de Chat, que é a etapa 9."""
    consulta = (
        select(
            Handoff.id,
            Handoff.conversa_id,
            Handoff.codigo,
            Handoff.motivo,
            Handoff.iniciado_em,
            Handoff.retomar_em,
            Handoff.cliente_id,
            Cliente.nome.label("cliente"),
            Handoff.agente_id,
            Agente.nome.label("agente"),
            Conversa.canal,
        )
        .join(Cliente, Cliente.id == Handoff.cliente_id)
        .join(Agente, and_(Agente.id == Handoff.agente_id, Agente.cliente_id == Handoff.cliente_id))
        .join(Conversa, and_(Conversa.id == Handoff.conversa_id, Conversa.cliente_id == Handoff.cliente_id))
        .where(Handoff.retomado_em.is_(None))
        .order_by(Handoff.iniciado_em)
        .limit(maximo)
    )
    if cliente_id is not None:
        consulta = consulta.where(Handoff.cliente_id == cliente_id)
    return [dict(linha._mapping) for linha in await sessao.execute(consulta)]


# Agentes
#
# O painel abre o agente pelo id, sem a empresa na URL: é o que a lista precisa para abrir o popup
# com um clique. O `cliente_id` sai da própria linha lida do banco e nunca do corpo da requisição,
# então a garantia do AGENTS.md continua de pé.


async def agente(sessao: AsyncSession, agente_id: uuid.UUID) -> Agente | None:
    return await sessao.scalar(
        select(Agente).where(Agente.id == agente_id, Agente.removido_em.is_(None))
    )


async def agentes(
    sessao: AsyncSession, cliente_id: uuid.UUID | None = None, ativo: bool | None = None
) -> list[tuple[Agente, str]]:
    """Agentes com o nome da empresa junto, que é o que a lista mostra em cada linha."""
    consulta = (
        select(Agente, Cliente.nome)
        .join(Cliente, Cliente.id == Agente.cliente_id)
        .where(Agente.removido_em.is_(None))
        .order_by(Cliente.nome, Agente.nome)
    )
    if cliente_id is not None:
        consulta = consulta.where(Agente.cliente_id == cliente_id)
    if ativo is not None:
        consulta = consulta.where(Agente.ativo.is_(ativo))
    return [(linha[0], linha[1]) for linha in await sessao.execute(consulta)]


async def conversas_do_agente(sessao: AsyncSession, agente_id: uuid.UUID) -> int:
    return await sessao.scalar(
        select(func.count()).select_from(Conversa).where(Conversa.agente_id == agente_id)
    ) or 0


# Conversas e contatos
#
# Leituras da tela de Chat e da de Contatos. Conteúdo de conversa aparece no navegador por decisão
# registrada em spec/decisoes.md; aqui sai só o que a tela mostra, com teto em toda lista.


async def conversas(
    sessao: AsyncSession,
    cliente_id: uuid.UUID | None = None,
    agente_id: uuid.UUID | None = None,
    status: str | None = None,
    limite: int = 50,
) -> list[dict[str, Any]]:
    consulta = (
        select(
            Conversa.id,
            Conversa.canal,
            Conversa.status,
            Conversa.criado_em,
            Conversa.atualizado_em,
            Conversa.cliente_id,
            Cliente.nome.label("empresa"),
            Conversa.agente_id,
            Agente.nome.label("agente"),
            Contato.id.label("contato_id"),
            Contato.nome.label("contato"),
            Contato.telefone,
        )
        .join(Cliente, Cliente.id == Conversa.cliente_id)
        .join(Agente, and_(Agente.id == Conversa.agente_id, Agente.cliente_id == Conversa.cliente_id))
        .join(Contato, and_(Contato.id == Conversa.contato_id, Contato.cliente_id == Conversa.cliente_id))
        .order_by(Conversa.atualizado_em.desc())
        .limit(limite)
    )
    if cliente_id is not None:
        consulta = consulta.where(Conversa.cliente_id == cliente_id)
    if agente_id is not None:
        consulta = consulta.where(Conversa.agente_id == agente_id)
    if status:
        consulta = consulta.where(Conversa.status == status)
    return [_texto(dict(linha._mapping)) for linha in await sessao.execute(consulta)]


async def conversa(sessao: AsyncSession, conversa_id: uuid.UUID) -> dict[str, Any] | None:
    linhas = await conversas_por_id(sessao, conversa_id)
    return linhas[0] if linhas else None


async def conversas_por_id(sessao: AsyncSession, conversa_id: uuid.UUID) -> list[dict[str, Any]]:
    consulta = (
        select(
            Conversa.id,
            Conversa.canal,
            Conversa.status,
            Conversa.criado_em,
            Conversa.atualizado_em,
            Conversa.cliente_id,
            Cliente.nome.label("empresa"),
            Conversa.agente_id,
            Agente.nome.label("agente"),
            Contato.id.label("contato_id"),
            Contato.nome.label("contato"),
            Contato.telefone,
        )
        .join(Cliente, Cliente.id == Conversa.cliente_id)
        .join(Agente, and_(Agente.id == Conversa.agente_id, Agente.cliente_id == Conversa.cliente_id))
        .join(Contato, and_(Contato.id == Conversa.contato_id, Contato.cliente_id == Conversa.cliente_id))
        .where(Conversa.id == conversa_id)
    )
    return [_texto(dict(linha._mapping)) for linha in await sessao.execute(consulta)]


async def turnos_da_conversa(
    sessao: AsyncSession, conversa_id: uuid.UUID, limite: int = 100
) -> list[dict[str, Any]]:
    """Modelo, tempo, tokens e custo de cada turno. É o que explica a conta no fim do mês."""
    consulta = (
        select(
            Turno.criado_em,
            Turno.modelo,
            Turno.funcao,
            Turno.tokens_entrada,
            Turno.tokens_saida,
            Turno.custo_estimado,
            Turno.latencia_ms,
            Turno.erro,
        )
        .where(Turno.conversa_id == conversa_id)
        .order_by(Turno.criado_em.desc())
        .limit(limite)
    )
    return [_texto(dict(linha._mapping)) for linha in await sessao.execute(consulta)]


async def contatos(
    sessao: AsyncSession, busca: str = "", cliente_id: uuid.UUID | None = None, limite: int = 50
) -> list[dict[str, Any]]:
    consulta = (
        select(
            Contato.id,
            Contato.nome,
            Contato.telefone,
            Contato.ultima_mensagem_em,
            Contato.cliente_id,
            Cliente.nome.label("empresa"),
            Agente.nome.label("agente"),
        )
        .join(Cliente, Cliente.id == Contato.cliente_id)
        .join(Agente, and_(Agente.id == Contato.agente_id, Agente.cliente_id == Contato.cliente_id))
        .order_by(Contato.ultima_mensagem_em.desc())
        .limit(limite)
    )
    if cliente_id is not None:
        consulta = consulta.where(Contato.cliente_id == cliente_id)
    if busca:
        # Telefone digitado com traço e parêntese acha o mesmo número guardado só com dígitos.
        digitos = "".join(c for c in busca if c.isdigit())
        alvo = f"%{busca.lower()}%"
        filtro = func.lower(func.coalesce(Contato.nome, "")).like(alvo)
        if digitos:
            filtro = filtro | Contato.telefone.like(f"%{digitos}%")
        consulta = consulta.where(filtro)
    return [_texto(dict(linha._mapping)) for linha in await sessao.execute(consulta)]


async def contato(sessao: AsyncSession, contato_id: uuid.UUID) -> dict[str, Any] | None:
    linha = await sessao.execute(
        select(
            Contato.id,
            Contato.nome,
            Contato.telefone,
            Contato.id_externo,
            Contato.criado_em,
            Contato.ultima_mensagem_em,
            Contato.cliente_id,
            Cliente.nome.label("empresa"),
            Contato.agente_id,
            Agente.nome.label("agente"),
        )
        .join(Cliente, Cliente.id == Contato.cliente_id)
        .join(Agente, and_(Agente.id == Contato.agente_id, Agente.cliente_id == Contato.cliente_id))
        .where(Contato.id == contato_id)
    )
    primeira = linha.first()
    if primeira is None:
        return None
    ficha = _texto(dict(primeira._mapping))
    conversas_do_contato = await sessao.execute(
        select(Conversa.id, Conversa.canal, Conversa.status, Conversa.criado_em, Conversa.atualizado_em)
        .where(Conversa.contato_id == contato_id)
        .order_by(Conversa.atualizado_em.desc())
        .limit(50)
    )
    ficha["conversas"] = [_texto(dict(c._mapping)) for c in conversas_do_contato]
    return ficha


def _texto(linha: dict[str, Any]) -> dict[str, Any]:
    """Id vira texto e data vira ISO: o JSON da rota sai pronto, sem passar por modelo."""
    saida: dict[str, Any] = {}
    for chave, valor in linha.items():
        if isinstance(valor, uuid.UUID):
            saida[chave] = str(valor)
        elif isinstance(valor, datetime):
            saida[chave] = valor.isoformat()
        elif isinstance(valor, Decimal):
            saida[chave] = str(valor)
        else:
            saida[chave] = valor
    return saida
