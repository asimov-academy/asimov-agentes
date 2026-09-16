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

    provedor_ia: str
    provedor_apoio: str = ""
    openai_api_key: str = ""
    anthropic_api_key: str = ""
    gemini_api_key: str = ""

    diretorio_prompts: Path = Path("/app/prompts")
    diretorio_modelos: Path = Path("/app/modelos")

    log_nivel: str = "INFO"
    lock_ttl_segundos: int = 90
    tentativas_extra_modelo: int = 2

    def chave_do_provedor(self, provedor: str) -> str:
        return {
            "openai": self.openai_api_key,
            "anthropic": self.anthropic_api_key,
            "gemini": self.gemini_api_key,
        }.get(provedor, "")

    def url_webhook(self, canal: str, token: str) -> str:
        return f"https://{self.subdominio_bot}/webhook/{canal}/{token}"


@lru_cache
def config() -> Config:
    return Config()  # type: ignore[call-arg]
