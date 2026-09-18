"""arquivo de mídia sai do disco em 24 horas

O texto lido do arquivo fica; o arquivo em si não é lido por ninguém depois da leitura.

Revision ID: 0011
Revises: 0010
Create Date: 2026-09-18 00:30:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = '0011'
down_revision: str | None = '0010'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column('midia', sa.Column('arquivo_apagado_em', sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column('midia', 'arquivo_apagado_em')
