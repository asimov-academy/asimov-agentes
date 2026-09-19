"""Base de conhecimento pelo painel: a aba Treinamento da ficha do agente.

Mesma fronteira das outras rotas do painel: sessão do operador, CSRF em escrita e nenhuma regra
nova aqui dentro. Quem grava, enfileira e busca é `conhecimento/servico.py`, o mesmo do terminal.

O `cliente_id` nunca vem do corpo: sai do agente, achado pelo id da URL.
"""

import uuid
from typing import Any

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.agentes.modelos import Agente
from app.conhecimento import embeddings, repo, servico
from app.conhecimento.rotas import saida
from app.painel import repo as painel_repo
from app.painel.acesso import exige_csrf, exige_sessao
from app.plataforma.banco import sessao

router = APIRouter(
    prefix="/api/agentes",
    include_in_schema=False,
    dependencies=[Depends(exige_sessao), Depends(exige_csrf)],
)

DE_NEGOCIO = (
    servico.NaoEncontrado,
    servico.Conflito,
    servico.CampoInvalido,
    embeddings.SemEmbeddings,
)


def _erro(erro: Exception) -> HTTPException:
    if isinstance(erro, servico.NaoEncontrado):
        return HTTPException(status_code=404, detail=str(erro))
    if isinstance(erro, servico.Conflito):
        return HTTPException(status_code=409, detail=str(erro))
    return HTTPException(status_code=422, detail=str(erro))


async def _agente(s: AsyncSession, agente_id: uuid.UUID) -> Agente:
    agente = await painel_repo.agente(s, agente_id)
    if agente is None:
        raise HTTPException(status_code=404, detail="agente não encontrado")
    return agente


class TextoDoPainel(BaseModel):
    texto: str = Field(min_length=3, max_length=20000)
    titulo: str = Field(default="", max_length=200)


class SiteDoPainel(BaseModel):
    url: str = Field(min_length=8, max_length=500)


@router.get("/{agente_id}/documentos")
async def lista(agente_id: uuid.UUID, s: AsyncSession = Depends(sessao)) -> dict[str, Any]:
    agente = await _agente(s, agente_id)
    from app.ia import chaves
    from app.conhecimento.modelos import ConfiguracaoEmbeddings
    await chaves.carregar(s)
    fixado = await s.get(ConfiguracaoEmbeddings, 1)
    documentos = await repo.listar(s, agente.cliente_id, agente.id)
    return {
        "documentos": [saida(d) for d in documentos],
        # Sem isto, a tela deixaria o operador enviar material e só depois descobrir que a
        # instalação não tem como gerar vetor nenhum.
        "modelo_embeddings": fixado.modelo if fixado else embeddings.modelo(),
    }


@router.post("/{agente_id}/documentos", status_code=201)
async def envia(
    agente_id: uuid.UUID,
    request: Request,
    arquivo: UploadFile = File(...),
    s: AsyncSession = Depends(sessao),
) -> dict[str, Any]:
    agente = await _agente(s, agente_id)
    conteudo = await arquivo.read()
    try:
        documento = await servico.recebe_arquivo(
            s,
            agente.cliente_id,
            agente.id,
            arquivo.filename or "material",
            conteudo,
            arquivo.content_type or "application/octet-stream",
            getattr(request.app.state, "fila", None),
        )
    except DE_NEGOCIO as erro:
        raise _erro(erro) from erro
    except ValueError as erro:  # formato que não lemos
        raise HTTPException(status_code=422, detail=str(erro)) from erro
    return saida(documento)


@router.post("/{agente_id}/documentos/texto", status_code=201)
async def envia_texto(
    agente_id: uuid.UUID,
    dados: TextoDoPainel,
    request: Request,
    s: AsyncSession = Depends(sessao),
) -> dict[str, Any]:
    agente = await _agente(s, agente_id)
    try:
        documento = await servico.recebe_texto(
            s,
            agente.cliente_id,
            agente.id,
            dados.texto,
            dados.titulo,
            getattr(request.app.state, "fila", None),
        )
    except DE_NEGOCIO as erro:
        raise _erro(erro) from erro
    return saida(documento)


@router.post("/{agente_id}/documentos/site", status_code=201)
async def envia_site(
    agente_id: uuid.UUID,
    dados: SiteDoPainel,
    request: Request,
    s: AsyncSession = Depends(sessao),
) -> dict[str, Any]:
    agente = await _agente(s, agente_id)
    try:
        documento = await servico.recebe_site(
            s, agente.cliente_id, agente.id, dados.url, getattr(request.app.state, "fila", None)
        )
    except DE_NEGOCIO as erro:
        raise _erro(erro) from erro
    return saida(documento)


@router.delete("/{agente_id}/documentos/{documento_id}")
async def remove(
    agente_id: uuid.UUID, documento_id: uuid.UUID, s: AsyncSession = Depends(sessao)
) -> dict[str, bool]:
    agente = await _agente(s, agente_id)
    try:
        await servico.remover(s, agente.cliente_id, agente.id, documento_id)
    except DE_NEGOCIO as erro:
        raise _erro(erro) from erro
    return {"removido": True}
