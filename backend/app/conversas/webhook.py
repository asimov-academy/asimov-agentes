"""Entrada dos canais: valida, grava a mensagem, agenda o buffer e responde rápido.

Nada de IA aqui. O `cliente_id` sai do token da URL, nunca do corpo.
"""

import json
import uuid
from dataclasses import asdict
from typing import Any

import structlog
from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.agentes import repo as agentes_repo
from app.agentes import servico as agentes_servico
from app.canais.base import Acao, EntradaWebhook, Evento
from app.canais.registro import CANAIS, obter_canal
from app.consumo.repo import registra_falha
from app.conversas import buffer, repo
from app.conversas.modelos import Mensagem
from app.handoff import servico as handoff
from app.plataforma.banco import sessao
from app.plataforma.cripto import hash_token
from app.plataforma.textos import mesmo_telefone

log = structlog.get_logger()
router = APIRouter()


def _recusa(canal_pune_erro: bool, status: int) -> Response:
    return Response(status_code=200 if canal_pune_erro else status)


def _mensagens(evento: Evento, cliente_id: uuid.UUID, conversa_id: uuid.UUID) -> list[Mensagem]:
    """Uma mensagem por anexo; o texto vai na primeira. O anexo só é baixado no turno."""
    anexos = evento.anexos or (None,)
    mensagens = []
    for i, anexo in enumerate(anexos):
        id_externo = evento.mensagem_externa
        if i and id_externo is not None:
            id_externo = f"{id_externo}:{i}"
        mensagens.append(
            Mensagem(
                cliente_id=cliente_id,
                conversa_id=conversa_id,
                direcao=evento.direcao,
                autor=evento.autor,
                tipo=anexo.tipo if anexo else "texto",
                texto=evento.texto if i == 0 else None,
                anexo=asdict(anexo) if anexo else None,
                id_externo=id_externo,
            )
        )
    return mensagens


@router.post("/webhook/{canal}/{token}")
async def receber(
    canal: str, token: str, request: Request, s: AsyncSession = Depends(sessao)
) -> Response:
    if canal not in CANAIS:
        return Response(status_code=404)
    canal_obj = obter_canal(canal)
    pune = canal_obj.responde_200_em_assinatura_invalida

    agente = await agentes_repo.ativo_por_token(s, hash_token(token))
    if agente is None or agente.canal != canal:
        await registra_falha("webhook_token_desconhecido", {"canal": canal})
        return _recusa(pune, 404)

    structlog.contextvars.bind_contextvars(
        cliente_id=str(agente.cliente_id), agente_id=str(agente.id)
    )
    credenciais = agentes_servico.credenciais(agente)
    corpo = await request.body()
    entrada = EntradaWebhook(corpo=corpo, cabecalhos={k.lower(): v for k, v in request.headers.items()})

    if not canal_obj.verificar(entrada, credenciais):
        await registra_falha(
            "webhook_assinatura_invalida", {"canal": canal}, agente.cliente_id, agente.id
        )
        return _recusa(pune, 401)

    try:
        payload: dict[str, Any] = json.loads(corpo)
    except ValueError:
        await registra_falha("webhook_json_invalido", {}, agente.cliente_id, agente.id)
        return _recusa(pune, 400)

    evento = canal_obj.interpretar(payload, credenciais, agente.handoff_destino)
    if evento.acao is Acao.IGNORAR:
        # Info de propósito: evento ignorado sem motivo visível é o que mais atrasa o debug de canal novo.
        log.info("webhook_ignorado", motivo=evento.motivo)
        return Response(status_code=200)

    if evento.acao is Acao.RETOMAR_POR_CODIGO:
        assert evento.codigo is not None
        return await _retoma_por_codigo(s, agente, evento.codigo)

    if not _contato_permitido(agente, evento):
        # Agente em teste: só os números da lista são atendidos, o resto nem vira conversa.
        log.info("webhook_ignorado", motivo="contato fora da lista do agente")
        return Response(status_code=200)

    assert evento.conversa_externa is not None
    if evento.acao is Acao.RETOMAR:
        return await _retoma(s, agente.cliente_id, agente.id, agente.canal, evento.conversa_externa)

    try:
        if evento.autor == "contato":
            assert evento.contato_externo is not None
            contato = await repo.contato_do_canal(
                s,
                agente.cliente_id,
                agente.id,
                evento.contato_externo,
                evento.contato_nome,
                evento.contato_telefone,
            )
            conversa = await repo.conversa_do_canal(
                s, agente.cliente_id, agente.id, contato.id, evento.conversa_externa, agente.canal
            )
        else:
            conversa = await repo.conversa_por_externo(
                s, agente.cliente_id, agente.id, evento.conversa_externa
            )
            if conversa is None:
                return Response(status_code=200)

        nova = False
        for mensagem in _mensagens(evento, agente.cliente_id, conversa.id):
            nova = await repo.grava_mensagem(s, mensagem) or nova
        await s.commit()
    except Exception as erro:
        log.error("webhook_gravacao_falhou", erro=repr(erro))
        return Response(status_code=500)

    if not nova:
        log.info("webhook_reentrega_ignorada")
        return Response(status_code=200)

    if evento.acao is Acao.PROCESSAR:
        fila = getattr(request.app.state, "fila", None)
        try:
            if fila is None:
                raise RuntimeError("fila indisponível")
            await buffer.agenda_turno(fila, agente.cliente_id, conversa.id, agente.buffer_segundos)
        except Exception as erro:
            # 500 de propósito: o canal repete e, persistindo, a conversa vai para humano.
            log.error("webhook_agendamento_falhou", erro=repr(erro))
            return Response(status_code=500)

    log.info("webhook_aceito", acao=str(evento.acao), motivo=evento.motivo)
    return Response(status_code=200)


