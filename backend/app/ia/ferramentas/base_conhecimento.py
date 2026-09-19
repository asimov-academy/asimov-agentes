"""Ferramenta de busca na base de conhecimento do agente.

O agente responde com o material do cliente em vez de só com o prompt. A busca é vetorial e filtra
`cliente_id` e `agente_id` no `WHERE`: material de uma empresa nunca aparece na conversa de outra.

A ferramenta liga sozinha quando o operador manda o primeiro material (em `conhecimento/servico.py`)
e pode ser desligada em Ferramentas, como qualquer outra.
"""

from pydantic_ai import RunContext

from app.ia.contexto import ContextoTurno
from app.ia.ferramentas.base import Ferramenta

QUANTOS = 5
DISTANCIA_MAXIMA = 0.6
"""Acima disso o trecho não fala do assunto: devolver mesmo assim é convidar o modelo a inventar."""


async def buscar_base_conhecimento(ctx: RunContext[ContextoTurno], pergunta: str) -> str:
    """Procura no material da empresa (documentos, textos e páginas que o operador ensinou).

    Use sempre que o contato perguntar algo sobre a empresa, produto, preço, prazo, política ou
    procedimento. Responda com o que voltar daqui, e nunca invente o que não estiver nos trechos.

    Args:
        pergunta: O que procurar, com as palavras do contato.
    """
    from app.conhecimento import servico
    from app.plataforma.banco import fabrica_sessao

    if ctx.deps.cliente_id is None or ctx.deps.agente_id is None:
        return "A base de conhecimento não está disponível neste atendimento."
    async with fabrica_sessao()() as sessao:
        achados = await servico.buscar(
            sessao, ctx.deps.cliente_id, ctx.deps.agente_id, pergunta, QUANTOS
        )
    uteis = [a for a in achados if a["distancia"] <= DISTANCIA_MAXIMA]
    if not uteis:
        return (
            "Nada na base sobre isso. Não invente: diga que vai confirmar, ou trate como assunto "
            "que você não tem material para responder."
        )
    ctx.deps.usou_base = True
    return "\n\n".join(f"[{a['documento']}]\n{a['texto']}" for a in uteis)


FERRAMENTA = Ferramenta(
    nome="base_conhecimento",
    rotulo="Base de conhecimento",
    descricao="Procura no material que você ensinou ao agente (documentos, textos e sites).",
    instrucao=(
        "Você tem o material da empresa numa base de conhecimento. Use buscar_base_conhecimento "
        "antes de responder qualquer pergunta sobre a empresa, produto, preço, prazo ou "
        "procedimento, e responda só com o que voltar de lá. Quando não voltar nada, diga que vai "
        "confirmar, sem inventar."
    ),
    tools=lambda: [buscar_base_conhecimento],
)
