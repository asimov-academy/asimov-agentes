"""Monta e roda o agente de um turno.

O prompt da persona vem do arquivo do agente em `prompts/`, relido a cada turno: o operador
edita o arquivo e a mudança vale na próxima mensagem, sem publicar de novo.
"""

from dataclasses import dataclass, field
from decimal import Decimal
from typing import TYPE_CHECKING

from pydantic import BaseModel, Field
from pydantic_ai import Agent
from pydantic_ai.messages import (
    ModelMessage,
    ModelRequest,
    ModelResponse,
    TextPart,
    ToolCallPart,
    UserPromptPart,
)

from app.ia.provedores import modelo_de_resposta
from app.plataforma.config import config

if TYPE_CHECKING:
    from pydantic_ai.models import Model

    from app.agentes.modelos import Agente
    from app.conversas.modelos import Mensagem


class Resposta(BaseModel):
    mensagens: list[str] = Field(
        description="Mensagens curtas, na ordem em que serão enviadas ao contato.",
        min_length=1,
    )


@dataclass
class ResultadoTurno:
    mensagens: list[str]
    tokens_entrada: int = 0
    tokens_saida: int = 0
    custo_estimado: Decimal | None = None
    tools_chamadas: list[str] = field(default_factory=list)


INSTRUCAO_DE_SAIDA = (
    "Responda com no máximo {n} mensagens curtas, como alguém digitando no celular. "
    "Sem markdown, sem listas com asterisco, sem títulos."
)


def le_prompt(agente: "Agente") -> str:
    return (config().diretorio_prompts / agente.arquivo_prompt).read_text(encoding="utf-8")


def historico(mensagens: list["Mensagem"]) -> list[ModelMessage]:
    """Contato vira fala do usuário; agente e atendente humano viram fala do assistente."""
    saida: list[ModelMessage] = []
    for m in mensagens:
        texto = m.texto or m.texto_extraido or f"[{m.tipo} sem texto]"
        if m.autor == "contato":
            saida.append(ModelRequest(parts=[UserPromptPart(content=texto)]))
        else:
            prefixo = "(atendente humano) " if m.autor == "humano" else ""
            saida.append(ModelResponse(parts=[TextPart(content=prefixo + texto)]))
    return saida


def _custo(novas: list[ModelMessage]) -> Decimal | None:
    total = Decimal(0)
    for mensagem in novas:
        if not isinstance(mensagem, ModelResponse):
            continue
        try:
            total += Decimal(str(mensagem.cost().total_price))
        except Exception:
            return None
    return total


async def roda_turno(
    agente: "Agente",
    anteriores: list["Mensagem"],
    pendentes: list["Mensagem"],
    modelo: "Model | None" = None,
) -> ResultadoTurno:
    ia = Agent(
        modelo or modelo_de_resposta(agente.modelo_conversa, agente.modelo_fallback),
        output_type=Resposta,
        instructions=[
            le_prompt(agente),
            INSTRUCAO_DE_SAIDA.format(n=agente.max_mensagens_por_resposta),
        ],
    )
    entrada = "\n".join(m.texto or f"[{m.tipo} sem texto]" for m in pendentes)
    resultado = await ia.run(entrada, message_history=historico(anteriores))
    novas = resultado.new_messages()
    return ResultadoTurno(
        mensagens=resultado.output.mensagens,
        tokens_entrada=resultado.usage.input_tokens,
        tokens_saida=resultado.usage.output_tokens,
        custo_estimado=_custo(novas),
        tools_chamadas=[
            parte.tool_name
            for m in novas
            if isinstance(m, ModelResponse)
            for parte in m.parts
            if isinstance(parte, ToolCallPart) and not parte.tool_name.startswith("final_result")
        ],
    )
