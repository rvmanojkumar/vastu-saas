"""Add phone_verified flag on users.

Revision ID: c7d8e9f0a1b2
Revises: f6a7b8c9d0e1
Create Date: 2026-08-25
"""
from alembic import op
import sqlalchemy as sa


revision = "c7d8e9f0a1b2"
down_revision = "f6a7b8c9d0e1"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "users",
        sa.Column(
            "phone_verified",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )


def downgrade():
    op.drop_column("users", "phone_verified")
