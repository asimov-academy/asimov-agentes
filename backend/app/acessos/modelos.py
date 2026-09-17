from datetime import datetime

from sqlalchemy import DateTime, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.plataforma.banco import Base, ComCriacao, ComId, agora


class AcessoCanal(ComId, ComCriacao, Base):
    """Acesso do operador a um canal (no Chatwoot, o token de administrador), guardado cifrado.

    É da instalação, não de um cliente: o mesmo Chatwoot atende empresas diferentes na revenda.
    """

    __tablename__ = "acesso_canal"
    __table_args__ = (UniqueConstraint("canal", "endereco"),)

    canal: Mapped[str] = mapped_column(String(20))
    endereco: Mapped[str] = mapped_column(String(500))
    """Onde o acesso vale (URL do Chatwoot)."""
    acesso_cifrado: Mapped[str] = mapped_column(Text)
    atualizado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=agora, onupdate=agora
    )
