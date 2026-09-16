"""Entrada dos canais: valida, grava a mensagem, agenda o buffer e responde rápido.

Nada de IA aqui. O `cliente_id` sai do token da URL, nunca do corpo.
"""

import json
from typing import Any

import structlog
from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.agentes import repo as agentes_repo
from app.agentes import servico as agentes_servico
from app.canais.base import Acao, EntradaWebhook
from app.canais.registro import CANAIS, obter_canal
from app.consumo.repo import registra_falha
from app.conversas import buffer, repo
from app.conversas.modelos import Mensagem
from app.plataforma.banco import sessao
from app.plataforma.cripto import hash_token

log = structlog.get_logger()
router = APIRouter()


def _recusa(canal_pune_erro: bool, status: int) -> Response:
    return Response(status_code=200 if canal_pune_erro else status)


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

    evento = canal_obj.interpretar(payload, credenciais)
    if evento.acao is Acao.IGNORAR:
        log.debug("webhook_ignorado", motivo=evento.motivo)
        return Response(status_code=200)

    assert evento.conversa_externa is not None
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
                s, agente.cliente_id, agente.id, contato.id, evento.conversa_externa
            )
        else:
            conversa = await repo.conversa_por_externo(
                s, agente.cliente_id, agente.id, evento.conversa_externa
            )
            if conversa is None:
                return Response(status_code=200)

        nova = await repo.grava_mensagem(
            s,
            Mensagem(
                cliente_id=agente.cliente_id,
                conversa_id=conversa.id,
                direcao=evento.direcao,
                autor=evento.autor,
                tipo=evento.tipo,
                texto=evento.texto,
                id_externo=evento.mensagem_externa,
            ),
        )
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
