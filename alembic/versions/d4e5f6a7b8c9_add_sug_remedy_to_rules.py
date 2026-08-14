"""Add sug_remedy_en/hi/mr columns to rules.

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-08-14
"""
from alembic import op
import sqlalchemy as sa


revision = "d4e5f6a7b8c9"
down_revision = "c3d4e5f6a7b8"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("rules", sa.Column("sug_remedy_en", sa.Text(), nullable=True))
    op.add_column("rules", sa.Column("sug_remedy_hi", sa.Text(), nullable=True))
    op.add_column("rules", sa.Column("sug_remedy_mr", sa.Text(), nullable=True))


def downgrade():
    op.drop_column("rules", "sug_remedy_mr")
    op.drop_column("rules", "sug_remedy_hi")
    op.drop_column("rules", "sug_remedy_en")
