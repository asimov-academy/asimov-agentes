"""Páginas públicas da instalação: hoje só a política de privacidade.

A Meta exige uma URL de política de privacidade para publicar o app do WhatsApp, e a instalação já
tem domínio com HTTPS. Em vez de mandar o operador hospedar uma página em outro lugar, a própria
plataforma serve uma, a partir de `modelos/privacidade.html`: é o único lugar do projeto onde a API
devolve HTML. O operador edita o arquivo e a página muda.

Três endereços, porque na Meta existe um app por número: `/privacidade` para a instalação,
`/privacidade/{empresa}` para o cliente e `/privacidade/{empresa}/{agente}` para um agente dele.
Não existe listagem: quem não sabe o slug não descobre quem são os clientes da instalação.

`/icone-app.png` serve o ícone quadrado que o app da Meta também exige, para o operador baixar pelo
navegador em vez de tirar o arquivo da VPS com `scp`.
"""

from datetime import date

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Depends

from app.agentes import repo as agentes_repo
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


def pagina(empresa: str, agente: str = "") -> str:
    cfg = config()
    arquivo = cfg.diretorio_modelos / "privacidade.html"
    if not arquivo.is_file():
        # Acontece quando a atualização não trouxe `modelos/`: melhor dizer o que falta do que
        # devolver um erro interno sem explicação.
        raise HTTPException(
            status_code=503,
            detail=f"{arquivo} não encontrado: atualize a instalação (asimov atualizar)",
        )
    contato = (
        f"Escreva para {cfg.email_ssl}."
        if cfg.email_ssl
        else "Responda na própria conversa do atendimento."
    )
    return (
        arquivo.read_text(encoding="utf-8")
        .replace("{{EMPRESA}}", empresa)
        .replace("{{AGENTE}}", f" · atendimento de {agente}" if agente else "")
        .replace("{{DOMINIO}}", cfg.subdominio_bot)
        .replace("{{CONTATO}}", contato)
        .replace("{{ATUALIZADO_EM}}", _por_extenso(date.today()))
    )


@router.get("/privacidade", response_class=HTMLResponse)
async def privacidade() -> HTMLResponse:
    """Política da instalação, sem nomear empresa. Serve a qualquer app da Meta."""
    return HTMLResponse(pagina("O atendimento desta instalação"))


@router.get("/privacidade/{empresa}", response_class=HTMLResponse)
async def privacidade_do_cliente(empresa: str, s: AsyncSession = Depends(sessao)) -> HTMLResponse:
    """Política com o nome da empresa, para o app da Meta daquela empresa."""
    cliente = await clientes_repo.por_slug(s, empresa)
    if cliente is None:
        raise HTTPException(status_code=404, detail="empresa não encontrada")
    return HTMLResponse(pagina(cliente.nome))


@router.get("/privacidade/{empresa}/{agente}", response_class=HTMLResponse)
async def privacidade_do_agente(
    empresa: str, agente: str, s: AsyncSession = Depends(sessao)
) -> HTMLResponse:
    """Política de um agente: na Meta é um app por número, e cada app quer a própria URL."""
    cliente = await clientes_repo.por_slug(s, empresa)
    if cliente is None:
        raise HTTPException(status_code=404, detail="empresa não encontrada")
    achado = await agentes_repo.por_slug(s, cliente.id, agente)
    if achado is None:
        raise HTTPException(status_code=404, detail="agente não encontrado")
    return HTMLResponse(pagina(cliente.nome, achado.nome))


@router.get("/icone-app.png", response_class=FileResponse)
async def icone_do_app() -> FileResponse:
    """Ícone quadrado para o app da Meta. Trocar `modelos/icone-app.png` troca o que sai aqui."""
    arquivo = config().diretorio_modelos / "icone-app.png"
    if not arquivo.is_file():
        raise HTTPException(
            status_code=503,
            detail=f"{arquivo} não encontrado: atualize a instalação (asimov atualizar)",
        )
    return FileResponse(arquivo, media_type="image/png", filename="icone-app.png")
