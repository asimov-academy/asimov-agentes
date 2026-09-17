"""Handoff: passar a conversa para humano e retomar quando ela volta.

Transferir: resumo com o modelo auxiliar, transferência no canal (nota, atribuição, pausa) e só
então o registro do Handoff aberto. Com handoff já aberto não faz nada: é idempotente.
Retomar: fecha o handoff aberto e devolve a conversa ao agente.
"""

import secrets
import time
import uuid
from datetime import timedelta
from typing import TYPE_CHECKING, Any

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.agentes import repo as agentes_repo
from app.agentes import servico as agentes_servico
from app.consumo.modelos import Turno
from app.consumo.repo import grava_turno, registra_falha
from app.conversas import repo as conversas_repo
from app.handoff import repo
from app.handoff.modelos import Handoff
from app.ia.agente import conteudo, resume_conversa
from app.plataforma.banco import agora

if TYPE_CHECKING:
    from app.agentes.modelos import Agente
    from app.canais.base import Canal
    from app.conversas.modelos import Conversa, Mensagem

log = structlog.get_logger()

MENSAGEM_DE_EXPECTATIVA = (
    "Tive um problema para te responder agora. Já chamei uma pessoa da equipe, "
    "que vai continuar o atendimento por aqui."
)
MOTIVO_FALHA_NO_TURNO = "o agente não conseguiu responder (modelo ou tool com erro)"
MOTIVO_ARQUIVO_GRANDE = "contato enviou arquivo grande ou longo demais para o agente abrir"

_LETRAS_DO_CODIGO = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"


def novo_codigo() -> str:
    return "".join(secrets.choice(_LETRAS_DO_CODIGO) for _ in range(6))


def nota_para_atendente(motivo: str, resumo: str) -> str:
    """Curta: o atendente lê no meio da conversa. O tamanho do resumo vem de `resumo_handoff.md`."""
    return f"Motivo: {motivo}\n{resumo}"


async def _resumo(
    sessao: AsyncSession,
    agente: "Agente",
    conversa_id: uuid.UUID,
    mensagens: list["Mensagem"],
    motivo: str,
) -> str:
    """Sem resumo do modelo, a nota leva as últimas falas do contato: o handoff não pode travar."""
    inicio = time.monotonic()
    try:
        resultado = await resume_conversa(agente, mensagens, motivo)
    except Exception as erro:
        await registra_falha(
            "resumo_handoff_falhou", {"erro": repr(erro)[:500]}, agente.cliente_id, agente.id
        )
        falas = [conteudo(m)[:300] for m in mensagens if m.autor == "contato"][-3:]
        return "Resumo automático indisponível. Últimas falas do contato:\n" + "\n".join(falas)
    await grava_turno(
        sessao,
        Turno(
            cliente_id=agente.cliente_id,
            conversa_id=conversa_id,
            modelo=agente.modelo_auxiliar,
            funcao="resumo_handoff",
            tokens_entrada=resultado.tokens_entrada,
            tokens_saida=resultado.tokens_saida,
            custo_estimado=resultado.custo_estimado,
            latencia_ms=int((time.monotonic() - inicio) * 1000),
        ),
    )
    return resultado.texto or "Resumo vazio."


async def transferir(
    sessao: AsyncSession,
    agente: "Agente",
    canal: "Canal",
    credenciais: dict[str, Any],
    conversa: "Conversa",
    motivo: str,
) -> str:
    """Devolve `transferido`, `ja_aberto` ou `falhou`. Quem chama faz o commit."""
    if await repo.aberto(sessao, agente.cliente_id, conversa.id) is not None:
        return "ja_aberto"

    mensagens = await conversas_repo.ultimas_mensagens(sessao, agente.cliente_id, conversa.id)
    resumo = await _resumo(sessao, agente, conversa.id, mensagens, motivo)
    try:
        problemas = await canal.transferir(
            credenciais,
            conversa.id_externo,
            agente.handoff_destino,
            nota_para_atendente(motivo, resumo),
        )
    except Exception as erro:
        await registra_falha("handoff_falhou", {"erro": repr(erro)[:500]}, agente.cliente_id, agente.id)
        return "falhou"
    if problemas:
        await registra_falha(
            "handoff_incompleto", {"problemas": problemas}, agente.cliente_id, agente.id
        )

    horas = agente.retomada_automatica_horas
    await repo.abre(
        sessao,
        Handoff(
            cliente_id=agente.cliente_id,
            agente_id=agente.id,
            conversa_id=conversa.id,
            motivo=motivo,
            resumo=resumo,
            codigo=novo_codigo(),
            destino=agente.handoff_destino,
            retomar_em=agora() + timedelta(hours=horas) if horas else None,
        ),
    )
    await conversas_repo.muda_status(sessao, agente.cliente_id, conversa.id, "humano")
    log.info("handoff_aberto", destino=(agente.handoff_destino or {}).get("tipo"))
    return "transferido"


async def retomar(
    sessao: AsyncSession, cliente_id: uuid.UUID, conversa_id: uuid.UUID, por: str
) -> bool:
    """Fecha o handoff aberto e devolve a conversa ao agente. False se não havia handoff aberto."""
    fechou = await repo.fecha(sessao, cliente_id, conversa_id, por)
    await conversas_repo.muda_status(sessao, cliente_id, conversa_id, "agente")
    if fechou:
        log.info("handoff_retomado", por=por)
    return fechou


class ConversaNaoEncontrada(LookupError):
    pass


async def retomar_pelo_operador(
    sessao: AsyncSession, cliente_id: uuid.UUID, conversa_id: uuid.UUID
) -> bool:
    """Devolve a conversa no canal e fecha o handoff. False se não havia handoff aberto.

    Se o canal recusar, o handoff continua aberto: o agente não pode falar onde o canal não deixa.
    """
    conversa = await conversas_repo.obter_conversa(sessao, cliente_id, conversa_id)
    if conversa is None:
        raise ConversaNaoEncontrada("conversa não encontrada")
    agente = await agentes_repo.obter(sessao, cliente_id, conversa.agente_id)
    if agente is None:
        raise ConversaNaoEncontrada("o agente desta conversa foi removido")
    canal, credenciais = agentes_servico.canal_da_conversa(agente, conversa)
    await canal.devolver_ao_agente(credenciais, conversa.id_externo)
    fechou = await retomar(sessao, cliente_id, conversa_id, "operador")
    await sessao.commit()
    return fechou
