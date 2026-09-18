"""Rotas JSON do painel, consumidas pelo front em `frontend/`.

Fronteira importante: isto **não** é `/admin` publicado. O front não conhece a `CHAVE_API_ADMIN`;
ele se identifica pela sessão do operador, e cada rota daqui chama os mesmos `servico.py` e
`repo.py` que as rotas administrativas chamam. Nenhuma regra de negócio nasce neste arquivo.

Contrato completo em spec/frontend.md, seção 6. As rotas entram por etapa, não de uma vez.
"""

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.agentes import repo as agentes_repo
from app.clientes import repo as clientes_repo
from app.painel import repo, servico
from app.painel.acesso import exige_csrf, exige_sessao, token_da_sessao
from app.plataforma.banco import sessao
from app.plataforma.config import config

router = APIRouter(
    prefix="/api",
    include_in_schema=False,
    dependencies=[Depends(exige_sessao), Depends(exige_csrf)],
)


@router.get("/eu")
async def eu(
    token: str = Depends(token_da_sessao), s: AsyncSession = Depends(sessao)
) -> dict[str, Any]:
    """Primeira chamada do front: quem entrou, o tamanho da instalação e o token de escrita.

    Nada de credencial de canal aqui, nem contagem que revele dado de contato. É a tela de casca.
    """
    operador = await repo.operador(s)
    if operador is None:
        raise HTTPException(status_code=401, detail="entre no painel")
    espaco = await repo.espaco(s)
    await s.commit()
    cfg = config()
    return {
        "operador": {
            "nome": operador.nome,
            "email": operador.email,
            "criado_em": operador.criado_em.isoformat(),
            "ultimo_acesso_em": operador.ultimo_acesso_em.isoformat()
            if operador.ultimo_acesso_em
            else None,
        },
        "espaco": {
            "nome": espaco.nome,
            "sigla": espaco.sigla,
            "negocio_nome": espaco.negocio_nome,
            "negocio_documento": espaco.negocio_documento,
            "negocio_email": espaco.negocio_email,
            "negocio_telefone": espaco.negocio_telefone,
            "negocio_site": espaco.negocio_site,
        },
        "instalacao": {
            "subdominio_bot": cfg.subdominio_bot,
            "subdominio_app": cfg.subdominio_app,
        },
        "empresas": len(await clientes_repo.listar(s)),
        "agentes": len(await agentes_repo.listar_de_todos_os_clientes(s)),
        "csrf": servico.token_csrf(token),
    }


@router.get("/empresas")
async def empresas(s: AsyncSession = Depends(sessao)) -> list[dict[str, Any]]:
    """Alimenta o seletor da barra do topo. Só o que a barra mostra: nome, slug e se está ativa."""
    return [
        {"id": str(c.id), "nome": c.nome, "slug": c.slug, "ativo": c.ativo}
        for c in await clientes_repo.listar(s)
    ]


class Totais(BaseModel):
    conversas: int
    turnos: int
    custo: Decimal
    custo_parcial: bool
    """Alguma chamada sem preço informado: o custo real é maior que o mostrado."""
    falhas: int
    handoffs_vencidos: int


class Ponto(BaseModel):
    quando: datetime
    turnos: int


class Serie(BaseModel):
    por: str
    """`hour` no período de um dia, `day` nos outros."""
    pontos: list[Ponto]


class GastoDoModelo(BaseModel):
    modelo: str
    chamadas: int
    tokens: int
    custo: Decimal


class FalhaDoPainel(BaseModel):
    """Sem o `detalhe` cru: o corpo de um erro de provedor já veio com a chave de API dentro."""

    criado_em: datetime
    tipo: str
    resumo: str
    cliente_id: uuid.UUID | None
    cliente: str | None
    agente_id: uuid.UUID | None
    agente: str | None


class HandoffAberto(BaseModel):
    """Sem `resumo`: o texto da conversa aparece na tela de Chat, não na de abertura."""

    id: uuid.UUID
    conversa_id: uuid.UUID
    codigo: str
    motivo: str
    canal: str
    iniciado_em: datetime
    retomar_em: datetime | None
    vencido: bool
    cliente_id: uuid.UUID
    cliente: str
    agente_id: uuid.UUID
    agente: str


class Variacao(BaseModel):
    """Quanto cada número mudou do período anterior, em por cento. `None` é "sem comparação"."""

    conversas: float | None
    turnos: float | None
    custo: float | None
    falhas: float | None


class Resolucao(BaseModel):
    """De cada conversa do período, quantas o agente fechou sem chamar gente."""

    conversas: int
    com_gente: int
    sozinho: int
    porcento: int | None


class TurnosDoAgente(BaseModel):
    agente: str
    cliente: str
    turnos: int
    custo: Decimal


class Situacao(BaseModel):
    cor: str
    texto: str


class VisaoGeral(BaseModel):
    dias: int
    desde: datetime
    totais: Totais
    variacao: Variacao
    serie: Serie
    modelos: list[GastoDoModelo]
    resolucao: Resolucao
    agentes: list[TurnosDoAgente]
    falhas: list[FalhaDoPainel]
    handoffs: list[HandoffAberto]
    situacao: Situacao


@router.get("/visao-geral", response_model=VisaoGeral)
async def visao_geral(
    dias: int = Query(default=7),
    cliente_id: uuid.UUID | None = Query(default=None),
    s: AsyncSession = Depends(sessao),
) -> VisaoGeral:
    """Cartões, gráficos, falhas e handoffs do período. Sem `cliente_id`, a instalação inteira.

    O `cliente_id` chega pela URL e é conferido no banco antes de virar filtro: o corpo da
    requisição nunca escolhe de quem é o dado, nem aqui nem em rota nenhuma.
    """
    if dias not in servico.PERIODOS:
        raise HTTPException(
            status_code=422, detail=f"período inválido: use {', '.join(map(str, servico.PERIODOS))}"
        )
    if cliente_id is not None and await clientes_repo.obter(s, cliente_id) is None:
        raise HTTPException(status_code=404, detail="empresa não encontrada")
    return VisaoGeral.model_validate(await servico.visao_geral(s, dias, cliente_id))


# Espaço de trabalho e perfil
#
# Os dois são da instalação, não de uma empresa atendida: por isso ficam aqui e não em `clientes/`.
# Uma linha cada, como o operador.


class PerfilDoOperador(BaseModel):
    nome: str = Field(default="", max_length=120)
    email: str = Field(default="", max_length=200)


class EspacoDeTrabalho(BaseModel):
    nome: str = Field(default="", max_length=120)
    sigla: str = Field(default="", max_length=2)
    negocio_nome: str = Field(default="", max_length=200)
    negocio_documento: str = Field(default="", max_length=40)
    negocio_email: str = Field(default="", max_length=200)
    negocio_telefone: str = Field(default="", max_length=40)
    negocio_site: str = Field(default="", max_length=300)


@router.put("/perfil", status_code=204)
async def grava_perfil(dados: PerfilDoOperador, s: AsyncSession = Depends(sessao)) -> None:
    """Quem opera. Não serve para entrar: a senha continua a única credencial."""
    operador = await repo.operador(s)
    if operador is None:
        raise HTTPException(status_code=401, detail="entre no painel")
    operador.nome = dados.nome.strip()
    operador.email = dados.email.strip()
    await s.commit()


@router.put("/espaco", status_code=204)
async def grava_espaco(dados: EspacoDeTrabalho, s: AsyncSession = Depends(sessao)) -> None:
    espaco = await repo.espaco(s)
    for campo, valor in dados.model_dump().items():
        setattr(espaco, campo, str(valor).strip())
    await s.commit()
