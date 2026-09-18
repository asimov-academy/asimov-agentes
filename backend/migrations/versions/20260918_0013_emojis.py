"""quanto o agente usa emoji

Agente criado antes desta escolha fica em `livre`: a plataforma não diz nada sobre emoji para ele,
como sempre fez. Mudar o padrão deles para `nenhum` mudaria o jeito de responder sem ninguém pedir.

Revision ID: 0013
Revises: 0012
Create Date: 2026-09-18 20:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = '0013'
down_revision: str | None = '0012'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        'agente',
        sa.Column('emojis', sa.String(length=10), nullable=False, server_default='livre'),
    )


def downgrade() -> None:
    op.drop_column('agente', 'emojis')
