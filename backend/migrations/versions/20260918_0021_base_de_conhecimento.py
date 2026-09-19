"""Base de conhecimento: documento, trecho e a extensão de vetores.

Aditiva: duas tabelas novas e nenhuma coluna mexida. Agente que já existe segue sem base, e o
`CREATE EXTENSION` é o que o Postgres da instalação já traz (imagem `pgvector/pgvector:pg16`).

Revision ID: 0021
Revises: 0020
"""

from collections.abc import Sequence

import pgvector.sqlalchemy
import sqlalchemy as sa
from alembic import op


revision: str = '0021'
down_revision: str | None = '0020'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute('CREATE EXTENSION IF NOT EXISTS vector')
    op.create_table(
        'documento',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('criado_em', sa.DateTime(timezone=True), nullable=False),
        sa.Column('cliente_id', sa.Uuid(), nullable=False),
        sa.Column('agente_id', sa.Uuid(), nullable=False),
        sa.Column('nome_arquivo', sa.String(length=300), nullable=False),
        sa.Column('caminho_arquivo', sa.String(length=500), nullable=False),
        sa.Column('origem', sa.String(length=20), nullable=False),
        sa.Column('hash_sha256', sa.String(length=64), nullable=False),
        sa.Column('tipo_mime', sa.String(length=120), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('erro', sa.Text(), nullable=False),
        sa.Column('total_trechos', sa.Integer(), nullable=False),
        sa.Column('removido_em', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['agente_id'], ['agente.id'], name=op.f('fk_documento_agente_id_agente')),
        sa.ForeignKeyConstraint(['cliente_id'], ['cliente.id'], name=op.f('fk_documento_cliente_id_cliente')),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_documento')),
    )
    op.create_index(op.f('ix_documento_agente_id'), 'documento', ['agente_id'], unique=False)
    op.create_index(op.f('ix_documento_cliente_id'), 'documento', ['cliente_id'], unique=False)
    op.create_index(
        'uq_documento_agente_hash',
        'documento',
        ['agente_id', 'hash_sha256'],
        unique=True,
        postgresql_where=sa.text('removido_em IS NULL'),
    )
    op.create_table(
        'trecho',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('criado_em', sa.DateTime(timezone=True), nullable=False),
        sa.Column('cliente_id', sa.Uuid(), nullable=False),
        sa.Column('agente_id', sa.Uuid(), nullable=False),
        sa.Column('documento_id', sa.Uuid(), nullable=False),
        sa.Column('ordem', sa.Integer(), nullable=False),
        sa.Column('texto', sa.Text(), nullable=False),
        sa.Column('embedding', pgvector.sqlalchemy.Vector(dim=1536), nullable=False),
        sa.ForeignKeyConstraint(['agente_id'], ['agente.id'], name=op.f('fk_trecho_agente_id_agente')),
        sa.ForeignKeyConstraint(['cliente_id'], ['cliente.id'], name=op.f('fk_trecho_cliente_id_cliente')),
        sa.ForeignKeyConstraint(['documento_id'], ['documento.id'], name=op.f('fk_trecho_documento_id_documento')),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_trecho')),
        sa.UniqueConstraint('documento_id', 'ordem', name=op.f('uq_trecho_documento_id')),
    )
    op.create_index(op.f('ix_trecho_cliente_id'), 'trecho', ['cliente_id'], unique=False)
    op.create_index('ix_trecho_agente', 'trecho', ['cliente_id', 'agente_id'], unique=False)


def downgrade() -> None:
    op.drop_table('trecho')
    op.drop_table('documento')
