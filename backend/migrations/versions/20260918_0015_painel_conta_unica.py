"""uma conta só no painel, garantida pelo banco

Conferir a ausência antes de inserir não basta: dois cadastros ao mesmo tempo passavam os dois
pela consulta (revisão da auditoria de 2026-09-18).

Revision ID: 0015
Revises: 0014
Create Date: 2026-09-18 23:30:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = '0015'
down_revision: str | None = '0014'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        'usuario_painel',
        sa.Column('unico', sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.create_unique_constraint(op.f('uq_usuario_painel_unico'), 'usuario_painel', ['unico'])


def downgrade() -> None:
    op.drop_constraint(op.f('uq_usuario_painel_unico'), 'usuario_painel', type_='unique')
    op.drop_column('usuario_painel', 'unico')
