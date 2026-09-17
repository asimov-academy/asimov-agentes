"""agente novo nasce sem ferramentas

O operador marca as ferramentas na criação; agentes existentes mantêm as que têm.

Revision ID: 0009
Revises: 0008
Create Date: 2026-09-17 18:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = '0009'
down_revision: str | None = '0008'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column('agente', 'ferramentas', server_default=sa.text("'[]'::jsonb"))


def downgrade() -> None:
    op.alter_column('agente', 'ferramentas', server_default=sa.text("'[\"calculadora\", \"busca_web\"]'::jsonb"))
