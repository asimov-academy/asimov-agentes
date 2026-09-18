"""conta do operador no painel web

Uma linha só, criada no primeiro acesso com o código que `asimov painel` mostra no terminal.
A sessão não fica aqui: mora no Redis e expira sozinha.

Revision ID: 0014
Revises: 0013
Create Date: 2026-09-18 22:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = '0014'
down_revision: str | None = '0013'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        'usuario_painel',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('criado_em', sa.DateTime(timezone=True), nullable=False),
        sa.Column('senha', sa.String(length=300), nullable=False),
        sa.Column('ultimo_acesso_em', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_usuario_painel')),
    )


def downgrade() -> None:
    op.drop_table('usuario_painel')
