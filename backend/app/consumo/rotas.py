import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.consumo import servico
from app.plataforma.admin import exige_admin
from app.plataforma.banco import sessao

router = APIRouter(prefix="/admin/consumo", dependencies=[Depends(exige_admin)])


class ConsumoAgente(BaseModel):
    cliente_id: uuid.UUID
    cliente: str
    agente_id: uuid.UUID
    agente: str
    turnos: int
    chamadas: int
    tokens_entrada: int
    tokens_saida: int
    custo_estimado: Decimal
    sem_custo: int
    """Chamadas cujo preço o modelo não informou: o custo real é maior que o estimado."""


class FalhaSaida(BaseModel):
    criado_em: datetime
    tipo: str
    detalhe: dict[str, Any]
    cliente_id: uuid.UUID | None
    cliente: str | None
    agente_id: uuid.UUID | None
    agente: str | None


class Relatorio(BaseModel):
    dias: int
    desde: datetime
    agentes: list[ConsumoAgente]
    falhas: list[FalhaSaida]


@router.get("", response_model=Relatorio)
async def ver(
    dias: int = Query(default=7, ge=1, le=365),
    cliente_id: uuid.UUID | None = Query(default=None),
    agente_id: uuid.UUID | None = Query(default=None),
    s: AsyncSession = Depends(sessao),
) -> Relatorio:
    if agente_id is not None and cliente_id is None:
        raise HTTPException(status_code=422, detail="para filtrar por agente, informe também cliente_id")
    try:
        return Relatorio.model_validate(await servico.relatorio(s, dias, cliente_id, agente_id))
    except servico.NaoEncontrado as erro:
        raise HTTPException(status_code=404, detail=str(erro)) from erro
