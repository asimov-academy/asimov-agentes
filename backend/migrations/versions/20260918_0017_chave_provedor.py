"""chave de API dos provedores de IA, cifrada no banco

O modelo deixou de ser pergunta da instalação e virou escolha de cada agente. A chave do provedor
precisa valer na hora em que o operador a informa, no terminal ou no painel, e o `.env` só é lido
no boot. Chave que já estava no `.env` continua valendo.

Revision ID: 0017
Revises: 0016
Create Date: 2026-09-18 23:50:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = '0017'
down_revision: str | None = '0016'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        'chave_provedor',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('provedor', sa.String(length=20), nullable=False),
        sa.Column('chave_cifrada', sa.Text(), nullable=False),
        sa.Column('atualizado_em', sa.DateTime(timezone=True), nullable=False),
        sa.Column('criado_em', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_chave_provedor')),
        sa.UniqueConstraint('provedor', name=op.f('uq_chave_provedor_provedor')),
    )


def downgrade() -> None:
    op.drop_table('chave_provedor')
