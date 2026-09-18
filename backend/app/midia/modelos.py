import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.plataforma.banco import Base, ComCriacao, ComId


class Midia(ComId, ComCriacao, Base):
    """Arquivo de contato já lido. O cache é por cliente: o mesmo hash em outro cliente é outro registro."""

    __tablename__ = "midia"
    __table_args__ = (UniqueConstraint("cliente_id", "hash_sha256"),)

    cliente_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("cliente.id"), index=True)
    hash_sha256: Mapped[str] = mapped_column(String(64))
    tipo_mime: Mapped[str] = mapped_column(String(100))
    tamanho_bytes: Mapped[int]
    caminho_arquivo: Mapped[str] = mapped_column(String(500))
    arquivo_apagado_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    """O arquivo some do disco na limpeza do dia seguinte; o texto lido dele fica, que é o que a
    IA usa."""
    resultado: Mapped[str] = mapped_column(Text)
    metadados: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
