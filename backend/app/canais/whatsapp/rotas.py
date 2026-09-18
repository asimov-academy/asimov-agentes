"""Consultas do setup ao WhatsApp oficial: situação do número e templates aprovados.

Só o setup chama (rotas `/admin`, fora do Caddy). As credenciais são as do agente, guardadas
cifradas: o token de acesso e o segredo do app nunca saem daqui.
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.agentes import repo as agentes_repo
from app.agentes import servico as agentes_servico
from app.agentes.modelos import Agente
from app.canais.base import CredencialInvalida
from app.canais.registro import obter_canal
from app.canais.whatsapp import api
from app.canais.whatsapp.canal import PARAMETROS_DO_TEMPLATE
from app.plataforma.admin import exige_admin
from app.plataforma.banco import sessao

router = APIRouter(prefix="/admin", dependencies=[Depends(exige_admin)])


class NumeroSaida(BaseModel):
    phone_number_id: str
    numero: str
    nome: str


class TemplateSaida(BaseModel):
    nome: str
    idioma: str
    situacao: str
    categoria: str
    parametros: int
    serve: bool
    """True quando o template pode levar o aviso de handoff: aprovado e com três parâmetros."""


async def _agente(s: AsyncSession, cliente_id: uuid.UUID, agente_id: uuid.UUID) -> Agente:
    agente = await agentes_repo.obter(s, cliente_id, agente_id)
    if agente is None or not agente.ativo:
        raise HTTPException(status_code=404, detail="agente não encontrado")
    if agente.canal != "whatsapp":
        raise HTTPException(status_code=422, detail="este agente não atende pelo WhatsApp oficial")
    return agente


def _erro_da_meta(erro: CredencialInvalida) -> HTTPException:
    return HTTPException(status_code=502, detail=str(erro))


@router.get("/clientes/{cliente_id}/agentes/{agente_id}/whatsapp", response_model=NumeroSaida)
async def numero(
    cliente_id: uuid.UUID, agente_id: uuid.UUID, s: AsyncSession = Depends(sessao)
) -> NumeroSaida:
    """Confere na Meta que o número segue de pé e que o token ainda vale."""
    credenciais = agentes_servico.credenciais(await _agente(s, cliente_id, agente_id))
    try:
        ficha = await api.numero(credenciais["access_token"], credenciais["phone_number_id"])
    except CredencialInvalida as erro:
        raise _erro_da_meta(erro) from erro
    return NumeroSaida(
        phone_number_id=str(credenciais["phone_number_id"]),
        numero=ficha["numero"],
        nome=ficha["nome"],
    )


@router.post("/clientes/{cliente_id}/agentes/{agente_id}/whatsapp/webhook", status_code=204)
async def refazer_webhook(
    cliente_id: uuid.UUID, agente_id: uuid.UUID, s: AsyncSession = Depends(sessao)
) -> None:
    """Refaz as três camadas de webhook na Meta, com as credenciais que o agente já tem.

    Serve para quando alguém mexeu na configuração do app pelo painel, ou para agente criado por
    uma versão anterior que não ligava o campo `messages`. É idempotente.
    """
    agente = await _agente(s, cliente_id, agente_id)
    credenciais = agentes_servico.credenciais(agente)
    url = agentes_servico.url_webhook(agente)
    try:
        await obter_canal("whatsapp").conectar(credenciais, url, agente.nome)
    except CredencialInvalida as erro:
        raise _erro_da_meta(erro) from erro


@router.get(
    "/clientes/{cliente_id}/agentes/{agente_id}/whatsapp/templates",
    response_model=list[TemplateSaida],
)
async def templates(
    cliente_id: uuid.UUID, agente_id: uuid.UUID, s: AsyncSession = Depends(sessao)
) -> list[TemplateSaida]:
    """Templates da conta, para escolher o que leva o aviso de handoff."""
    credenciais = agentes_servico.credenciais(await _agente(s, cliente_id, agente_id))
    try:
        achados = await api.templates(credenciais["access_token"], credenciais["waba_id"])
    except CredencialInvalida as erro:
        raise _erro_da_meta(erro) from erro
    return [
        TemplateSaida(
            **t,
            serve=t["situacao"] == "APPROVED" and t["parametros"] == PARAMETROS_DO_TEMPLATE,
        )
        for t in achados
    ]
