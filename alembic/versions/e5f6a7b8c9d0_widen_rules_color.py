"""Widen rules.color so comma-separated color lists can be saved.

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-08-19
"""
from alembic import op
import sqlalchemy as sa


revision = "e5f6a7b8c9d0"
down_revision = "d4e5f6a7b8c9"
branch_labels = None
depends_on = None


def upgrade():
    op.alter_column(
        "rules",
        "color",
        existing_type=sa.String(length=50),
        type_=sa.Text(),
        existing_nullable=True,
    )


def downgrade():
    op.alter_column(
        "rules",
        "color",
        existing_type=sa.Text(),
        type_=sa.String(length=50),
        existing_nullable=True,
    )
