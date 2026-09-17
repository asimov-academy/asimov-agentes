"""canal da conversa

A conversa de teste no terminal fala pelo canal nativo mesmo quando o agente está em outro canal.
Conversas existentes ficam com o canal do agente.

Revision ID: 0008
Revises: 0007
Create Date: 2026-09-17 12:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = '0008'
down_revision: str | None = '0007'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column('conversa', sa.Column('canal', sa.String(length=20), nullable=True))
    op.execute("UPDATE conversa SET canal = agente.canal FROM agente WHERE conversa.agente_id = agente.id")
    op.alter_column('conversa', 'canal', nullable=False)


def downgrade() -> None:
    op.drop_column('conversa', 'canal')
