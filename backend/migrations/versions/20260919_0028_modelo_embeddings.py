"""Fixa o modelo da base sem presumir a origem de vetores antigos."""
from alembic import op
import sqlalchemy as sa

revision = "0028"
down_revision = "0027"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("configuracao_embeddings",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=False),
        sa.Column("modelo", sa.String(100), nullable=False),
        sa.CheckConstraint("id = 1", name="linha_unica"),
    )


def downgrade():
    op.drop_table("configuracao_embeddings")
