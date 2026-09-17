import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.ia import ferramentas
from app.plataforma.banco import Base, ComCriacao, ComId, agora



class Agente(ComId, ComCriacao, Base):
    __tablename__ = "agente"
    __table_args__ = (UniqueConstraint("cliente_id", "slug"),)

    cliente_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("cliente.id"), index=True)
    nome: Mapped[str] = mapped_column(String(200))
    slug: Mapped[str] = mapped_column(String(200))
    canal: Mapped[str] = mapped_column(String(20))

    credenciais_cifradas: Mapped[str] = mapped_column(Text)
    token_webhook_hash: Mapped[str] = mapped_column(String(64), unique=True)
    token_webhook_cifrado: Mapped[str] = mapped_column(Text)

    arquivo_prompt: Mapped[str] = mapped_column(String(500))
    arquivo_prompt_handoff: Mapped[str] = mapped_column(String(500))

    modelo_conversa: Mapped[str] = mapped_column(String(100))
    modelo_fallback: Mapped[str | None] = mapped_column(String(100))
    modelo_auxiliar: Mapped[str] = mapped_column(String(100))
    modelo_visao: Mapped[str] = mapped_column(String(100))
    modelo_transcricao: Mapped[str] = mapped_column(String(100))

    buffer_segundos: Mapped[int] = mapped_column(default=8)
    max_mensagens_por_resposta: Mapped[int] = mapped_column(default=3)
    digitacao_caracteres_por_segundo: Mapped[int] = mapped_column(default=6, server_default="6")
    """Velocidade com que o agente "digita": define quanto o digitando dura antes de cada mensagem."""
    digitacao_maximo_segundos: Mapped[int] = mapped_column(default=20, server_default="20")
    ferramentas: Mapped[list[str]] = mapped_column(
        JSONB, default=lambda: list(ferramentas.PADRAO), server_default='["calculadora", "busca_web"]'
    )
    """Nomes do catálogo de `ia/ferramentas/registro.py` ligados neste agente."""

    handoff_destino: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    handoff_template: Mapped[str | None] = mapped_column(String(200))
    retomada_automatica_horas: Mapped[int | None]

    ativo: Mapped[bool] = mapped_column(default=True)
    atualizado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=agora, onupdate=agora
    )
    removido_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
