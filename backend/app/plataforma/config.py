from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Config(BaseSettings):
    """Tudo vem do ambiente. Segredo sem valor impede o boot."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str
    redis_url: str
    subdominio_bot: str

    chave_api_admin: str
    chave_criptografia: str

    # Modelos padrão da instalação, no formato provedor:modelo, escolhidos no setup.
    modelo_conversa: str
    modelo_fallback: str = ""
    modelo_visao: str
    modelo_transcricao: str

    openai_api_key: str = ""
    anthropic_api_key: str = ""
    gemini_api_key: str = ""
    groq_api_key: str = ""

    diretorio_prompts: Path = Path("/app/prompts")
    diretorio_modelos: Path = Path("/app/modelos")
    diretorio_midia: Path = Path("/var/lib/asimov/midia")

    log_nivel: str = "INFO"
    # Cobre ler mídia e responder no mesmo turno; abaixo do job_timeout do worker.
    lock_ttl_segundos: int = 240
    tentativas_extra_modelo: int = 2
    # Teto por turno: o gpt-5.1 chegou a chamar a tool de handoff 16 vezes num turno (102 mil tokens).
    limite_chamadas_modelo_por_turno: int = 6
    limite_tools_por_turno: int = 8
    # Soma do digitando de uma resposta; abaixo do lock, que também cobre mídia e modelo.
    digitacao_total_maximo_segundos: int = 90

    midia_limite_bytes: int = 20 * 1024 * 1024
    midia_limite_audio_segundos: int = 5 * 60
    midia_paginas_pdf_visao: int = 10
    midia_caracteres_extraidos: int = 12000

    def chave_do_provedor(self, provedor: str) -> str:
        return {
            "openai": self.openai_api_key,
            "anthropic": self.anthropic_api_key,
            "gemini": self.gemini_api_key,
            "groq": self.groq_api_key,
        }.get(provedor, "")

    def url_webhook(self, canal: str, token: str) -> str:
        return f"https://{self.subdominio_bot}/webhook/{canal}/{token}"


@lru_cache
def config() -> Config:
    return Config()  # type: ignore[call-arg]
