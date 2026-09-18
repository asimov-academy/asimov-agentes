"""Job do worker: um turno depois do buffer.

Ordem: token do buffer ainda vale, lock da conversa, canal ainda deixa o agente falar,
leitura das mídias pendentes, modelo, envio mensagem a mensagem com digitando, registro do Turno.

Mensagem nova do contato antes do envio descarta a resposta: o turno dela responde tudo junto.
Depois que o envio começou, o que chegar é respondido no turno seguinte.

Handoff acontece no fim, depois do envio: pedido pelo modelo, por arquivo grande demais ou por
falha do modelo depois das tentativas (aí com mensagem fixa de expectativa).
"""

import asyncio
import time
import uuid
from collections.abc import Awaitable, Callable
from datetime import datetime
from typing import Any

import structlog
from pydantic_ai.exceptions import UsageLimitExceeded

from app.agentes import repo as agentes_repo
from app.agentes import servico as agentes_servico
from app.consumo.modelos import Turno
from app.consumo.repo import grava_turno, registra_falha
from app.conversas import buffer, repo
from app.conversas.divisao import limita_mensagens, tempos_de_digitacao
from app.conversas.modelos import Conversa, Mensagem
from app.handoff import repo as handoff_repo
from app.handoff import servico as handoff
from app.ia.agente import ResultadoTurno, roda_turno
from app.midia import servico as midia
from app.plataforma.banco import fabrica_sessao
from app.plataforma.config import config

log = structlog.get_logger()

REENFILEIRA_EM_SEGUNDOS = 5
_espera = asyncio.sleep


def separa_pendentes(
    mensagens: list[Mensagem], respondido_ate: datetime | None
) -> tuple[list[Mensagem], list[Mensagem]]:
    """Pendentes são as falas do contato ainda não respondidas por um turno.

    Não basta "depois da última resposta do agente": a resposta é gravada no fim do turno, e o
    que o contato mandou durante o turno ficaria antes dela, sem resposta nunca. Fala de atendente
    humano encerra as pendências anteriores. Conversa sem `respondido_ate` (anterior à v0.3.2)
    usa a regra antiga.
    """
    pendentes: list[Mensagem] = []
    for m in mensagens:
        if m.autor == "contato":
            if respondido_ate is None or m.criado_em > respondido_ate:
                pendentes.append(m)
        elif m.autor == "humano" or respondido_ate is None:
            pendentes = []
    ids = {m.id for m in pendentes}
    return [m for m in mensagens if m.id not in ids], pendentes


async def _roda_com_tentativas(
    agente: Any, anteriores: list[Mensagem], pendentes: list[Mensagem], handoffs: list[Any]
) -> ResultadoTurno:
    tentativas = config().tentativas_extra_modelo + 1
    for tentativa in range(1, tentativas + 1):
        try:
            return await roda_turno(agente, anteriores, pendentes, handoffs=handoffs)
        except Exception as erro:
            log.warning("modelo_falhou", tentativa=tentativa, erro=repr(erro))
            # Estourar o teto do turno é o modelo em loop: tentar de novo só repete o gasto.
            if tentativa == tentativas or isinstance(erro, UsageLimitExceeded):
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
        return await _turno(cid, conv_id, lambda: buffer.token_ainda_vale(redis, conv_id, token))
    finally:
        await buffer.libera_lock(redis, conv_id, token)


