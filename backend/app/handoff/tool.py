"""Tool que o modelo chama para passar a conversa a um humano.

Só registra o pedido. A transferência acontece no fim do turno, depois de a resposta ao contato
ser enviada: se o contato mandar mensagem nova antes, a resposta e o pedido são descartados
juntos e o turno seguinte decide de novo.
"""

from pydantic_ai import RunContext

from app.ia.contexto import ContextoTurno


async def transferir_para_humano(ctx: RunContext[ContextoTurno], motivo: str) -> str:
    """Passa a conversa para uma pessoa da equipe e para de responder este contato.

    Use quando o contato pedir para falar com uma pessoa ou quando o atendimento precisar de alguém da equipe.

    Args:
        motivo: Por que a conversa vai para humano, em uma frase.
    """
    if ctx.deps.motivo_handoff is None:
        ctx.deps.motivo_handoff = motivo.strip()[:500] or "sem motivo informado"
    return (
        "Transferência registrada. Avise o contato, em uma mensagem curta, que uma pessoa da "
        "equipe vai continuar o atendimento por aqui. Não faça novas perguntas."
    )
