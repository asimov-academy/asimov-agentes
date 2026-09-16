from datetime import datetime

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from app.plataforma.banco import Base, ComCriacao, ComId


class Cliente(ComId, ComCriacao, Base):
    __tablename__ = "cliente"

    nome: Mapped[str] = mapped_column(String(200))
    slug: Mapped[str] = mapped_column(String(200), unique=True)
    ativo: Mapped[bool] = mapped_column(default=True)
    removido_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
