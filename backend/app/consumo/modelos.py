import uuid
from decimal import Decimal
from typing import Any

from sqlalchemy import ForeignKey, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.plataforma.banco import Base, ComCriacao, ComId


class Turno(ComId, ComCriacao, Base):
    __tablename__ = "turno"

    cliente_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("cliente.id"), index=True)
    conversa_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("conversa.id"), index=True)
    modelo: Mapped[str] = mapped_column(String(100))
    tokens_entrada: Mapped[int] = mapped_column(default=0)
    tokens_saida: Mapped[int] = mapped_column(default=0)
    custo_estimado: Mapped[Decimal | None] = mapped_column(Numeric(12, 6))
    latencia_ms: Mapped[int] = mapped_column(default=0)
    tools_chamadas: Mapped[list[str] | None] = mapped_column(JSONB)
    erro: Mapped[str | None] = mapped_column(Text)


class Falha(ComId, ComCriacao, Base):
    __tablename__ = "falha"

    cliente_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("cliente.id"), index=True)
    agente_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("agente.id"))
    tipo: Mapped[str] = mapped_column(String(100), index=True)
    detalhe: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
