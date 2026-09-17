import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.canais.nativo import servico
from app.plataforma.admin import exige_admin
from app.plataforma.banco import sessao

router = APIRouter(prefix="/admin", dependencies=[Depends(exige_admin)])


class MensagemDoTerminal(BaseModel):
    texto: str = Field(min_length=1, max_length=4000)
    conversa: str | None = Field(default=None, min_length=1, max_length=200, description="Vazio começa outra conversa.")


class EnviadaSaida(BaseModel):
    conversa: str
    conversa_id: uuid.UUID
    agendada: bool


class LeituraSaida(BaseModel):
    mensagens: list[dict[str, Any]]
    proxima: int
    digitando: bool
    respondendo: bool
    turno: dict[str, Any] | None
    handoff: dict[str, Any] | None


@router.post("/clientes/{cliente_id}/agentes/{agente_id}/terminal", response_model=EnviadaSaida)
async def enviar(
    cliente_id: uuid.UUID,
    agente_id: uuid.UUID,
    dados: MensagemDoTerminal,
    request: Request,
    s: AsyncSession = Depends(sessao),
) -> EnviadaSaida:
    texto = dados.texto.strip()
    if not texto:
        raise HTTPException(status_code=422, detail="mensagem vazia")
    try:
        enviada = await servico.enviar(s, request.app.state.fila, cliente_id, agente_id, texto, dados.conversa)
    except servico.NaoEncontrado as erro:
        raise HTTPException(status_code=404, detail=str(erro)) from erro
    return EnviadaSaida(conversa=enviada.conversa, conversa_id=enviada.conversa_id, agendada=enviada.agendada)


@router.get("/clientes/{cliente_id}/agentes/{agente_id}/terminal/{conversa}", response_model=LeituraSaida)
async def ler(
    cliente_id: uuid.UUID,
    agente_id: uuid.UUID,
    conversa: str,
    depois: int = Query(default=0, ge=0, description="Quantas mensagens do agente o terminal já mostrou."),
    s: AsyncSession = Depends(sessao),
) -> LeituraSaida:
    try:
        leitura = await servico.ler(s, cliente_id, agente_id, conversa, depois)
    except servico.NaoEncontrado as erro:
        raise HTTPException(status_code=404, detail=str(erro)) from erro
    return LeituraSaida(
        mensagens=leitura.mensagens,
        proxima=leitura.proxima,
        digitando=leitura.digitando,
        respondendo=leitura.respondendo,
        turno=leitura.turno,
        handoff=leitura.handoff,
    )
