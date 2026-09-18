"""Conversas e contatos no painel: a tela de Chat e a de Contatos.

Conteúdo de conversa aparece no navegador. É decisão consciente, registrada em spec/decisoes.md: o
acesso é só do operador, não existe exportação e a página leva `noindex`. Por isso aqui só sai o que
a tela mostra, e nada vira arquivo.
"""

import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.clientes import repo as clientes_repo
from app.conversas import repo as conversas_repo
from app.handoff import servico as handoff_servico
from app.painel import repo
from app.painel.acesso import exige_csrf, exige_sessao
from app.plataforma.banco import sessao

router = APIRouter(
    prefix="/api",
    include_in_schema=False,
    dependencies=[Depends(exige_sessao), Depends(exige_csrf)],
)


@router.get("/conversas")
async def conversas(
    cliente_id: uuid.UUID | None = Query(default=None),
    agente_id: uuid.UUID | None = Query(default=None),
    status: str | None = Query(default=None),
    limite: int = Query(default=50, ge=1, le=200),
    s: AsyncSession = Depends(sessao),
) -> list[dict[str, Any]]:
    """As conversas mais recentes, com o contato, o agente e como ela está agora."""
    if cliente_id is not None and await clientes_repo.obter(s, cliente_id) is None:
        raise HTTPException(status_code=404, detail="empresa não encontrada")
    return await repo.conversas(s, cliente_id, agente_id, status, limite)


@router.get("/conversas/{conversa_id}")
async def conversa(conversa_id: uuid.UUID, s: AsyncSession = Depends(sessao)) -> dict[str, Any]:
    """O histórico da conversa e o que cada turno custou."""
    cabecalho = await repo.conversa(s, conversa_id)
    if cabecalho is None:
        raise HTTPException(status_code=404, detail="conversa não encontrada")
    mensagens = await conversas_repo.ultimas_mensagens(
        s, uuid.UUID(cabecalho["cliente_id"]), conversa_id, limite=200
    )
    return {
        **cabecalho,
        "mensagens": [
            {
                "id": str(m.id),
                "criado_em": m.criado_em.isoformat(),
                "direcao": m.direcao,
                "autor": m.autor,
                "tipo": m.tipo,
                "texto": m.texto,
                "texto_extraido": m.texto_extraido,
                "anexo": m.anexo,
            }
            for m in mensagens
        ],
        "turnos": await repo.turnos_da_conversa(s, conversa_id),
    }


class Retomada(BaseModel):
    """Sem corpo por enquanto: a retomada não tem opção. O modelo existe para a rota exigir POST."""


@router.post("/conversas/{conversa_id}/retomar")
async def retomar(
    conversa_id: uuid.UUID, dados: Retomada, s: AsyncSession = Depends(sessao)
) -> dict[str, bool]:
    """Devolve ao agente uma conversa que está com uma pessoa. Mesma operação do menu."""
    cabecalho = await repo.conversa(s, conversa_id)
    if cabecalho is None:
        raise HTTPException(status_code=404, detail="conversa não encontrada")
    try:
        retomado = await handoff_servico.retomar_pelo_operador(
            s, uuid.UUID(cabecalho["cliente_id"]), conversa_id
        )
    except handoff_servico.ConversaNaoEncontrada as erro:
        raise HTTPException(status_code=404, detail=str(erro)) from erro
    except Exception as erro:
        raise HTTPException(
            status_code=502, detail="o canal recusou devolver a conversa ao agente"
        ) from erro
    return {"retomado": retomado}


@router.get("/contatos")
async def contatos(
    busca: str = Query(default="", max_length=200),
    cliente_id: uuid.UUID | None = Query(default=None),
    limite: int = Query(default=50, ge=1, le=200),
    s: AsyncSession = Depends(sessao),
) -> list[dict[str, Any]]:
    """Contatos por nome ou telefone. Sem exportação em massa: a lista tem teto e é só leitura."""
    if cliente_id is not None and await clientes_repo.obter(s, cliente_id) is None:
        raise HTTPException(status_code=404, detail="empresa não encontrada")
    return await repo.contatos(s, busca.strip(), cliente_id, limite)


@router.get("/contatos/{contato_id}")
async def contato(contato_id: uuid.UUID, s: AsyncSession = Depends(sessao)) -> dict[str, Any]:
    """A ficha do contato: quem é e as conversas dele."""
    ficha = await repo.contato(s, contato_id)
    if ficha is None:
        raise HTTPException(status_code=404, detail="contato não encontrado")
    return ficha