def _contato_permitido(agente: Any, evento: Evento) -> bool:
    """Lista vazia (o normal) atende qualquer pessoa. Só vale para mensagem de contato.

    Devolução da conversa (pelo atendente ou pelo `/retomar` de quem recebeu o handoff) passa
    sempre: quem recebe o handoff não precisa estar na lista de quem conversa com o agente.
    """
    permitidos = agente.contatos_permitidos or []
    if not permitidos or evento.autor != "contato":
        return True
    if evento.acao in (Acao.RETOMAR, Acao.RETOMAR_POR_CODIGO):
        return True
    do_canal = evento.contato_telefone or evento.contato_externo or ""
    return any(mesmo_telefone(p, do_canal) for p in permitidos)


async def _retoma_por_codigo(s: AsyncSession, agente: Any, codigo: str) -> Response:
    """Canais diretos: quem recebeu o handoff mandou `/retomar <código>` na conversa dele.

    Código que não existe (ou de um handoff já fechado) responde 200 sem fazer nada: o destino
    recebe o aviso de que não deu certo, e nada quebra.
    """
    try:
        avisado = await handoff.retomar_por_codigo(s, agente, codigo)
    except Exception as erro:
        log.error("retomada_por_codigo_falhou", erro=repr(erro))
        return Response(status_code=500)
    log.info("webhook_aceito", acao="retomar_por_codigo", motivo="comando do destino", achou=avisado)
    return Response(status_code=200)


async def _retoma(
    s: AsyncSession, cliente_id: uuid.UUID, agente_id: uuid.UUID, canal: str, conversa_externa: str
) -> Response:
    """Idempotente: o Chatwoot manda a mesma devolução em dois eventos."""
    try:
        conversa = await repo.conversa_por_externo(s, cliente_id, agente_id, conversa_externa)
        if conversa is not None:
            structlog.contextvars.bind_contextvars(conversa_id=str(conversa.id))
            await handoff.retomar(s, cliente_id, conversa.id, canal)
            await s.commit()
    except Exception as erro:
        log.error("webhook_retomada_falhou", erro=repr(erro))
        return Response(status_code=500)
    return Response(status_code=200)
