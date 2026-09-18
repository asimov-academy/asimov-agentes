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


class ChaveProvedor(ComId, ComCriacao, Base):
    """Chave de API de um provedor de IA, guardada cifrada.

    É da instalação: o operador informa uma vez, ao criar um agente pelo terminal ou pelo painel, e
    todo agente que usar o provedor aproveita. Fica no banco e não no `.env` para valer na hora,
    sem reconstruir nem reiniciar a API.
    """

    __tablename__ = "chave_provedor"
    __table_args__ = (UniqueConstraint("provedor"),)

    provedor: Mapped[str] = mapped_column(String(20))
    chave_cifrada: Mapped[str] = mapped_column(Text)
    atualizado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=agora, onupdate=agora
    )
