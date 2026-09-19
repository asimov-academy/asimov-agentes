"""Memória do contato: resumo da conversa, ficha do contato e o liga e desliga no agente.

Aditiva. `memoria_ativa` tem `server_default` falso de propósito: agente que já existe não começa a
guardar o que o contato disse sem alguém pedir. Agente novo nasce com ela ligada, pelo padrão do
modelo em Python.

Revision ID: 0023
Revises: 0022
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = '0023'
down_revision: str | None = '0022'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column('contato', sa.Column('memoria', sa.Text(), server_default='', nullable=False))
    op.add_column('conversa', sa.Column('resumo', sa.Text(), server_default='', nullable=False))
    op.add_column('conversa', sa.Column('resumido_ate', sa.DateTime(timezone=True), nullable=True))
    op.add_column('agente', sa.Column('memoria_ativa', sa.Boolean(), server_default='false', nullable=False))


def downgrade() -> None:
    op.drop_column('agente', 'memoria_ativa')
    op.drop_column('conversa', 'resumido_ate')
    op.drop_column('conversa', 'resumo')
    op.drop_column('contato', 'memoria')
