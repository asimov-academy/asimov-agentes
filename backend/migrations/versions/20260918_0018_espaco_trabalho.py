"""espaço de trabalho e perfil do operador

O painel não guardava nada sobre quem opera nem sobre a instalação: o menu dizia ASIMOV para todo
mundo e a tela de configurações só tinha o que vinha do `.env`. Tudo aditivo e com padrão vazio, e o
painel continua funcionando sem nada preenchido.

Revision ID: 0018
Revises: 0017
Create Date: 2026-09-18 21:40:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = '0018'
down_revision: str | None = '0017'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column('usuario_painel', sa.Column('nome', sa.String(length=120), nullable=False, server_default=''))
    op.add_column('usuario_painel', sa.Column('email', sa.String(length=200), nullable=False, server_default=''))
    op.create_table(
        'espaco_trabalho',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('unico', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('nome', sa.String(length=120), nullable=False, server_default=''),
        sa.Column('sigla', sa.String(length=2), nullable=False, server_default=''),
        sa.Column('negocio_nome', sa.String(length=200), nullable=False, server_default=''),
        sa.Column('negocio_documento', sa.String(length=40), nullable=False, server_default=''),
        sa.Column('negocio_email', sa.String(length=200), nullable=False, server_default=''),
        sa.Column('negocio_telefone', sa.String(length=40), nullable=False, server_default=''),
        sa.Column('negocio_site', sa.String(length=300), nullable=False, server_default=''),
        sa.Column('atualizado_em', sa.DateTime(timezone=True), nullable=False),
        sa.Column('criado_em', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_espaco_trabalho')),
        sa.UniqueConstraint('unico', name=op.f('uq_espaco_trabalho_unico')),
    )


def downgrade() -> None:
    op.drop_table('espaco_trabalho')
    op.drop_column('usuario_painel', 'email')
    op.drop_column('usuario_painel', 'nome')
