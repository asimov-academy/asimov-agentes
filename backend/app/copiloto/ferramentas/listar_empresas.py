"""Empresas da instalação, para o copiloto saber onde criar ou procurar um agente."""

import json

from app.clientes import repo as clientes_repo
from app.copiloto.ferramentas.base import FerramentaDoCopiloto
from app.plataforma.banco import fabrica_sessao


async def listar_empresas() -> str:
    """Lista as empresas da instalação, com id, nome e se estão ativas.

    Use antes de criar um agente, para descobrir o id da empresa, e quando o operador falar de uma
    empresa pelo nome.
    """
    async with fabrica_sessao()() as s:
        empresas = await clientes_repo.listar(s)
    return json.dumps(
        [{"id": str(c.id), "nome": c.nome, "slug": c.slug, "ativa": c.ativo} for c in empresas],
        ensure_ascii=False,
    )


FERRAMENTA = FerramentaDoCopiloto(
    nome="listar_empresas",
    descricao="empresas da instalação, com o id que as outras ferramentas pedem",
    funcao=listar_empresas,
)
