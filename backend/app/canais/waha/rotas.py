"""Pareamento do número na WAHA: o setup consulta o status, desenha o QR code e lista os grupos.

Só o setup chama (rotas `/admin`, fora do Caddy). A sessão é a do agente; a chave da WAHA fica na
API e nunca sai.
"""

import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.agentes import repo as agentes_repo
from app.agentes import servico as agentes_servico
from app.agentes.modelos import Agente
from app.canais.base import CredencialInvalida
from app.canais.waha import api, vigia
from app.plataforma.admin import exige_admin
from app.plataforma.banco import sessao

router = APIRouter(prefix="/admin", dependencies=[Depends(exige_admin)])


class SituacaoSaida(BaseModel):
    status: str
    """`STARTING`, `SCAN_QR_CODE`, `WORKING`, `FAILED` ou `STOPPED`, como a WAHA informa."""
    pareado: bool
    numero: str | None
    nome: str | None
    qr: str | None
    """Texto do QR code para o terminal desenhar; só vem em `SCAN_QR_CODE`."""


class GrupoSaida(BaseModel):
    chat_id: str
    nome: str


class Numero(BaseModel):
    telefone: str


class NumeroSaida(BaseModel):
    existe: bool
    chat_id: str | None
    telefone: str | None


@router.post("/canais/waha/manutencao", status_code=204)
async def manutencao(request: Request, s: AsyncSession = Depends(sessao)) -> None:
    """O setup vai mexer no contêiner: sessão parada nos próximos minutos não é número fora do ar.

    Sem isso, atualizar a plataforma ou preparar o nome do aparelho gerava alarme sobre o que o
    próprio operador estava fazendo.
    """
    fila = getattr(request.app.state, "fila", None)
    for agente in await agentes_repo.listar_de_todos_os_clientes(s):
        if agente.canal == "waha" and agente.ativo:
            await vigia.marca_pareamento(fila, agente.id)


@router.get("/canais/waha", response_model=dict)
async def saude() -> dict[str, Any]:
    """Se a WAHA está no ar e em que versão. O setup espera por aqui depois de recriar o contêiner."""
    try:
        return {"no_ar": True, **await api.versao()}
    except CredencialInvalida as erro:
        return {"no_ar": False, "erro": str(erro)}


async def _agente_waha(s: AsyncSession, cliente_id: uuid.UUID, agente_id: uuid.UUID) -> Agente:
    agente = await agentes_repo.obter(s, cliente_id, agente_id)
    if agente is None or not agente.ativo:
        raise HTTPException(status_code=404, detail="agente não encontrado")
    if agente.canal != "waha":
        raise HTTPException(status_code=422, detail="este agente não atende pela WAHA")
    return agente


def _sessao(agente: Agente) -> str:
    sessao_waha = agentes_servico.credenciais(agente).get("sessao")
    if not sessao_waha:
        raise HTTPException(status_code=422, detail="o agente não tem sessão na WAHA")
    return str(sessao_waha)


def _erro_da_waha(erro: CredencialInvalida) -> HTTPException:
    return HTTPException(status_code=502, detail=str(erro))


@router.get("/clientes/{cliente_id}/agentes/{agente_id}/waha", response_model=SituacaoSaida)
async def situacao(
    cliente_id: uuid.UUID, agente_id: uuid.UUID, s: AsyncSession = Depends(sessao)
) -> SituacaoSaida:
    """Chamada em laço pelo setup enquanto o operador lê o QR code."""
    nome_sessao = _sessao(await _agente_waha(s, cliente_id, agente_id))
    try:
        dados = await api.situacao(nome_sessao)
        qr = await api.qr_code(nome_sessao) if dados.get("status") == api.STATUS_QR else None
    except CredencialInvalida as erro:
        raise _erro_da_waha(erro) from erro
    eu: dict[str, Any] = dados.get("me") or {}
    numero = eu.get("id")
    return SituacaoSaida(
        status=str(dados.get("status")),
        pareado=dados.get("status") == api.STATUS_PAREADO,
        numero=str(numero).split("@")[0] if numero else None,
        nome=eu.get("pushName"),
        qr=qr,
    )


@router.post("/clientes/{cliente_id}/agentes/{agente_id}/waha/reiniciar", response_model=SituacaoSaida)
async def reiniciar(
    cliente_id: uuid.UUID, agente_id: uuid.UUID, request: Request, s: AsyncSession = Depends(sessao)
) -> SituacaoSaida:
    """Depois de FAILED ou de o QR code expirar: para e inicia a sessão para vir um QR novo."""
    agente = await _agente_waha(s, cliente_id, agente_id)
    nome_sessao = _sessao(agente)
    # A sessão vai passar por STOPPED até o QR ser lido: isso não é número fora do ar.
    await vigia.marca_pareamento(getattr(request.app.state, "fila", None), agente.id)
    try:
        await api.para_sessao(nome_sessao)
        await api.inicia_sessao(nome_sessao)
    except CredencialInvalida as erro:
        raise _erro_da_waha(erro) from erro
    return await situacao(cliente_id, agente_id, s)


@router.post("/clientes/{cliente_id}/agentes/{agente_id}/waha/webhook", status_code=204)
async def reconfigurar_webhook(
    cliente_id: uuid.UUID, agente_id: uuid.UUID, s: AsyncSession = Depends(sessao)
) -> None:
    """Põe na sessão a lista de eventos de hoje, para sessão criada por uma versão anterior.

    Chamado pelo setup em `asimov atualizar`. A URL e a chave são as que o agente já tem.
    """
    agente = await _agente_waha(s, cliente_id, agente_id)
    credenciais = agentes_servico.credenciais(agente)
    try:
        await api.atualiza_webhook(
            _sessao(agente), agentes_servico.url_webhook(agente), credenciais.get("hmac_key", "")
        )
    except CredencialInvalida as erro:
        raise _erro_da_waha(erro) from erro


@router.post("/clientes/{cliente_id}/agentes/{agente_id}/waha/numero", response_model=NumeroSaida)
async def conferir_numero(
    cliente_id: uuid.UUID, agente_id: uuid.UUID, dados: Numero, s: AsyncSession = Depends(sessao)
) -> NumeroSaida:
    """O WhatsApp diz se o número existe e qual é o id dele, que é para onde a mensagem vai.

    O mesmo celular circula com e sem o nono dígito e hoje pode ser um `@lid`: guardar o id errado
    faz o aviso de handoff não chegar em ninguém.
    """
    nome_sessao = _sessao(await _agente_waha(s, cliente_id, agente_id))
    try:
        return NumeroSaida(**await api.confere_numero(nome_sessao, dados.telefone))
    except CredencialInvalida as erro:
        raise _erro_da_waha(erro) from erro


@router.get("/clientes/{cliente_id}/agentes/{agente_id}/waha/grupos", response_model=list[GrupoSaida])
async def grupos(
    cliente_id: uuid.UUID, agente_id: uuid.UUID, s: AsyncSession = Depends(sessao)
) -> list[GrupoSaida]:
    """Grupos do número pareado, para escolher quem recebe o handoff."""
    nome_sessao = _sessao(await _agente_waha(s, cliente_id, agente_id))
    try:
        return [GrupoSaida(**g) for g in await api.grupos(nome_sessao)]
    except CredencialInvalida as erro:
        raise _erro_da_waha(erro) from erro
