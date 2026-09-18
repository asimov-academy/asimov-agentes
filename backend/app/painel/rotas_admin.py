"""O que o setup precisa saber e fazer sobre o painel, pela API local.

Só o terminal da VPS chega aqui (é `/admin`, com a chave da instalação e sem sair de localhost).
É de propósito: o código de primeiro acesso nasce em quem tem a VPS, não em quem abre o endereço.
"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.painel import repo, servico
from app.plataforma.admin import exige_admin
from app.plataforma.banco import sessao
from app.plataforma.config import config

router = APIRouter(prefix="/admin/painel", dependencies=[Depends(exige_admin)])


class EstadoSaida(BaseModel):
    ativo: bool
    endereco: str
    tem_operador: bool


class CodigoSaida(BaseModel):
    codigo: str
    minutos: int
    endereco: str


def _endereco() -> str:
    cfg = config()
    return f"https://{cfg.subdominio_app}/painel" if cfg.subdominio_app else ""


@router.get("", response_model=EstadoSaida)
async def estado(s: AsyncSession = Depends(sessao)) -> EstadoSaida:
    return EstadoSaida(
        ativo=config().painel_ativo,
        endereco=_endereco(),
        tem_operador=await repo.operador(s) is not None,
    )


@router.post("/codigo", response_model=CodigoSaida)
async def codigo() -> CodigoSaida:
    """Código de uso único para criar o acesso no navegador."""
    gerado = servico.novo_codigo()
    await servico.guarda_codigo(gerado)
    return CodigoSaida(
        codigo=gerado, minutos=servico.DURACAO_CODIGO_SEGUNDOS // 60, endereco=_endereco()
    )


@router.delete("/operador", status_code=204)
async def esquece_operador(s: AsyncSession = Depends(sessao)) -> None:
    """Apaga a conta e derruba as sessões: é como se troca uma senha esquecida.

    Quem manda isto já está dentro da VPS, que é onde mora tudo o que o painel protege.
    """
    usuario = await repo.operador(s)
    if usuario is not None:
        await s.delete(usuario)
        await s.commit()
    async with servico.conexao() as r:
        chaves = await r.keys("painel:sessao:*")
        if chaves:
            await r.delete(*chaves)
