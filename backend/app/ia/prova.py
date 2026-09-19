"""A prova do agente: as mesmas cinco perguntas, antes e depois de mexer no prompt.

Fase 10, etapa 5. Duas coisas já reescrevem o prompt sozinhas (o botão "Melhorar com IA" e o
copiloto), e ninguém media o resultado. A prova roda um punhado de casos fixos contra o agente de
verdade, com o modelo e o prompt dele, e devolve o que ele respondeu.

**Mostra, não bloqueia.** Nota de juiz automático não é confiável a ponto de impedir o operador de
salvar o próprio prompt; o que ele precisa é ver a diferença. Quem julga é quem vai responder ao
cliente depois.

Nada é gravado: a conversa da prova não existe no banco, não entra no histórico do contato e não
conta como conversa do período. O consumo do modelo, esse existe, e é do operador.
"""

import asyncio
import uuid
from datetime import timedelta
from typing import TYPE_CHECKING, Any

import structlog

from app.conversas.modelos import Mensagem
from app.ia.agente import roda_turno
from app.plataforma.banco import agora

if TYPE_CHECKING:
    from app.agentes.modelos import Agente

log = structlog.get_logger()

CASOS: tuple[tuple[str, str], ...] = (
    ("saudação", "oi"),
    ("preço", "quanto custa?"),
    ("reclamação", "isso é um absurdo, faz três dias que ninguém me responde"),
    ("pedido de pessoa", "quero falar com um atendente de verdade"),
    ("fora do assunto", "me explica como fazer um bolo de cenoura"),
)
"""Os cinco casos em que dá para ver, lendo, se o agente piorou: como ele abre, o que faz com preço,
o que faz com raiva, o que faz com o pedido de gente e o que faz com assunto que não é dele."""

LIMITE_DE_SEGUNDOS = 120


async def roda(agente: "Agente") -> list[dict[str, Any]]:
    """Responde os cinco casos em paralelo. Caso que falhar vira erro na linha dele, não exceção."""

    async def um(indice: int, caso: tuple[str, str]) -> dict[str, Any]:
        nome, pergunta = caso
        mensagem = Mensagem(
            id=uuid.uuid4(),
            cliente_id=agente.cliente_id,
            conversa_id=uuid.uuid4(),
            direcao="entrada",
            autor="contato",
            texto=pergunta,
            criado_em=agora() + timedelta(milliseconds=indice),
        )
        try:
            resultado = await roda_turno(agente, [], [mensagem])
        except Exception as erro:
            log.info("prova_falhou", agente_id=str(agente.id), caso=nome, erro=repr(erro)[:200])
            return {"caso": nome, "pergunta": pergunta, "erro": "o modelo não respondeu"}
        return {
            "caso": nome,
            "pergunta": pergunta,
            "mensagens": resultado.mensagens,
            "sentimento": resultado.sentimento,
            "transferiu": resultado.motivo_handoff is not None,
            "erro": "",
        }

    async with asyncio.timeout(LIMITE_DE_SEGUNDOS):
        return list(await asyncio.gather(*(um(i, caso) for i, caso in enumerate(CASOS))))
