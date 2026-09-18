"""Funil de oportunidades: as etapas do kanban, os cartões e as etiquetas.

Tudo por empresa (`cliente_id`), como o resto da plataforma: quem atende várias empresas tem um
funil para cada uma, e nenhuma consulta cruza a linha. As etapas são do operador, não fixas no
código: kanban com coluna fixa serve para um negócio só.
"""

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Index, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.plataforma.banco import Base, ComCriacao, ComId, agora


class EtapaFunil(ComId, ComCriacao, Base):
    """Uma coluna do kanban. A ordem é do operador, e é ela que desenha o quadro."""

    __tablename__ = "etapa_funil"
    __table_args__ = (UniqueConstraint("cliente_id", "nome"),)

    cliente_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("cliente.id"), index=True)
    nome: Mapped[str] = mapped_column(String(60))
    ordem: Mapped[int] = mapped_column(default=0)
    ganha: Mapped[bool] = mapped_column(default=False)
    """A coluna que fecha o negócio. Serve para somar o ganho do período sem adivinhar pelo nome."""
    perdida: Mapped[bool] = mapped_column(default=False)


class Etiqueta(ComId, ComCriacao, Base):
    """Marcação livre, para o operador cortar o funil do jeito dele.

    A cor é o **nome de um token** da paleta do painel, nunca um hexadecimal: cor solta na tela é
    proibida no projeto, e etiqueta colorida por fora da paleta estraga o quadro inteiro.
    """

    __tablename__ = "etiqueta"
    __table_args__ = (UniqueConstraint("cliente_id", "nome"),)

    cliente_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("cliente.id"), index=True)
    nome: Mapped[str] = mapped_column(String(40))
    cor: Mapped[str] = mapped_column(String(20), default="ciano")


class Oportunidade(ComId, ComCriacao, Base):
    """Um cartão do kanban: o que está em jogo com um contato.

    O contato é opcional: nem toda oportunidade nasce de uma conversa, e contato apagado não pode
    levar o histórico do funil junto.
    """

    __tablename__ = "oportunidade"
    __table_args__ = (Index("ix_oportunidade_cliente_etapa", "cliente_id", "etapa_id"),)

    cliente_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("cliente.id"), index=True)
    etapa_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("etapa_funil.id"))
    contato_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("contato.id"))
    titulo: Mapped[str] = mapped_column(String(200))
    valor: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0"))
    nota: Mapped[str] = mapped_column(Text, default="")
    ordem: Mapped[int] = mapped_column(default=0)
    """Posição dentro da coluna. Arrastar dois cartões mexe só nos dois."""
    atualizado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=agora, onupdate=agora
    )


class OportunidadeEtiqueta(Base):
    """Quais etiquetas o cartão tem. Tabela de ligação, sem id próprio."""

    __tablename__ = "oportunidade_etiqueta"

    oportunidade_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("oportunidade.id", ondelete="CASCADE"), primary_key=True
    )
    etiqueta_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("etiqueta.id", ondelete="CASCADE"), primary_key=True
    )
