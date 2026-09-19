"""Rotas de administração da base de conhecimento. O menu do terminal é o cliente delas.

A rota só recebe e valida: quem grava, enfileira e busca é `servico.py`.
"""

import uuid
from typing import Any

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.conhecimento import embeddings, repo, servico
from app.conhecimento.extracao import NaoDeuParaLer
from app.plataforma.banco import sessao
from app.plataforma.admin import exige_admin

router = APIRouter(prefix="/admin", tags=["conhecimento"], dependencies=[Depends(exige_admin)])

DE_NEGOCIO = (servico.NaoEncontrado, servico.Conflito, servico.CampoInvalido, NaoDeuParaLer, embeddings.SemEmbeddings)


def _erro(erro: Exception) -> HTTPException:
    if isinstance(erro, servico.NaoEncontrado):
        return HTTPException(status_code=404, detail=str(erro))
    if isinstance(erro, servico.Conflito):
        return HTTPException(status_code=409, detail=str(erro))
    return HTTPException(status_code=422, detail=str(erro))


def saida(documento: Any) -> dict[str, Any]:
    return {
        "id": str(documento.id),
        "nome": documento.nome_arquivo,
        "origem": documento.origem,
        "status": documento.status,
        "erro": documento.erro,
        "total_trechos": documento.total_trechos,
        "criado_em": documento.criado_em.isoformat(),
    }


class TextoDaBase(BaseModel):
    texto: str = Field(min_length=3, max_length=20000)
    titulo: str = Field(default="", max_length=200)


class SiteDaBase(BaseModel):
    url: str = Field(min_length=8, max_length=500)


@router.get("/clientes/{cliente_id}/agentes/{agente_id}/documentos")
async def lista(
    cliente_id: uuid.UUID, agente_id: uuid.UUID, s: AsyncSession = Depends(sessao)
) -> list[dict[str, Any]]:
    return [saida(d) for d in await repo.listar(s, cliente_id, agente_id)]


@router.post("/clientes/{cliente_id}/agentes/{agente_id}/documentos", status_code=201)
async def envia(
    cliente_id: uuid.UUID,
    agente_id: uuid.UUID,
    request: Request,
    arquivo: UploadFile = File(...),
    s: AsyncSession = Depends(sessao),
) -> dict[str, Any]:
    conteudo = await arquivo.read()
    try:
        documento = await servico.recebe_arquivo(
            s,
            cliente_id,
            agente_id,
            arquivo.filename or "material",
            conteudo,
            arquivo.content_type or "application/octet-stream",
            getattr(request.app.state, "fila", None),
        )
    except DE_NEGOCIO as erro:
        raise _erro(erro) from erro
    return saida(documento)


@router.post("/clientes/{cliente_id}/agentes/{agente_id}/documentos/texto", status_code=201)
async def envia_texto(
    cliente_id: uuid.UUID,
    agente_id: uuid.UUID,
    dados: TextoDaBase,
    request: Request,
    s: AsyncSession = Depends(sessao),
) -> dict[str, Any]:
    try:
        documento = await servico.recebe_texto(
            s, cliente_id, agente_id, dados.texto, dados.titulo, getattr(request.app.state, "fila", None)
        )
    except DE_NEGOCIO as erro:
        raise _erro(erro) from erro
    return saida(documento)


@router.post("/clientes/{cliente_id}/agentes/{agente_id}/documentos/site", status_code=201)
async def envia_site(
    cliente_id: uuid.UUID,
    agente_id: uuid.UUID,
    dados: SiteDaBase,
    request: Request,
    s: AsyncSession = Depends(sessao),
) -> dict[str, Any]:
    try:
        documento = await servico.recebe_site(
            s, cliente_id, agente_id, dados.url, getattr(request.app.state, "fila", None)
        )
    except DE_NEGOCIO as erro:
        raise _erro(erro) from erro
    return saida(documento)


@router.delete("/clientes/{cliente_id}/agentes/{agente_id}/documentos/{documento_id}")
async def remove(
    cliente_id: uuid.UUID,
    agente_id: uuid.UUID,
    documento_id: uuid.UUID,
    s: AsyncSession = Depends(sessao),
) -> dict[str, bool]:
    try:
        await servico.remover(s, cliente_id, agente_id, documento_id)
    except DE_NEGOCIO as erro:
        raise _erro(erro) from erro
    return {"removido": True}
