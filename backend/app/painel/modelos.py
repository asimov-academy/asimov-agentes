from datetime import datetime

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from app.plataforma.banco import Base, ComCriacao, ComId


class UsuarioPainel(ComId, ComCriacao, Base):
    """O operador do painel. Uma linha só: quem administra a instalação é quem tem a VPS.

    A senha nasce no primeiro acesso, com o código de uso único que o `asimov painel` mostra no
    terminal. Sem essa conta, o painel não deixa entrar e nem oferece cadastro: quem descobrir o
    endereço antes do operador não tem o que fazer com ele.
    """

    __tablename__ = "usuario_painel"

    unico: Mapped[bool] = mapped_column(default=True, unique=True)
    """Uma linha só, garantida pelo banco. Conferir a ausência antes de inserir não basta: dois
    cadastros ao mesmo tempo passavam os dois pela consulta (revisão da auditoria de 2026-09-18)."""
    senha: Mapped[str] = mapped_column(String(300))
    """Formato `scrypt$n$r$p$salt$hash`, tudo em hexadecimal. Ver painel/servico.py."""
    ultimo_acesso_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
