"""Tom de voz, handoff opcional e restrição de temas no agente.

Aditiva: todo agente que já existe continua como estava, com tom normal, transferindo para humano
e falando de qualquer assunto, que é o comportamento de antes desta migração.

Revision ID: 0020
Revises: 0019
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = '0020'
down_revision: str | None = '0019'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column('agente', sa.Column('tom', sa.String(length=20), server_default='normal', nullable=False))
    op.add_column('agente', sa.Column('transfere_para_humano', sa.Boolean(), server_default='true', nullable=False))
    op.add_column('agente', sa.Column('restringe_temas', sa.Boolean(), server_default='false', nullable=False))


def downgrade() -> None:
    op.drop_column('agente', 'restringe_temas')
    op.drop_column('agente', 'transfere_para_humano')
    op.drop_column('agente', 'tom')
