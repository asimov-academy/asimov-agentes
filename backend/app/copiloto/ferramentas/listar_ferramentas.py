"""Catálogo de ferramentas que um agente pode ter ligadas."""

import json

from app.copiloto.ferramentas.base import FerramentaDoCopiloto
from app.ia.ferramentas import registro


async def listar_ferramentas() -> str:
    """Lista as ferramentas que um agente de atendimento pode ter ligadas, com o nome exato.

    Use antes de propor ligar ou desligar ferramenta: só estes nomes valem.
    """
    return json.dumps(
        [{"nome": f.nome, "rotulo": f.rotulo, "descricao": f.descricao} for f in registro.FICHAS],
        ensure_ascii=False,
    )


FERRAMENTA = FerramentaDoCopiloto(
    nome="listar_ferramentas",
    descricao="ferramentas que um agente pode ter ligadas, com o nome exato",
    funcao=listar_ferramentas,
)
