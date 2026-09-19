"""Sentimento no turno e o aviso de que o agente é uma IA.

Aditiva. O aviso nasce desligado (escolha do operador): quem atende na União Europeia marca, e quem
atende só no Brasil decide. O sentimento fica vazio nos turnos que já existem.

Revision ID: 0024
Revises: 0023
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = '0024'
down_revision: str | None = '0023'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column('turno', sa.Column('sentimento', sa.String(length=10), server_default='', nullable=False))
    op.add_column('agente', sa.Column('avisa_que_e_ia', sa.Boolean(), server_default='false', nullable=False))
    op.add_column('agente', sa.Column('aviso_de_ia', sa.String(length=300), server_default='', nullable=False))
    op.add_column('conversa', sa.Column('avisou_ia_em', sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column('conversa', 'avisou_ia_em')
    op.drop_column('agente', 'aviso_de_ia')
    op.drop_column('agente', 'avisa_que_e_ia')
    op.drop_column('turno', 'sentimento')
