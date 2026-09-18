"""Proposta de mudança num agente que já existe.

Nada é salvo aqui. A ferramenta confere o que dá para conferir na hora (o agente existe, as
ferramentas existem, o emoji é um dos quatro) e guarda a proposta na sessão do copiloto. O
operador vê no painel o que vai mudar e confirma; quem aplica é `app/copiloto/aplicar.py`.

É o que impede uma frase escondida num prompt ou numa conversa de contato de virar mudança de
configuração: o caminho da escrita passa obrigatoriamente por um clique do operador.
"""

import uuid

from app.agentes import repo as agentes_repo
from app.copiloto import sessao as sessao_do_copiloto
from app.copiloto.ferramentas.base import FerramentaDoCopiloto
from app.ia.ferramentas import registro
from app.plataforma.banco import fabrica_sessao

EMOJIS = ("nenhum", "pouco", "medio", "muito")
LIMITE_PROMPT = 20000


async def propor_mudanca_no_agente(
    agente_id: str,
    resumo: str,
    prompt: str | None = None,
    nome: str | None = None,
    ferramentas: list[str] | None = None,
    emojis: str | None = None,
    buffer_segundos: int | None = None,
    max_mensagens_por_resposta: int | None = None,
) -> str:
    """Propõe mudar um agente. Nada muda até o operador confirmar no painel.

    Mande só o que muda. Para o prompt, mande o texto inteiro já reescrito, nunca um pedaço: ele
    substitui o que está lá. Leia o agente com ver_agente antes, para não apagar o que já existe.
    Uma proposta por pedido: se o operador pediu duas coisas no mesmo agente, junte na mesma.

    Args:
        agente_id: id do agente, como veio de listar_agentes.
        resumo: uma frase dizendo ao operador o que muda e por quê.
        prompt: prompt novo, inteiro, para substituir o atual.
        nome: nome novo do agente.
        ferramentas: lista completa de ferramentas ligadas, com os nomes de listar_ferramentas.
        emojis: quanto o agente usa emoji: nenhum, pouco, medio ou muito.
        buffer_segundos: segundos que o agente espera juntando mensagens antes de responder.
        max_mensagens_por_resposta: em quantas mensagens ele pode quebrar uma resposta.
    """
    try:
        procurado = uuid.UUID(agente_id)
    except ValueError:
        return "agente_id inválido. Chame listar_agentes para ver os ids que existem."

    async with fabrica_sessao()() as s:
        agente = next(
            (a for a in await agentes_repo.listar_de_todos_os_clientes(s) if a.id == procurado),
            None,
        )
    if agente is None:
        return "Agente não encontrado. Chame listar_agentes para ver os ids que existem."

    campos: dict[str, object] = {}
    if nome is not None:
        campos["nome"] = nome.strip()
    if ferramentas is not None:
        desconhecidas = sorted(set(ferramentas) - set(registro.CATALOGO))
        if desconhecidas:
            return (
                f"Estas ferramentas não existem: {', '.join(desconhecidas)}. "
                "Chame listar_ferramentas e use os nomes de lá."
            )
        campos["ferramentas"] = ferramentas
    if emojis is not None:
        if emojis not in EMOJIS:
            return f"emojis precisa ser um de: {', '.join(EMOJIS)}."
        campos["emojis"] = emojis
    if buffer_segundos is not None:
        campos["buffer_segundos"] = buffer_segundos
    if max_mensagens_por_resposta is not None:
        campos["max_mensagens_por_resposta"] = max_mensagens_por_resposta

    if not campos and prompt is None:
        return "Nada para mudar: mande pelo menos um campo ou o prompt."

    proposta = await sessao_do_copiloto.anota_proposta(
        {
            "tipo": "mudanca",
            "agente_id": str(agente.id),
            "cliente_id": str(agente.cliente_id),
            "titulo": f"Ajustar {agente.nome}",
            "resumo": resumo.strip(),
            "campos": campos,
            "prompt": prompt[:LIMITE_PROMPT] if prompt is not None else None,
        }
    )
    return (
        f"Proposta {proposta['id']} registrada e mostrada ao operador. Nada foi salvo ainda: ele"
        " precisa confirmar no painel. Diga em uma frase o que propôs e espere a resposta dele."
    )


FERRAMENTA = FerramentaDoCopiloto(
    nome="propor_mudanca_no_agente",
    descricao="propõe mudar prompt, nome, ferramentas ou ritmo de um agente",
    funcao=propor_mudanca_no_agente,
    escreve=True,
)
