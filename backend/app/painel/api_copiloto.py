"""Rotas do copiloto no painel: conversar, acompanhar e confirmar o que ele propõe.

Mesma fronteira das outras rotas do painel: sessão do operador, CSRF em escrita, nenhuma regra
nova aqui dentro. A rota enfileira e lê; quem executa o CLI é o worker do copiloto, e quem aplica
uma proposta é `app/copiloto/aplicar.py`.

O acompanhamento é por polling, como a conversa de teste do agente: o front pergunta de tempos em
tempos e mostra o que mudou.
"""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.copiloto import aplicar, vinculo
from app.copiloto import sessao as sessao_do_copiloto
from app.copiloto.worker import FILA
from app.painel.acesso import exige_csrf, exige_sessao
from app.plataforma.banco import sessao

router = APIRouter(
    prefix="/api/copiloto",
    include_in_schema=False,
    dependencies=[Depends(exige_sessao), Depends(exige_csrf)],
)

LIMITE_PEDIDO = 4000


class Pedido(BaseModel):
    texto: str = Field(min_length=1, max_length=LIMITE_PEDIDO)


class Decisao(BaseModel):
    aplicar: bool


@router.get("")
async def estado() -> dict[str, Any]:
    """Uma chamada só ao abrir o popup: se o copiloto existe nesta instalação e o que já foi dito."""
    return {
        "vinculo": vinculo.situacao(),
        "sessao": sessao_do_copiloto.para_o_painel(await sessao_do_copiloto.ler()),
    }


@router.get("/sessao")
async def acompanha() -> dict[str, Any]:
    return sessao_do_copiloto.para_o_painel(await sessao_do_copiloto.ler())


@router.post("/mensagens")
async def fala(pedido: Pedido, request: Request) -> dict[str, Any]:
    if not vinculo.disponivel():
        raise HTTPException(
            status_code=409,
            detail="nenhuma conta de IA vinculada; rode asimov ia no terminal da VPS",
        )
    atual = await sessao_do_copiloto.ler()
    if atual["estado"] == "pensando":
        raise HTTPException(status_code=409, detail="o copiloto ainda está respondendo")

    # O que aconteceu fora da conversa (uma proposta aplicada, por exemplo) entra no começo do
    # pedido, em vez de gastar um turno só para contar ao copiloto.
    recado = atual.get("recado_pendente", "")
    texto = f"[o operador acabou de: {recado}]\n\n{pedido.texto}" if recado else pedido.texto

    await sessao_do_copiloto.anota_mensagem("operador", pedido.texto)
    await sessao_do_copiloto.muda(estado="pensando", erro="", recado_pendente="")
    await request.app.state.fila.enqueue_job("turno_do_copiloto", texto, _queue_name=FILA)
    return sessao_do_copiloto.para_o_painel(await sessao_do_copiloto.ler())


@router.post("/propostas/{proposta_id}")
async def decide(
    proposta_id: str, decisao: Decisao, s: AsyncSession = Depends(sessao)
) -> dict[str, Any]:
    """O clique do operador. É o único caminho pelo qual o copiloto muda alguma coisa."""
    proposta = await sessao_do_copiloto.proposta(proposta_id)
    if proposta is None:
        raise HTTPException(status_code=404, detail="proposta não encontrada")
    if not decisao.aplicar:
        await sessao_do_copiloto.fecha_proposta(proposta_id, "recusada")
        await sessao_do_copiloto.muda(recado_pendente=f"recusar: {proposta['titulo']}")
        return sessao_do_copiloto.para_o_painel(await sessao_do_copiloto.ler())

    try:
        resultado = await aplicar.aplica(s, proposta)
    except aplicar.PropostaInvalida as erro:
        raise HTTPException(status_code=409, detail=str(erro)) from erro
    except Exception as erro:
        await sessao_do_copiloto.fecha_proposta(proposta_id, "falhou", "não deu para aplicar")
        raise HTTPException(status_code=422, detail=_recado(erro)) from erro

    await sessao_do_copiloto.fecha_proposta(proposta_id, "aplicada", resultado)
    await sessao_do_copiloto.anota_mensagem("sistema", resultado)
    await sessao_do_copiloto.muda(recado_pendente=f"confirmar: {proposta['titulo']}. {resultado}")
    return sessao_do_copiloto.para_o_painel(await sessao_do_copiloto.ler())


@router.delete("/sessao")
async def recomeca() -> dict[str, Any]:
    """Conversa nova. O fio do lado do CLI também é abandonado: o próximo turno começa do zero."""
    await sessao_do_copiloto.limpa()
    return sessao_do_copiloto.para_o_painel(await sessao_do_copiloto.ler())


def _recado(erro: Exception) -> str:
    """O motivo em português, curto. O corpo cru do erro fica no log, nunca na tela."""
    texto = str(erro).strip()
    return texto[:180] if texto else "não deu para aplicar esta proposta"
