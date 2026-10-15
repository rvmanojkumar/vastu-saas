"""Create numerology_reports table and allow null task.project_id

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-08-05
"""
from alembic import op
import sqlalchemy as sa


revision = "b2c3d4e5f6a7"
down_revision = "a1b2c3d4e5f6"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "numerology_reports",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("task_id", sa.String(length=64), nullable=True),
        sa.Column("full_name", sa.String(length=255), nullable=False),
        sa.Column("date_of_birth", sa.Date(), nullable=False),
        sa.Column("gender", sa.String(length=1), nullable=False),
        sa.Column("mobile_number", sa.String(length=20), nullable=True),
        sa.Column("lang", sa.String(length=5), server_default="en"),
        sa.Column("moolank", sa.Integer(), nullable=True),
        sa.Column("bhagyank", sa.Integer(), nullable=True),
        sa.Column("first_name_number", sa.Integer(), nullable=True),
        sa.Column("last_name_number", sa.Integer(), nullable=True),
        sa.Column("full_name_number", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(length=30), server_default="pending"),
        sa.Column("result_path", sa.String(length=500), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("chart_json", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_numerology_reports_user_id", "numerology_reports", ["user_id"])
    op.create_index("ix_numerology_reports_task_id", "numerology_reports", ["task_id"])

    # Allow numerology tasks without a Vastu project
    try:
        op.alter_column(
            "tasks",
            "project_id",
            existing_type=sa.Integer(),
            nullable=True,
        )
    except Exception:
        # Some MySQL setups need batch mode; ignore if already nullable
        pass


def downgrade():
    op.drop_index("ix_numerology_reports_task_id", table_name="numerology_reports")
    op.drop_index("ix_numerology_reports_user_id", table_name="numerology_reports")
    op.drop_table("numerology_reports")
