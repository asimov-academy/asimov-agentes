"""Chaves dos provedores de IA e catálogo de modelos, para o menu do terminal.

A chave entra e nunca mais sai: a resposta diz só quais provedores têm chave.
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.ia import chaves
from app.ia.provedores import PROVEDORES, PROVEDORES_TRANSCRICAO, ModeloInvalido
from app.plataforma.admin import exige_admin
from app.plataforma.banco import sessao

router = APIRouter(prefix="/admin/ia", dependencies=[Depends(exige_admin)])


class NovaChave(BaseModel):
    chave: str = Field(min_length=1, max_length=500)


class Provedores(BaseModel):
    provedores: list[str]
    provedores_transcricao: list[str]
    com_chave: list[str]


@router.get("/chaves", response_model=Provedores)
async def lista(s: AsyncSession = Depends(sessao)) -> Provedores:
    return Provedores(
        provedores=list(PROVEDORES),
        provedores_transcricao=list(PROVEDORES_TRANSCRICAO),
        com_chave=await chaves.provedores_com_chave(s),
    )


@router.put("/chaves/{provedor}", status_code=204)
async def guarda(provedor: str, dados: NovaChave, s: AsyncSession = Depends(sessao)) -> None:
    """Testa a chave no provedor antes de guardar."""
    try:
        await chaves.guardar(s, provedor, dados.chave)
    except (chaves.ChaveRecusada, ModeloInvalido) as erro:
        raise HTTPException(status_code=422, detail=str(erro)) from erro


@router.delete("/chaves/{provedor}", status_code=204)
async def esquece(provedor: str, s: AsyncSession = Depends(sessao)) -> None:
    try:
        await chaves.esquecer(s, provedor)
    except ModeloInvalido as erro:
        raise HTTPException(status_code=422, detail=str(erro)) from erro


@router.get("/modelos/{provedor}")
async def modelos(provedor: str, funcao: str = "conversa", s: AsyncSession = Depends(sessao)) -> list[str]:
    try:
        return await chaves.listar_modelos(s, provedor, funcao)
    except ModeloInvalido as erro:
        raise HTTPException(status_code=422, detail=str(erro)) from erro
