"""funil de oportunidades: etapas, cartões e etiquetas

Kanban por empresa. As etapas são do operador e não fixas no código: quem atende várias empresas
tem um funil para cada uma. Tudo novo e aditivo; nenhuma tabela existente muda.

Revision ID: 0019
Revises: 0018
Create Date: 2026-09-18 22:30:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = '0019'
down_revision: str | None = '0018'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        'etapa_funil',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('cliente_id', sa.Uuid(), nullable=False),
        sa.Column('nome', sa.String(length=60), nullable=False),
        sa.Column('ordem', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('ganha', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('perdida', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('criado_em', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['cliente_id'], ['cliente.id'], name=op.f('fk_etapa_funil_cliente_id_cliente')),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_etapa_funil')),
        sa.UniqueConstraint('cliente_id', 'nome', name=op.f('uq_etapa_funil_cliente_id')),
    )
    op.create_index(op.f('ix_etapa_funil_cliente_id'), 'etapa_funil', ['cliente_id'])

    op.create_table(
        'etiqueta',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('cliente_id', sa.Uuid(), nullable=False),
        sa.Column('nome', sa.String(length=40), nullable=False),
        sa.Column('cor', sa.String(length=20), nullable=False, server_default='ciano'),
        sa.Column('criado_em', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['cliente_id'], ['cliente.id'], name=op.f('fk_etiqueta_cliente_id_cliente')),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_etiqueta')),
        sa.UniqueConstraint('cliente_id', 'nome', name=op.f('uq_etiqueta_cliente_id')),
    )
    op.create_index(op.f('ix_etiqueta_cliente_id'), 'etiqueta', ['cliente_id'])

    op.create_table(
        'oportunidade',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('cliente_id', sa.Uuid(), nullable=False),
        sa.Column('etapa_id', sa.Uuid(), nullable=False),
        sa.Column('contato_id', sa.Uuid(), nullable=True),
        sa.Column('titulo', sa.String(length=200), nullable=False),
        sa.Column('valor', sa.Numeric(precision=12, scale=2), nullable=False, server_default='0'),
        sa.Column('nota', sa.Text(), nullable=False, server_default=''),
        sa.Column('ordem', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('atualizado_em', sa.DateTime(timezone=True), nullable=False),
        sa.Column('criado_em', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['cliente_id'], ['cliente.id'], name=op.f('fk_oportunidade_cliente_id_cliente')),
        sa.ForeignKeyConstraint(['etapa_id'], ['etapa_funil.id'], name=op.f('fk_oportunidade_etapa_id_etapa_funil')),
        sa.ForeignKeyConstraint(['contato_id'], ['contato.id'], name=op.f('fk_oportunidade_contato_id_contato')),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_oportunidade')),
    )
    op.create_index(op.f('ix_oportunidade_cliente_id'), 'oportunidade', ['cliente_id'])
    op.create_index('ix_oportunidade_cliente_etapa', 'oportunidade', ['cliente_id', 'etapa_id'])

    op.create_table(
        'oportunidade_etiqueta',
        sa.Column('oportunidade_id', sa.Uuid(), nullable=False),
        sa.Column('etiqueta_id', sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(['oportunidade_id'], ['oportunidade.id'], ondelete='CASCADE', name=op.f('fk_oportunidade_etiqueta_oportunidade_id_oportunidade')),
        sa.ForeignKeyConstraint(['etiqueta_id'], ['etiqueta.id'], ondelete='CASCADE', name=op.f('fk_oportunidade_etiqueta_etiqueta_id_etiqueta')),
        sa.PrimaryKeyConstraint('oportunidade_id', 'etiqueta_id', name=op.f('pk_oportunidade_etiqueta')),
    )


def downgrade() -> None:
    op.drop_table('oportunidade_etiqueta')
    op.drop_index('ix_oportunidade_cliente_etapa', table_name='oportunidade')
    op.drop_index(op.f('ix_oportunidade_cliente_id'), table_name='oportunidade')
    op.drop_table('oportunidade')
    op.drop_index(op.f('ix_etiqueta_cliente_id'), table_name='etiqueta')
    op.drop_table('etiqueta')
    op.drop_index(op.f('ix_etapa_funil_cliente_id'), table_name='etapa_funil')
    op.drop_table('etapa_funil')
