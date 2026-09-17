import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.plataforma.banco import Base, ComId, agora


class Handoff(ComId, Base):
    """Conversa passada para humano. Aberto enquanto `retomado_em` está vazio."""

    __tablename__ = "handoff"
    __table_args__ = (
        UniqueConstraint("agente_id", "codigo"),
        # Um handoff aberto por conversa: é o que torna a transferência idempotente.
        Index(
            "uq_handoff_conversa_aberto",
            "conversa_id",
            unique=True,
            postgresql_where="retomado_em IS NULL",
        ),
    )

    cliente_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("cliente.id"), index=True)
    agente_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("agente.id"))
    conversa_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("conversa.id"))
    motivo: Mapped[str] = mapped_column(Text)
    resumo: Mapped[str] = mapped_column(Text)
    codigo: Mapped[str] = mapped_column(String(12))
    """Usado no `/retomar <código>` dos canais diretos (fase 5). No Chatwoot só aparece na nota."""
    destino: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    iniciado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=agora)
    retomar_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    retomado_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    retomado_por: Mapped[str | None] = mapped_column(String(20))
    """`chatwoot`, `comando`, `tempo` ou `operador` (menu)."""
