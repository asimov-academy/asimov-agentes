"""Conversa do operador com um agente nativo, pelo terminal.

Mandar grava a mensagem e agenda o buffer, como um webhook: a IA roda só no worker. Ler devolve o que
o agente mandou desde a última leitura, se está digitando e o handoff aberto.
"""

import uuid
from dataclasses import dataclass
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.agentes import repo as agentes_repo
from app.agentes.modelos import Agente
from app.canais.nativo import memoria
from app.canais.nativo.canal import ID_CONTATO, Nativo
from app.conversas import buffer
from app.conversas import repo as conversas_repo
from app.conversas.modelos import Conversa, Mensagem
from app.handoff import repo as handoff_repo


class NaoEncontrado(LookupError):
    pass


class NaoENativo(ValueError):
    pass


@dataclass(frozen=True)
class Enviada:
    conversa: str
    conversa_id: uuid.UUID
    agendada: bool
    """False com handoff aberto: a mensagem fica gravada e o agente não responde."""


@dataclass(frozen=True)
class Leitura:
    mensagens: list[dict[str, Any]]
    proxima: int
    digitando: bool
    respondendo: bool
    """Turno em andamento: resposta, handoff ou resumo ainda podem chegar."""
    handoff: dict[str, Any] | None


async def _agente(sessao: AsyncSession, cliente_id: uuid.UUID, agente_id: uuid.UUID) -> Agente:
    agente = await agentes_repo.obter(sessao, cliente_id, agente_id)
    if agente is None or not agente.ativo:
        raise NaoEncontrado("agente não encontrado")
    if agente.canal != Nativo.nome:
        raise NaoENativo("só agentes nativos conversam no terminal")
    return agente


async def _conversa(
    sessao: AsyncSession, cliente_id: uuid.UUID, agente_id: uuid.UUID, conversa: str
) -> Conversa:
    encontrada = await conversas_repo.conversa_por_externo(sessao, cliente_id, agente_id, conversa)
    if encontrada is None:
        raise NaoEncontrado("conversa não encontrada")
    return encontrada


async def enviar(
    sessao: AsyncSession,
    fila: Any,
    cliente_id: uuid.UUID,
    agente_id: uuid.UUID,
    texto: str,
    conversa: str | None,
) -> Enviada:
    """Sem `conversa`, começa uma nova. Quem chama já validou o texto."""
    agente = await _agente(sessao, cliente_id, agente_id)
    if conversa is None:
        contato = await conversas_repo.contato_do_canal(
            sessao, cliente_id, agente.id, ID_CONTATO, "Operador no terminal", None
        )
        atual = await conversas_repo.conversa_do_canal(
            sessao, cliente_id, agente.id, contato.id, uuid.uuid4().hex
        )
    else:
        atual = await _conversa(sessao, cliente_id, agente.id, conversa)

    await conversas_repo.grava_mensagem(
        sessao,
        Mensagem(
            cliente_id=cliente_id,
            conversa_id=atual.id,
            direcao="entrada",
            autor="contato",
            texto=texto,
            id_externo=uuid.uuid4().hex,
        ),
    )
    await sessao.commit()

    agendada = atual.status != "humano"
    if agendada:
        await buffer.agenda_turno(fila, cliente_id, atual.id, agente.buffer_segundos)
    return Enviada(conversa=atual.id_externo, conversa_id=atual.id, agendada=agendada)


async def ler(
    sessao: AsyncSession, cliente_id: uuid.UUID, agente_id: uuid.UUID, conversa: str, depois: int
) -> Leitura:
    agente = await _agente(sessao, cliente_id, agente_id)
    atual = await _conversa(sessao, cliente_id, agente.id, conversa)
    # O lock primeiro: livre aqui, tudo que o turno gravou já está no Redis e no banco.
    async with memoria.conexao() as r:
        respondendo = await buffer.turno_em_andamento(r, atual.id)
    mensagens = await memoria.le_saida(atual.id_externo, depois)
    handoff = await handoff_repo.aberto(sessao, cliente_id, atual.id)
    return Leitura(
        mensagens=mensagens,
        proxima=depois + len(mensagens),
        digitando=await memoria.esta_digitando(atual.id_externo),
        respondendo=respondendo,
        handoff=(
            {"motivo": handoff.motivo, "resumo": handoff.resumo, "codigo": handoff.codigo}
            if handoff is not None
            else None
        ),
    )
