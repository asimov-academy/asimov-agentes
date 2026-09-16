"""Job do worker: um turno depois do buffer.

Ordem: token do buffer ainda vale, lock da conversa, canal ainda deixa o agente falar,
leitura das mídias pendentes, modelo, envio mensagem a mensagem com digitando, registro do Turno.
"""

import asyncio
import time
import uuid
from typing import Any

import structlog

from app.agentes import repo as agentes_repo
from app.agentes import servico as agentes_servico
from app.canais.registro import obter_canal
from app.consumo.modelos import Turno
from app.consumo.repo import grava_turno, registra_falha
from app.conversas import buffer, repo
from app.conversas.divisao import delay_ms, limita_mensagens
from app.conversas.modelos import Mensagem
from app.ia.agente import ResultadoTurno, roda_turno
from app.midia import servico as midia
from app.plataforma.banco import fabrica_sessao
from app.plataforma.config import config

log = structlog.get_logger()

REENFILEIRA_EM_SEGUNDOS = 5
_espera = asyncio.sleep


def separa_pendentes(mensagens: list[Mensagem]) -> tuple[list[Mensagem], list[Mensagem]]:
    """Pendentes são as falas do contato depois da última fala do nosso lado."""
    corte = 0
    for i, m in enumerate(mensagens):
        if m.autor != "contato":
            corte = i + 1
    return mensagens[:corte], [m for m in mensagens[corte:] if m.autor == "contato"]


async def _roda_com_tentativas(agente: Any, anteriores: list[Mensagem], pendentes: list[Mensagem]) -> ResultadoTurno:
    tentativas = config().tentativas_extra_modelo + 1
    for tentativa in range(1, tentativas + 1):
        try:
            return await roda_turno(agente, anteriores, pendentes)
        except Exception as erro:
            log.warning("modelo_falhou", tentativa=tentativa, erro=repr(erro))
            if tentativa == tentativas:
                raise
            await _espera(2**tentativa)
    raise AssertionError("inalcançável")


async def processar_turno(ctx: dict[str, Any], cliente_id: str, conversa_id: str, token: str) -> str:
    redis = ctx["redis"]
    cid, conv_id = uuid.UUID(cliente_id), uuid.UUID(conversa_id)
    structlog.contextvars.bind_contextvars(cliente_id=cliente_id, conversa_id=conversa_id)

    if not await buffer.token_ainda_vale(redis, conv_id, token):
        return "substituido"
    if not await buffer.adquire_lock(redis, conv_id, token, config().lock_ttl_segundos):
        await redis.enqueue_job(
            "processar_turno", cliente_id, conversa_id, token, _defer_by=REENFILEIRA_EM_SEGUNDOS
        )
        return "ocupado"

    try:
        return await _turno(cid, conv_id)
    finally:
        await buffer.libera_lock(redis, conv_id, token)


async def _turno(cliente_id: uuid.UUID, conversa_id: uuid.UUID) -> str:
    async with fabrica_sessao()() as s:
        conversa = await repo.obter_conversa(s, cliente_id, conversa_id)
        if conversa is None:
            return "sem_conversa"
        agente = await agentes_repo.obter(s, cliente_id, conversa.agente_id)
        if agente is None or not agente.ativo:
            return "agente_inativo"

        canal = obter_canal(agente.canal)
        credenciais = agentes_servico.credenciais(agente)
        if not await canal.agente_pode_falar(credenciais, conversa.id_externo):
            return "humano_conduz"

        mensagens = await repo.ultimas_mensagens(s, cliente_id, conversa_id)
        anteriores, pendentes = separa_pendentes(mensagens)
        if not pendentes:
            return "nada_pendente"

        await _digitando(canal, credenciais, conversa.id_externo, True)
        # Grava a leitura antes do modelo: se a resposta falhar, a mídia não é lida de novo.
        await midia.processa_pendentes(s, agente, canal, credenciais, conversa_id, pendentes)
        await s.commit()
        inicio = time.monotonic()
        try:
            resultado = await _roda_com_tentativas(agente, anteriores, pendentes)
        except Exception as erro:
            await _digitando(canal, credenciais, conversa.id_externo, False)
            await grava_turno(
                s,
                Turno(
                    cliente_id=cliente_id,
                    conversa_id=conversa_id,
                    modelo=agente.modelo_conversa,
                    latencia_ms=int((time.monotonic() - inicio) * 1000),
                    erro=repr(erro)[:2000],
                ),
            )
            await s.commit()
            await registra_falha("turno_modelo_falhou", {"erro": repr(erro)[:500]}, cliente_id, agente.id)
            return "falhou"

        latencia = int((time.monotonic() - inicio) * 1000)
        enviadas = 0
        for texto in limita_mensagens(resultado.mensagens, agente.max_mensagens_por_resposta):
            await _digitando(canal, credenciais, conversa.id_externo, True)
            await asyncio.sleep(delay_ms(texto) / 1000)
            try:
                id_externo = await canal.enviar_texto(credenciais, conversa.id_externo, texto)
            except Exception as erro:
                await registra_falha("envio_falhou", {"erro": repr(erro)[:500]}, cliente_id, agente.id)
                break
            await repo.grava_mensagem(
                s,
                Mensagem(
                    cliente_id=cliente_id,
                    conversa_id=conversa_id,
                    direcao="saida",
                    autor="agente",
                    texto=texto,
                    id_externo=id_externo,
                ),
            )
            enviadas += 1
        await _digitando(canal, credenciais, conversa.id_externo, False)

        await grava_turno(
            s,
            Turno(
                cliente_id=cliente_id,
                conversa_id=conversa_id,
                modelo=agente.modelo_conversa,
                tokens_entrada=resultado.tokens_entrada,
                tokens_saida=resultado.tokens_saida,
                custo_estimado=resultado.custo_estimado,
                latencia_ms=latencia,
                tools_chamadas=resultado.tools_chamadas or None,
            ),
        )
        await s.commit()
        log.info("turno_concluido", mensagens=enviadas, latencia_ms=latencia)
        return "respondido"


async def _digitando(canal: Any, credenciais: dict[str, Any], conversa: str, ligado: bool) -> None:
    """Digitando é cosmético: falha aqui nunca derruba o turno."""
    try:
        await canal.digitando(credenciais, conversa, ligado)
    except Exception as erro:
        log.debug("digitando_falhou", erro=repr(erro))