async def _turno(
    cliente_id: uuid.UUID, conversa_id: uuid.UUID, sem_mensagem_nova: Callable[[], Awaitable[bool]]
) -> str:
    comeco = time.monotonic()
    async with fabrica_sessao()() as s:
        conversa = await repo.obter_conversa(s, cliente_id, conversa_id)
        if conversa is None:
            return "sem_conversa"
        agente = await agentes_repo.obter(s, cliente_id, conversa.agente_id)
        if agente is None or not agente.ativo:
            return "agente_inativo"

        canal, credenciais = agentes_servico.canal_da_conversa(agente, conversa)
        if not await canal.agente_pode_falar(credenciais, conversa.id_externo, conversa.status):
            return "humano_conduz"
        # O canal diz que o agente conduz: handoff ainda aberto é devolução que não chegou.
        if conversa.status == "humano" and await handoff.retomar(
            s, cliente_id, conversa_id, conversa.canal
        ):
            await s.commit()

        mensagens = await repo.ultimas_mensagens(s, cliente_id, conversa_id)
        anteriores, pendentes = separa_pendentes(mensagens, conversa.respondido_ate)
        if not pendentes:
            return "nada_pendente"

        ultima = _ultima_recebida(pendentes)
        await _digitando(canal, credenciais, conversa.id_externo, True, ultima)
        # Grava a leitura antes do modelo: se a resposta falhar, a mídia não é lida de novo.
        await midia.processa_pendentes(s, agente, canal, credenciais, conversa_id, pendentes)
        await s.commit()
        if not await sem_mensagem_nova():
            await _digitando(canal, credenciais, conversa.id_externo, False, ultima)
            return "substituido"
        inicio = time.monotonic()
        try:
            resultado = await _roda_com_tentativas(
                agente, anteriores, pendentes, await handoff_repo.da_conversa(s, cliente_id, conversa_id)
            )
        except Exception as erro:
            await _digitando(canal, credenciais, conversa.id_externo, False, ultima)
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
            await _envia(
                s, canal, credenciais, agente, conversa, [handoff.MENSAGEM_DE_EXPECTATIVA], comeco, ultima
            )
            await repo.marca_respondido(s, cliente_id, conversa_id, max(m.criado_em for m in pendentes))
            await handoff.transferir(s, agente, canal, credenciais, conversa, handoff.MOTIVO_FALHA_NO_TURNO)
            await s.commit()
            return "falhou"

        latencia = int((time.monotonic() - inicio) * 1000)
        if not await sem_mensagem_nova():
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
                    erro="descartada: contato mandou mensagem nova antes do envio",
                ),
            )
            await s.commit()
            await _digitando(canal, credenciais, conversa.id_externo, False, ultima)
            log.info("resposta_descartada")
            return "substituido"
        enviadas = await _envia(
            s,
            canal,
            credenciais,
            agente,
            conversa,
            limita_mensagens(resultado.mensagens, agente.max_mensagens_por_resposta),
            comeco,
            ultima,
        )
        await repo.marca_respondido(s, cliente_id, conversa_id, max(m.criado_em for m in pendentes))

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
        if resultado.correcoes:
            await registra_falha(
                "resposta_corrigida", {"avisos": resultado.correcoes}, cliente_id, agente.id
            )
        motivo = resultado.motivo_handoff or _motivo_por_midia(pendentes)
        transferencia = None
        if motivo is not None:
            transferencia = await handoff.transferir(s, agente, canal, credenciais, conversa, motivo)
        await s.commit()
        log.info("turno_concluido", mensagens=enviadas, latencia_ms=latencia, handoff=transferencia)
        return "transferido" if transferencia == "transferido" else "respondido"


def _motivo_por_midia(pendentes: list[Mensagem]) -> str | None:
    """Arquivo acima do limite vai para humano mesmo que o modelo não tenha pedido."""
    if any((m.anexo or {}).get("situacao") == "acima_do_limite" for m in pendentes):
        return handoff.MOTIVO_ARQUIVO_GRANDE
    return None


async def _envia(
    s: Any,
    canal: Any,
    credenciais: dict[str, Any],
    agente: Any,
    conversa: Conversa,
    textos: list[str],
    comeco: float,
    ultima_recebida: str | None = None,
) -> int:
    """Envia na ordem com digitando antes de cada uma; para na primeira que falhar.

    O digitando dura o tempo de uma pessoa digitar a mensagem (`tempos_de_digitacao`).
    """
    tempos = tempos_de_digitacao(
        textos,
        agente.digitacao_caracteres_por_segundo,
        agente.digitacao_maximo_segundos,
        ja_passou_segundos=time.monotonic() - comeco,
        total_maximo_segundos=config().digitacao_total_maximo_segundos,
    )
    enviadas = 0
    for texto, segundos in zip(textos, tempos, strict=True):
        await _digitando(canal, credenciais, conversa.id_externo, True, ultima_recebida)
        await asyncio.sleep(segundos)
        try:
            id_externo = await canal.enviar_texto(credenciais, conversa.id_externo, texto)
        except Exception as erro:
            await registra_falha("envio_falhou", {"erro": repr(erro)[:500]}, agente.cliente_id, agente.id)
            break
        await repo.grava_mensagem(
            s,
            Mensagem(
                cliente_id=agente.cliente_id,
                conversa_id=conversa.id,
                direcao="saida",
                autor="agente",
                texto=texto,
                id_externo=id_externo,
            ),
        )
        enviadas += 1
    await _digitando(canal, credenciais, conversa.id_externo, False, ultima_recebida)
    return enviadas


def _ultima_recebida(pendentes: list[Mensagem]) -> str | None:
    """Id da última mensagem que chegou, no canal: a Cloud API prende o digitando a ela.

    O sufixo `:1` que a gravação põe nos anexos extras não existe no canal, e sai aqui.
    """
    for mensagem in reversed(pendentes):
        if mensagem.direcao == "entrada" and mensagem.id_externo:
            return mensagem.id_externo.split(":")[0]
    return None


async def _digitando(
    canal: Any,
    credenciais: dict[str, Any],
    conversa: str,
    ligado: bool,
    ultima_recebida: str | None = None,
) -> None:
    """Digitando é cosmético: falha aqui nunca derruba o turno."""
    try:
        await canal.digitando(credenciais, conversa, ligado, ultima_recebida)
    except Exception as erro:
        log.debug("digitando_falhou", erro=repr(erro))
