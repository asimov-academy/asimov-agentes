"""Preset de ritmo no agente.

Aditiva. Todo agente que já existe nasce em `natural`, que é o ritmo dos números padrão (buffer de
8 s, 6 caracteres por segundo e teto de 20 s). Quem tinha número próprio vira `manual` na primeira
edição, que é quando a tela precisa dizer a verdade.

Revision ID: 0022
Revises: 0021
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = '0022'
down_revision: str | None = '0021'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column('agente', sa.Column('ritmo', sa.String(length=20), server_default='natural', nullable=False))


def downgrade() -> None:
    op.drop_column('agente', 'ritmo')
