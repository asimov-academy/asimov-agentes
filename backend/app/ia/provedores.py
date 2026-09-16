"""Modelos padrão por provedor e construção do modelo com a chave da configuração.

Nome de modelo sempre no formato `provedor:modelo`. A chave é passada explicitamente ao
provider: o pydantic-settings não exporta o .env para o ambiente do processo.
"""

from typing import TYPE_CHECKING

from app.plataforma.config import Config, config

if TYPE_CHECKING:
    from pydantic_ai.models import Model

PROVEDORES = ("openai", "anthropic", "gemini")
PROVEDORES_DE_APOIO = ("openai", "gemini")

PADROES: dict[str, dict[str, str]] = {
    "openai": {
        "modelo_conversa": "openai:gpt-5.5",
        "modelo_auxiliar": "openai:gpt-5-mini",
        "modelo_visao": "openai:gpt-5-mini",
        "modelo_transcricao": "openai:whisper-1",
    },
    "gemini": {
        "modelo_conversa": "gemini:gemini-2.5-pro",
        "modelo_auxiliar": "gemini:gemini-2.5-flash",
        "modelo_visao": "gemini:gemini-2.5-flash",
        "modelo_transcricao": "gemini:gemini-2.5-flash",
    },
    "anthropic": {
        "modelo_conversa": "anthropic:claude-sonnet-5",
        "modelo_auxiliar": "anthropic:claude-haiku-4-5",
        "modelo_visao": "anthropic:claude-sonnet-5",
    },
}


class ModeloInvalido(ValueError):
    pass


def modelos_padrao(cfg: Config | None = None) -> dict[str, str]:
    cfg = cfg or config()
    modelos = dict(PADROES[cfg.provedor_ia])
    if "modelo_transcricao" not in modelos:
        apoio = cfg.provedor_apoio or "openai"
        modelos["modelo_transcricao"] = PADROES[apoio]["modelo_transcricao"]
    return modelos


def provedor_de(nome_modelo: str) -> str:
    provedor, separador, modelo = nome_modelo.partition(":")
    if not separador or not modelo or provedor not in PROVEDORES:
        raise ModeloInvalido(f"modelo {nome_modelo!r} fora do formato provedor:modelo")
    return provedor


def valida_modelos(modelos: dict[str, str], cfg: Config | None = None) -> None:
    cfg = cfg or config()
    for campo, nome in modelos.items():
        provedor = provedor_de(nome)
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

    from pydantic_ai.models.google import GoogleModel
    from pydantic_ai.providers.google import GoogleProvider

    return GoogleModel(modelo, provider=GoogleProvider(api_key=chave))
