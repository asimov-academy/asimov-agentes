"""Base de conhecimento: o documento que o operador envia e os trechos que o agente busca.

O vetor tem dimensão fixa na coluna, então o modelo de embeddings é da instalação e não do agente
(spec/arquitetura.md). Os 1536 valem para os dois modelos que a plataforma usa: o
`text-embedding-3-small` da OpenAI nasce assim, e o `gemini-embedding-001` aceita pedir esse
tamanho. Trocar de modelo obriga a reprocessar todos os trechos.
"""

import uuid
from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.plataforma.banco import Base, ComCriacao, ComId

DIMENSAO = 1536


class Documento(ComId, ComCriacao, Base):
    __tablename__ = "documento"
    __table_args__ = (
        # Hash por agente: o mesmo arquivo pode servir a dois agentes, e mandar duas vezes para o
        # mesmo é engano. Só conta o que não foi removido, senão remover e reenviar ficaria travado.
        Index(
            "uq_documento_agente_hash",
            "agente_id",
            "hash_sha256",
            unique=True,
            postgresql_where="removido_em IS NULL",
        ),
    )

    cliente_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("cliente.id"), index=True)
    agente_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("agente.id"), index=True)
    nome_arquivo: Mapped[str] = mapped_column(String(300))
    caminho_arquivo: Mapped[str] = mapped_column(String(500), default="")
    """Vazio no material que nasce escrito no painel (texto e site): não há arquivo no disco."""
    origem: Mapped[str] = mapped_column(String(20), default="documento")
    """Como o operador ensinou: `documento`, `texto` ou `site`. Muda só o que a tela mostra."""
    hash_sha256: Mapped[str] = mapped_column(String(64))
    tipo_mime: Mapped[str] = mapped_column(String(120), default="text/plain")
    status: Mapped[str] = mapped_column(String(20), default="processando")
    """`processando`, `pronto` ou `erro`."""
    erro: Mapped[str] = mapped_column(Text, default="")
    """Por que a ingestão falhou, em português, pronto para a tela."""
    total_trechos: Mapped[int] = mapped_column(Integer, default=0)
    removido_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Trecho(ComId, ComCriacao, Base):
    __tablename__ = "trecho"
    __table_args__ = (
        UniqueConstraint("documento_id", "ordem"),
        Index("ix_trecho_agente", "cliente_id", "agente_id"),
    )

    cliente_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("cliente.id"), index=True)
    agente_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("agente.id"))
    documento_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("documento.id"))
    ordem: Mapped[int] = mapped_column(Integer)
    texto: Mapped[str] = mapped_column(Text)
    embedding: Mapped[list[float]] = mapped_column(Vector(DIMENSAO))


class ConfiguracaoEmbeddings(Base):
    """Uma linha da instalação, para não misturar espaços vetoriais."""
    __tablename__ = "configuracao_embeddings"
    __table_args__ = (
        CheckConstraint("id = 1", name="linha_unica"),
    )
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=False)
    modelo: Mapped[str] = mapped_column(String(100))
