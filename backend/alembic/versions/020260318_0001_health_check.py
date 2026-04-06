"""Initial base schema - health check only

Revision ID: 001_base
Revises: 
Create Date: 2026-03-18
"""

from alembic import op
import sqlalchemy as sa

revision = "001_base"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "health_check",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("created_at", sa.String(length=64), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("health_check")
