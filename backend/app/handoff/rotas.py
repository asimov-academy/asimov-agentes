import uuid

import structlog
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.handoff import servico
from app.plataforma.admin import exige_admin
from app.plataforma.banco import sessao

log = structlog.get_logger()
router = APIRouter(prefix="/admin", dependencies=[Depends(exige_admin)])


class RetomadaSaida(BaseModel):
    retomado: bool
    """False quando a conversa não tinha handoff aberto (a devolução no canal acontece mesmo assim)."""


@router.post("/clientes/{cliente_id}/conversas/{conversa_id}/retomar", response_model=RetomadaSaida)
async def retomar(
    cliente_id: uuid.UUID, conversa_id: uuid.UUID, s: AsyncSession = Depends(sessao)
) -> RetomadaSaida:
    try:
        return RetomadaSaida(retomado=await servico.retomar_pelo_operador(s, cliente_id, conversa_id))
    except servico.ConversaNaoEncontrada as erro:
        raise HTTPException(status_code=404, detail=str(erro)) from erro
    except Exception as erro:
        log.error("retomada_no_canal_falhou", erro=repr(erro)[:500])
        raise HTTPException(status_code=502, detail="o canal recusou devolver a conversa ao agente") from erro
