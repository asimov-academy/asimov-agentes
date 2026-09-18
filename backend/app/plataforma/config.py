from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Config(BaseSettings):
    """Tudo vem do ambiente. Segredo sem valor impede o boot."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str
    redis_url: str
    subdominio_bot: str
    # E-mail que o operador deu ao Let's Encrypt; serve de contato na página de privacidade.
    email_ssl: str = ""

    chave_api_admin: str
    chave_criptografia: str

    # Painel do operador no navegador, em app.<dominio>. Nasce desligado: quem escolhe o terminal na
    # instalação segue com a API exatamente como sempre foi, sem rota nova e sem host novo no Caddy.
    painel_ativo: bool = False
    subdominio_app: str = ""

    # Modelos padrão da instalação, no formato provedor:modelo, escolhidos no setup.
    modelo_conversa: str
    modelo_fallback: str = ""
    modelo_visao: str
    modelo_transcricao: str

    # WAHA (WhatsApp na própria VPS): container sem porta pública, subido no primeiro agente WAHA.
    # A chave é gerada na instalação, mesmo sem o container: assim ligar a WAHA depois não reinicia a API.
    waha_url: str = "http://waha:3000"
    waha_api_key: str = ""

    openai_api_key: str = ""
    anthropic_api_key: str = ""
    gemini_api_key: str = ""
    groq_api_key: str = ""
    # Nível de raciocínio dos modelos da OpenAI que vêm com ele desligado (gpt-5.1). Desligado, o modelo
    # tinha a busca e não usava o resultado; com `low` buscou e respondeu (teste na VPS, v0.8.5).
    # Vazio vale `low`; `none` mantém o padrão do modelo. Modelos que já raciocinam ou não aceitam ficam como estão.
    openai_raciocinio: Literal["", "none", "minimal", "low", "medium", "high"] = "low"

    diretorio_prompts: Path = Path("/app/prompts")
    diretorio_modelos: Path = Path("/app/modelos")
    diretorio_midia: Path = Path("/var/lib/asimov/midia")

    log_nivel: str = "INFO"
    # Cobre ler mídia e responder no mesmo turno, e passa do `job_timeout` do worker (300 s) de
    # propósito: com o lock vencendo antes, outro turno entrava na mesma conversa enquanto o
    # primeiro ainda enviava (auditoria de 2026-09-18, A06). Quem interrompe job longo é o arq.
    lock_ttl_segundos: int = 360
    tentativas_extra_modelo: int = 2
    # Teto por turno: o gpt-5.1 chegou a chamar a tool de handoff 16 vezes num turno (102 mil tokens).
    limite_chamadas_modelo_por_turno: int = 6
    limite_tools_por_turno: int = 8
    # Soma do digitando de uma resposta; abaixo do lock, que também cobre mídia e modelo.
    digitacao_total_maximo_segundos: int = 90

    # O arquivo é insumo: depois de virar texto, ninguém mais o lê. A limpeza é diária, então na
    # prática ele dura de um a dois dias, o que basta para conferir um atendimento estranho.
    # Idioma dos áudios que chegam. Sem isso o transcritor adivinha pelo som e erra em áudio curto
    # ou com ruído: "Boa noite" voltou como russo no teste da v0.14.0. Vazio deixa ele adivinhar.
    idioma_audio: str = "pt"
    midia_horas_no_disco: int = 24
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

    def url_publica(self) -> str:
        return f"https://{self.subdominio_bot}"

    def url_webhook(self, canal: str, token: str) -> str:
        return f"{self.url_publica()}/webhook/{canal}/{token}"

    def url_webhook_interna(self, canal: str, token: str) -> str:
        """Para o canal que roda na própria VPS (WAHA): não passa pelo Caddy nem pela internet."""
        return f"http://api:8000/webhook/{canal}/{token}"


@lru_cache
def config() -> Config:
    return Config()  # type: ignore[call-arg]
