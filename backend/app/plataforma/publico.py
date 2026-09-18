"""Páginas públicas da instalação: hoje só a política de privacidade.

A Meta exige uma URL de política de privacidade para publicar o app do WhatsApp, e a instalação já
tem domínio com HTTPS. Em vez de mandar o operador hospedar uma página em outro lugar, a própria
plataforma serve uma, a partir de `modelos/privacidade.html`: é o único lugar do projeto onde a API
devolve HTML. O operador edita o arquivo e a página muda.

`/privacidade/{slug}` nomeia a empresa do cliente, para o app da Meta daquela empresa apontar para
uma página com o nome dela. Não existe listagem: quem não sabe o slug não descobre quem são os
clientes da instalação.
"""

from datetime import date

from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Depends

from app.clientes import repo as clientes_repo
from app.plataforma.banco import sessao
from app.plataforma.config import config

router = APIRouter()

MESES = (
    "janeiro", "fevereiro", "março", "abril", "maio", "junho",
    "julho", "agosto", "setembro", "outubro", "novembro", "dezembro",
)


def _por_extenso(dia: date) -> str:
    return f"{dia.day} de {MESES[dia.month - 1]} de {dia.year}"


def pagina(empresa: str) -> str:
    cfg = config()
    arquivo = cfg.diretorio_modelos / "privacidade.html"
    contato = (
        f"Escreva para {cfg.email_ssl}."
        if cfg.email_ssl
        else "Responda na própria conversa do atendimento."
    )
    return (
        arquivo.read_text(encoding="utf-8")
        .replace("{{EMPRESA}}", empresa)
        .replace("{{DOMINIO}}", cfg.subdominio_bot)
        .replace("{{CONTATO}}", contato)
        .replace("{{ATUALIZADO_EM}}", _por_extenso(date.today()))
    )


@router.get("/privacidade", response_class=HTMLResponse)
async def privacidade() -> HTMLResponse:
    """Política da instalação, sem nomear empresa. Serve a qualquer app da Meta."""
    return HTMLResponse(pagina("O atendimento desta instalação"))


@router.get("/privacidade/{slug}", response_class=HTMLResponse)
async def privacidade_do_cliente(slug: str, s: AsyncSession = Depends(sessao)) -> HTMLResponse:
    """Política com o nome da empresa, para o app da Meta daquela empresa."""
    cliente = await clientes_repo.por_slug(s, slug)
    if cliente is None:
        raise HTTPException(status_code=404, detail="empresa não encontrada")
    return HTMLResponse(pagina(cliente.nome))
