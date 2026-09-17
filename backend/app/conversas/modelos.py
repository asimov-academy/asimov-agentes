import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.plataforma.banco import Base, ComCriacao, ComId, agora


class Contato(ComId, ComCriacao, Base):
    __tablename__ = "contato"
    __table_args__ = (UniqueConstraint("agente_id", "id_externo"),)

    cliente_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("cliente.id"), index=True)
    agente_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("agente.id"))
    id_externo: Mapped[str] = mapped_column(String(200))
    nome: Mapped[str | None] = mapped_column(String(200))
    telefone: Mapped[str | None] = mapped_column(String(50))
    ultima_mensagem_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=agora)


class Conversa(ComId, ComCriacao, Base):
    __tablename__ = "conversa"
    __table_args__ = (UniqueConstraint("agente_id", "id_externo"),)

    cliente_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("cliente.id"), index=True)
    agente_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("agente.id"))
    contato_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("contato.id"))
    id_externo: Mapped[str] = mapped_column(String(200))
    canal: Mapped[str] = mapped_column(String(20))
    """Por onde a conversa acontece: o canal do agente ou `nativo` na conversa de teste do terminal."""
    status: Mapped[str] = mapped_column(String(20), default="agente")
    respondido_ate: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    """Hora da última mensagem do contato que um turno respondeu. O que chega durante o turno fica depois."""
    atualizado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=agora, onupdate=agora
    )


class Mensagem(ComId, ComCriacao, Base):
    __tablename__ = "mensagem"
    __table_args__ = (
        # Reentrega de webhook não pode virar segunda mensagem nem segunda resposta.
        Index(
            "uq_mensagem_conversa_id_externo",
            "conversa_id",
            "id_externo",
            unique=True,
            postgresql_where="id_externo IS NOT NULL",
        ),
        Index("ix_mensagem_conversa_criado", "conversa_id", "criado_em"),
    )

    cliente_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("cliente.id"), index=True)
    conversa_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("conversa.id"))
    direcao: Mapped[str] = mapped_column(String(10))
    autor: Mapped[str] = mapped_column(String(10))
    tipo: Mapped[str] = mapped_column(String(20), default="texto")
    texto: Mapped[str | None] = mapped_column(Text)
    texto_extraido: Mapped[str | None] = mapped_column(Text)
    anexo: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    """Anexo do canal e, depois do turno, `situacao` da leitura (ver midia/servico.py)."""
    midia_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("midia.id"))
    id_externo: Mapped[str | None] = mapped_column(String(200))
