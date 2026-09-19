"""Agentes da instalação inteira, como a lista do painel mostra."""

import json

from app.agentes import repo as agentes_repo
from app.clientes import repo as clientes_repo
from app.copiloto.ferramentas.base import FerramentaDoCopiloto
from app.plataforma.banco import fabrica_sessao


async def listar_agentes() -> str:
    """Lista todos os agentes, com id, empresa, canal, modelo de resposta e se estão ativos.

    Use sempre antes de falar de um agente: é daqui que sai o id que as outras ferramentas pedem.
    """
    async with fabrica_sessao()() as s:
        agentes = await agentes_repo.listar_de_todos_os_clientes(s)
        empresas = {c.id: c.nome for c in await clientes_repo.listar(s)}
    return json.dumps(
        [
            {
                "id": str(a.id),
                "nome": a.nome,
                "empresa": empresas.get(a.cliente_id, ""),
                "empresa_id": str(a.cliente_id),
                "canal": a.canal,
                "situacao": a.situacao,
                "modelo": a.modelo_conversa,
                "ferramentas": a.ferramentas or [],
            }
            for a in agentes
        ],
        ensure_ascii=False,
    )


FERRAMENTA = FerramentaDoCopiloto(
    nome="listar_agentes",
    descricao="todos os agentes com id, empresa, canal e modelo",
    funcao=listar_agentes,
)
