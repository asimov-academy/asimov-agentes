"""Três situações do agente no lugar do ligado/desligado.

O `ativo` respondia a uma pergunta só: ele fala ou não fala. Faltava o meio, que é onde o agente
passa a maior parte da vida útil: existe, conversa no painel, mas ainda não atende cliente nenhum.
Agora são `ativo`, `treinamento` e `inativo`, num campo só: dois campos booleanos deixariam
"desligado e em treinamento" possível, e isso não quer dizer nada.

Quem estava ativo continua ativo, quem estava desligado vira inativo. Ninguém nasce em treinamento
por migração: o operador é quem escolhe.

Revision ID: 0025
Revises: 0024
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = '0025'
down_revision: str | None = '0024'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        'agente', sa.Column('situacao', sa.String(length=20), server_default='ativo', nullable=False)
    )
    op.execute("UPDATE agente SET situacao = CASE WHEN ativo THEN 'ativo' ELSE 'inativo' END")
    op.drop_column('agente', 'ativo')


def downgrade() -> None:
    op.add_column('agente', sa.Column('ativo', sa.Boolean(), server_default='true', nullable=False))
    # Em treinamento ele não atende canal, e é isso que o booleano sabia dizer.
    op.execute("UPDATE agente SET ativo = (situacao = 'ativo')")
    op.drop_column('agente', 'situacao')
