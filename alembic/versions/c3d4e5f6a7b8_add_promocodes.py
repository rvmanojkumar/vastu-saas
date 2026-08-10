"""Add promocodes table and payment promo columns.

Revision ID: c3d4e5f6a7b8
Revises: fc18611cee5a
Create Date: 2026-08-10
"""
from alembic import op
import sqlalchemy as sa


revision = "c3d4e5f6a7b8"
down_revision = "fc18611cee5a"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "promocodes",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("code", sa.String(length=50), nullable=False),
        sa.Column("plan_id", sa.Integer(), sa.ForeignKey("plans.id"), nullable=False),
        sa.Column("discount_type", sa.String(length=20), nullable=False),
        sa.Column("discount_value", sa.Numeric(10, 2), nullable=False),
        sa.Column("max_usage", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("used_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("ends_on", sa.Date(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="active"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"),
        ),
        sa.UniqueConstraint("code", name="uq_promocodes_code"),
    )
    op.create_index("ix_promocodes_code", "promocodes", ["code"])
    op.create_index("ix_promocodes_plan_id", "promocodes", ["plan_id"])

    op.add_column("payments", sa.Column("promocode_id", sa.Integer(), nullable=True))
    op.add_column(
        "payments", sa.Column("discount_applied", sa.Numeric(10, 2), nullable=True)
    )
    op.create_foreign_key(
        "fk_payments_promocode_id",
        "payments",
        "promocodes",
        ["promocode_id"],
        ["id"],
    )


def downgrade():
    op.drop_constraint("fk_payments_promocode_id", "payments", type_="foreignkey")
    op.drop_column("payments", "discount_applied")
    op.drop_column("payments", "promocode_id")
    op.drop_index("ix_promocodes_plan_id", table_name="promocodes")
    op.drop_index("ix_promocodes_code", table_name="promocodes")
    op.drop_table("promocodes")
