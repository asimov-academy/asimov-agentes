"""Modelos por função e construção do modelo com a chave da configuração.

Nome de modelo sempre no formato `provedor:modelo`. Cada função (resposta, fallback, visão,
transcrição) pode usar um provedor diferente, e a escolha é de cada agente. A chave vem de
`ia/chaves.py` (banco, ou `.env` de instalação antiga) e é passada explicitamente ao provider.
"""

from typing import TYPE_CHECKING

from app.plataforma.config import Config, config

if TYPE_CHECKING:
    from pydantic_ai.models import Model

PROVEDORES = ("openai", "anthropic", "gemini", "groq")
PROVEDORES_TRANSCRICAO = ("openai", "gemini", "groq")


class ModeloInvalido(ValueError):
    pass


def provedor_de(nome_modelo: str) -> str:
    provedor, separador, modelo = nome_modelo.partition(":")
    if not separador or not modelo or provedor not in PROVEDORES:
        raise ModeloInvalido(f"modelo {nome_modelo!r} fora do formato provedor:modelo")
    return provedor


# Só o fallback pode ficar sem modelo: é o segundo provedor, e nem toda instalação quer um.
MODELOS_OPCIONAIS = frozenset({"modelo_fallback"})


def valida_modelos(modelos: dict[str, str | None], cfg: Config | None = None) -> None:
    """Recusa modelo de provedor sem chave e campo obrigatório vazio.

    Vazio passava direto e era gravado: o agente ficava com `modelo_conversa: ""`, que não resolve
    modelo nenhum, e só dava erro no turno seguinte (auditoria de 2026-09-18, A12).
    """
    from app.ia import chaves

    cfg = cfg or config()
    for campo, nome in modelos.items():
        if nome is None or not str(nome).strip():
            if campo in MODELOS_OPCIONAIS:
                continue
            raise ModeloInvalido(f"{campo} não pode ficar vazio")
        provedor = provedor_de(nome)
        if campo == "modelo_transcricao" and provedor not in PROVEDORES_TRANSCRICAO:
            raise ModeloInvalido(f"{provedor} não transcreve áudio; use openai, gemini ou groq")
        if not chaves.chave_do_provedor(provedor, cfg):
            raise ModeloInvalido(f"{campo} usa {provedor}, mas a instalação não tem essa chave")


def construir_modelo(nome_modelo: str) -> "Model":
    provedor = provedor_de(nome_modelo)
    modelo = nome_modelo.split(":", 1)[1]
    from app.ia import chaves

    chave = chaves.chave_do_provedor(provedor)

    if provedor == "openai":
        # Responses, não Chat Completions: só nela a OpenAI tem busca na web nativa.
        from pydantic_ai.models.openai import OpenAIResponsesModel, OpenAIResponsesModelSettings
        from pydantic_ai.providers.openai import OpenAIProvider

        openai = OpenAIResponsesModel(modelo, provider=OpenAIProvider(api_key=chave))
        esforco = config().openai_raciocinio or "low"
        perfil = openai.profile
        if esforco == "none" or not perfil.get("openai_supports_reasoning") or perfil.get("openai_reasoning_enabled_by_default"):
            return openai
        return OpenAIResponsesModel(
            modelo,
            provider=OpenAIProvider(api_key=chave),
            settings=OpenAIResponsesModelSettings(openai_reasoning_effort=esforco),
        )
    if provedor == "anthropic":
        from pydantic_ai.models.anthropic import AnthropicModel
        from pydantic_ai.providers.anthropic import AnthropicProvider

        return AnthropicModel(modelo, provider=AnthropicProvider(api_key=chave))
    if provedor == "groq":
        from pydantic_ai.models.groq import GroqModel
        from pydantic_ai.providers.groq import GroqProvider

        groq = GroqModel(modelo, provider=GroqProvider(api_key=chave))
        if groq.profile.get("groq_always_has_web_search_builtin_tool"):
            return groq
        # O perfil da Groq anuncia busca nativa em todo modelo, mas só os `compound` têm: nos outros
        # a busca tem de cair na local, e não num erro na hora da resposta.
        from pydantic_ai.native_tools import WebSearchTool

        nativas = groq.profile.get("supported_native_tools", frozenset()) - {WebSearchTool}
        return GroqModel(
            modelo,
            provider=GroqProvider(api_key=chave),
            profile={**groq.profile, "supported_native_tools": nativas},
        )

    from pydantic_ai.models.google import GoogleModel
    from pydantic_ai.providers.google import GoogleProvider

    return GoogleModel(modelo, provider=GoogleProvider(api_key=chave))


def modelo_de_resposta(principal: str, fallback: str | None) -> "Model":
    """Com fallback, erro de API no principal (fora do ar, limite, chave) cai no segundo."""
    if not fallback:
        return construir_modelo(principal)
    from pydantic_ai.models.fallback import FallbackModel

    return FallbackModel(construir_modelo(principal), construir_modelo(fallback))
