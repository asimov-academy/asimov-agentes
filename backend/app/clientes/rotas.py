import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.clientes import repo, servico
from app.plataforma.admin import exige_admin
from app.plataforma.banco import sessao

router = APIRouter(prefix="/admin/clientes", dependencies=[Depends(exige_admin)])


class NovoCliente(BaseModel):
    nome: str = Field(min_length=1, max_length=200)


class Remocao(BaseModel):
    confirmacao: str = Field(min_length=1, max_length=200, description="Nome da empresa.")


class ClienteSaida(BaseModel):
    id: uuid.UUID
    nome: str
    slug: str
    ativo: bool


@router.post("", status_code=201, response_model=ClienteSaida)
async def criar(dados: NovoCliente, s: AsyncSession = Depends(sessao)) -> ClienteSaida:
    try:
        cliente = await servico.criar_cliente(s, dados.nome)
    except servico.ClienteJaExiste as erro:
        raise HTTPException(status_code=409, detail=str(erro)) from erro
    except ValueError as erro:
        raise HTTPException(status_code=422, detail=str(erro)) from erro
    return ClienteSaida.model_validate(cliente, from_attributes=True)


@router.get("", response_model=list[ClienteSaida])
async def listar(s: AsyncSession = Depends(sessao)) -> list[ClienteSaida]:
    return [ClienteSaida.model_validate(c, from_attributes=True) for c in await repo.listar(s)]


@router.delete("/{cliente_id}", status_code=204)
async def remover(cliente_id: uuid.UUID, dados: Remocao, s: AsyncSession = Depends(sessao)) -> None:
    try:
        await servico.remover_cliente(s, cliente_id, dados.confirmacao)
    except servico.NaoEncontrado as erro:
        raise HTTPException(status_code=404, detail=str(erro)) from erro
    except servico.ClienteComAgentes as erro:
        raise HTTPException(status_code=409, detail=str(erro)) from erro
    except ValueError as erro:
        raise HTTPException(status_code=422, detail=str(erro)) from erro
