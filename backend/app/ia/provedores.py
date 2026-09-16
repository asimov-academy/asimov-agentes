"""Modelos por função e construção do modelo com a chave da configuração.

Nome de modelo sempre no formato `provedor:modelo`. Cada função (resposta, fallback, visão,
transcrição) pode usar um provedor diferente; os padrões vêm do setup e cada agente pode
trocar. A chave é passada explicitamente ao provider: o pydantic-settings não exporta o .env
para o ambiente do processo.
"""

from typing import TYPE_CHECKING

from app.plataforma.config import Config, config

if TYPE_CHECKING:
    from pydantic_ai.models import Model

PROVEDORES = ("openai", "anthropic", "gemini", "groq")
PROVEDORES_TRANSCRICAO = ("openai", "gemini", "groq")


class ModeloInvalido(ValueError):
    pass


def modelos_padrao(cfg: Config | None = None) -> dict[str, str | None]:
    cfg = cfg or config()
    return {
        "modelo_conversa": cfg.modelo_conversa,
        "modelo_fallback": cfg.modelo_fallback or None,
        "modelo_auxiliar": cfg.modelo_conversa,
        "modelo_visao": cfg.modelo_visao,
        "modelo_transcricao": cfg.modelo_transcricao,
    }


def provedor_de(nome_modelo: str) -> str:
    provedor, separador, modelo = nome_modelo.partition(":")
    if not separador or not modelo or provedor not in PROVEDORES:
        raise ModeloInvalido(f"modelo {nome_modelo!r} fora do formato provedor:modelo")
    return provedor


def valida_modelos(modelos: dict[str, str | None], cfg: Config | None = None) -> None:
    cfg = cfg or config()
    for campo, nome in modelos.items():
        if not nome:
            continue
        provedor = provedor_de(nome)
        if campo == "modelo_transcricao" and provedor not in PROVEDORES_TRANSCRICAO:
            raise ModeloInvalido(f"{provedor} não transcreve áudio; use openai, gemini ou groq")
        if not cfg.chave_do_provedor(provedor):
            raise ModeloInvalido(f"{campo} usa {provedor}, mas a instalação não tem essa chave")


def construir_modelo(nome_modelo: str) -> "Model":
    provedor = provedor_de(nome_modelo)
    modelo = nome_modelo.split(":", 1)[1]
    chave = config().chave_do_provedor(provedor)

    if provedor == "openai":
        from pydantic_ai.models.openai import OpenAIChatModel
        from pydantic_ai.providers.openai import OpenAIProvider

        return OpenAIChatModel(modelo, provider=OpenAIProvider(api_key=chave))
    if provedor == "anthropic":
        from pydantic_ai.models.anthropic import AnthropicModel
        from pydantic_ai.providers.anthropic import AnthropicProvider

        return AnthropicModel(modelo, provider=AnthropicProvider(api_key=chave))
    if provedor == "groq":
        from pydantic_ai.models.groq import GroqModel
        from pydantic_ai.providers.groq import GroqProvider

        return GroqModel(modelo, provider=GroqProvider(api_key=chave))

    from pydantic_ai.models.google import GoogleModel
    from pydantic_ai.providers.google import GoogleProvider

    return GoogleModel(modelo, provider=GoogleProvider(api_key=chave))


def modelo_de_resposta(principal: str, fallback: str | None) -> "Model":
    """Com fallback, erro de API no principal (fora do ar, limite, chave) cai no segundo."""
    if not fallback:
        return construir_modelo(principal)
    from pydantic_ai.models.fallback import FallbackModel

    return FallbackModel(construir_modelo(principal), construir_modelo(fallback))
