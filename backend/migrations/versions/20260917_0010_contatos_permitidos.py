"""agente pode atender só os números listados

Lista vazia (o normal) atende qualquer pessoa. Serve para testar um número novo.

Revision ID: 0010
Revises: 0009
Create Date: 2026-09-17 21:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = '0010'
down_revision: str | None = '0009'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        'agente',
        sa.Column(
            'contatos_permitidos',
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
    )


def downgrade() -> None:
    op.drop_column('agente', 'contatos_permitidos')
