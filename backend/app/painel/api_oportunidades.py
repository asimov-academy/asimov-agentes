"""Rotas do funil no painel: o quadro, as colunas, os cartões e as etiquetas.

Mesma fronteira do resto do painel: nada de `/admin`, nenhuma regra de negócio aqui. Tudo chama
`oportunidades/servico.py`. O `cliente_id` vem da URL e é conferido no banco antes de virar filtro,
como manda o AGENTS.md; nunca do corpo da requisição.
"""

import uuid
from decimal import Decimal
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.clientes import repo as clientes_repo
from app.oportunidades import servico
from app.painel.acesso import exige_csrf, exige_sessao
from app.plataforma.banco import sessao

router = APIRouter(
    prefix="/api/empresas/{cliente_id}/funil",
    include_in_schema=False,
    dependencies=[Depends(exige_sessao), Depends(exige_csrf)],
)

DE_NEGOCIO = (servico.NaoEncontrado, servico.CampoInvalido, servico.Conflito)


def _erro(problema: Exception) -> HTTPException:
    if isinstance(problema, servico.NaoEncontrado):
        return HTTPException(status_code=404, detail=str(problema))
    if isinstance(problema, servico.Conflito):
        return HTTPException(status_code=409, detail=str(problema))
    return HTTPException(status_code=422, detail=str(problema))


async def _empresa(s: AsyncSession, cliente_id: uuid.UUID) -> uuid.UUID:
    """Confere a empresa no banco antes de usá-la como filtro."""
    if await clientes_repo.obter(s, cliente_id) is None:
        raise HTTPException(status_code=404, detail="empresa não encontrada")
    return cliente_id


class NovaEtapa(BaseModel):
    nome: str = Field(min_length=1, max_length=60)


class NovaEtiqueta(BaseModel):
    nome: str = Field(min_length=1, max_length=40)
    cor: str = Field(default="ciano", max_length=20)


class NovaOportunidade(BaseModel):
    titulo: str = Field(min_length=1, max_length=200)
    etapa_id: uuid.UUID | None = None
    contato_id: uuid.UUID | None = None
    valor: Decimal = Decimal("0")
    nota: str = Field(default="", max_length=4000)
    etiquetas: list[uuid.UUID] = Field(default_factory=list)


class EdicaoDaOportunidade(BaseModel):
    titulo: str | None = Field(default=None, max_length=200)
    etapa_id: uuid.UUID | None = None
    contato_id: uuid.UUID | None = None
    valor: Decimal | None = None
    nota: str | None = Field(default=None, max_length=4000)
    ordem: int | None = None
    etiquetas: list[uuid.UUID] | None = None


@router.get("")
async def quadro(cliente_id: uuid.UUID, s: AsyncSession = Depends(sessao)) -> dict[str, Any]:
    """O kanban inteiro numa chamada: colunas, cartões e etiquetas."""
    return await servico.quadro(s, await _empresa(s, cliente_id))


@router.post("/etapas", status_code=201)
async def cria_etapa(
    cliente_id: uuid.UUID, dados: NovaEtapa, s: AsyncSession = Depends(sessao)
) -> dict[str, Any]:
    try:
        etapa = await servico.cria_etapa(s, await _empresa(s, cliente_id), dados.nome)
    except DE_NEGOCIO as problema:
        raise _erro(problema) from problema
    return {"id": str(etapa.id), "nome": etapa.nome, "ordem": etapa.ordem}


@router.patch("/etapas/{etapa_id}")
async def renomeia_etapa(
    cliente_id: uuid.UUID, etapa_id: uuid.UUID, dados: NovaEtapa, s: AsyncSession = Depends(sessao)
) -> dict[str, Any]:
    try:
        etapa = await servico.renomeia_etapa(s, await _empresa(s, cliente_id), etapa_id, dados.nome)
    except DE_NEGOCIO as problema:
        raise _erro(problema) from problema
    return {"id": str(etapa.id), "nome": etapa.nome}


@router.delete("/etapas/{etapa_id}", status_code=204)
async def apaga_etapa(
    cliente_id: uuid.UUID, etapa_id: uuid.UUID, s: AsyncSession = Depends(sessao)
) -> None:
    try:
        await servico.apaga_etapa(s, await _empresa(s, cliente_id), etapa_id)
    except DE_NEGOCIO as problema:
        raise _erro(problema) from problema


@router.post("/etiquetas", status_code=201)
async def cria_etiqueta(
    cliente_id: uuid.UUID, dados: NovaEtiqueta, s: AsyncSession = Depends(sessao)
) -> dict[str, Any]:
    try:
        etiqueta = await servico.cria_etiqueta(
            s, await _empresa(s, cliente_id), dados.nome, dados.cor
        )
    except DE_NEGOCIO as problema:
        raise _erro(problema) from problema
    return {"id": str(etiqueta.id), "nome": etiqueta.nome, "cor": etiqueta.cor}


@router.delete("/etiquetas/{etiqueta_id}", status_code=204)
async def apaga_etiqueta(
    cliente_id: uuid.UUID, etiqueta_id: uuid.UUID, s: AsyncSession = Depends(sessao)
) -> None:
    try:
        await servico.apaga_etiqueta(s, await _empresa(s, cliente_id), etiqueta_id)
    except DE_NEGOCIO as problema:
        raise _erro(problema) from problema


@router.post("/oportunidades", status_code=201)
async def cria(
    cliente_id: uuid.UUID, dados: NovaOportunidade, s: AsyncSession = Depends(sessao)
) -> dict[str, Any]:
    try:
        oportunidade = await servico.cria(
            s,
            await _empresa(s, cliente_id),
            titulo=dados.titulo,
            etapa_id=dados.etapa_id,
            contato_id=dados.contato_id,
            valor=dados.valor,
            nota=dados.nota,
            etiquetas=dados.etiquetas,
        )
    except DE_NEGOCIO as problema:
        raise _erro(problema) from problema
    return {"id": str(oportunidade.id)}


@router.patch("/oportunidades/{oportunidade_id}")
async def edita(
    cliente_id: uuid.UUID,
    oportunidade_id: uuid.UUID,
    dados: EdicaoDaOportunidade,
    s: AsyncSession = Depends(sessao),
) -> dict[str, Any]:
    campos = dados.model_dump(exclude_unset=True)
    try:
        oportunidade = await servico.edita(
            s, await _empresa(s, cliente_id), oportunidade_id, campos
        )
    except DE_NEGOCIO as problema:
        raise _erro(problema) from problema
    return {"id": str(oportunidade.id), "etapa_id": str(oportunidade.etapa_id)}


@router.delete("/oportunidades/{oportunidade_id}", status_code=204)
async def apaga(
    cliente_id: uuid.UUID, oportunidade_id: uuid.UUID, s: AsyncSession = Depends(sessao)
) -> None:
    try:
        await servico.apaga(s, await _empresa(s, cliente_id), oportunidade_id)
    except DE_NEGOCIO as problema:
        raise _erro(problema) from problema
