from datetime import datetime

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from app.plataforma.banco import Base, ComCriacao, ComId, agora


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

    nome: Mapped[str] = mapped_column(String(120), default="")
    """Como o operador se chama. Aparece no menu; vazio, o painel diz só "Operador"."""
    email: Mapped[str] = mapped_column(String(200), default="")
    """Contato do operador. Não serve para entrar (a senha é a única credencial) e não sai em log."""


class EspacoTrabalho(ComId, ComCriacao, Base):
    """O espaço de trabalho: como esta instalação se chama e de quem ela é.

    Uma linha só, pela mesma razão do `UsuarioPainel`: a instalação é de quem tem a VPS. Serve para
    o operador que atende várias empresas reconhecer de qual instalação é a aba aberta, e os dados
    do negócio são os de quem opera, não os das empresas atendidas, que moram em `clientes/`.
    """

    __tablename__ = "espaco_trabalho"

    unico: Mapped[bool] = mapped_column(default=True, unique=True)
    nome: Mapped[str] = mapped_column(String(120), default="")
    """O que aparece no menu no lugar de ASIMOV. Vazio, fica ASIMOV."""
    sigla: Mapped[str] = mapped_column(String(2), default="")
    """Até duas letras, no quadrado da marca. Vazio, sai a primeira letra do nome."""

    negocio_nome: Mapped[str] = mapped_column(String(200), default="")
    negocio_documento: Mapped[str] = mapped_column(String(40), default="")
    negocio_email: Mapped[str] = mapped_column(String(200), default="")
    negocio_telefone: Mapped[str] = mapped_column(String(40), default="")
    negocio_site: Mapped[str] = mapped_column(String(300), default="")

    atualizado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=agora, onupdate=agora
    )
