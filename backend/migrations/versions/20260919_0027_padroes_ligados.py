"""Falar só de assuntos da empresa e lembrar do contato passam a nascer ligados.

Os dois entraram com `server_default` falso para agente que já existia não mudar de comportamento
sozinho, e o padrão de verdade vivia só no schema da API. Agora o banco diz a mesma coisa que ela:
agente novo nasce com os dois ligados.

Não mexe em quem já existe: quem desligou de propósito continua desligado.

Revision ID: 0027
Revises: 0026
"""

from collections.abc import Sequence

from alembic import op


revision: str = '0027'
down_revision: str | None = '0026'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column('agente', 'restringe_temas', server_default='true')
    op.alter_column('agente', 'memoria_ativa', server_default='true')


def downgrade() -> None:
    op.alter_column('agente', 'memoria_ativa', server_default='false')
    op.alter_column('agente', 'restringe_temas', server_default='false')
