"""Foto e cor do agente.

O agente aparecia na lista como a inicial do nome numa caixa ciano, igual para todos. Agora ele tem
cara: a foto que o operador enviar, a que veio do WhatsApp quando o número parear, ou a inicial numa
das cores do painel.

`avatar` guarda o caminho do arquivo dentro do diretório de mídia, nunca o arquivo. `avatar_cor`
guarda o nome do token de cor, nunca o hexadecimal.

Revision ID: 0026
Revises: 0025
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = '0026'
down_revision: str | None = '0025'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column('agente', sa.Column('avatar', sa.String(length=300), server_default='', nullable=False))
    op.add_column('agente', sa.Column('avatar_cor', sa.String(length=20), server_default='', nullable=False))


def downgrade() -> None:
    op.drop_column('agente', 'avatar_cor')
    op.drop_column('agente', 'avatar')
