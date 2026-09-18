"""o perfil que escreve o prompt, e a assinatura do nome

O formulário de Trabalho do painel guarda aqui o que ele perguntou (função, público, site e o texto
sobre a empresa) e é daqui que sai o `persona.md` gerado. Fica no agente, não na empresa: é o que
impede um prompt de atravessar de uma empresa para outra, que é o achado A05 da auditoria.

Agente criado antes fica com `perfil` vazio, e o painel mostra o prompt à mão em vez de inventar
campo que ninguém preencheu.

Revision ID: 0016
Revises: 0015
Create Date: 2026-09-18 22:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = '0016'
down_revision: str | None = '0015'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        'agente',
        sa.Column(
            'perfil',
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default='{}',
        ),
    )
    op.add_column(
        'agente',
        sa.Column('assina_nome', sa.Boolean(), nullable=False, server_default=sa.text('false')),
    )


def downgrade() -> None:
    op.drop_column('agente', 'assina_nome')
    op.drop_column('agente', 'perfil')
