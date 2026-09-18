"""o template do aviso de handoff virou parte do destino

No WhatsApp oficial, o template é como se avisa o destino fora da janela de 24 horas: mora em
`handoff_destino`, junto do número, e não numa coluna à parte que nenhum canal lia.

Revision ID: 0012
Revises: 0011
Create Date: 2026-09-18 12:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = '0012'
down_revision: str | None = '0011'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_column('agente', 'handoff_template')


def downgrade() -> None:
    op.add_column('agente', sa.Column('handoff_template', sa.String(length=200), nullable=True))
