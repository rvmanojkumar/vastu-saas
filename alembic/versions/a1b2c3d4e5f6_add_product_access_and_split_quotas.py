"""Add product_access and separate Vastu/Numerology report quotas.

Revision ID: a1b2c3d4e5f6
Revises: fc18611cee5a
Create Date: 2026-08-05
"""
from alembic import op
import sqlalchemy as sa


revision = "a1b2c3d4e5f6"
down_revision = "fc18611cee5a"
branch_labels = None
depends_on = None


def upgrade():
    # ---- plans ----
    op.add_column(
        "plans",
        sa.Column("product_access", sa.String(length=20), nullable=False, server_default="both"),
    )
    op.add_column("plans", sa.Column("vastu_report_limit", sa.Integer(), nullable=True))
    op.add_column("plans", sa.Column("numerology_report_limit", sa.Integer(), nullable=True))

    # Split existing plan.report_limit into separate quotas
    # Odd totals favour Vastu: e.g. 10 -> 5/5, 11 -> 6/5
    op.execute(
        """
        UPDATE plans
        SET
          vastu_report_limit = CASE
            WHEN report_limit IS NULL THEN 0
            ELSE (report_limit + 1) DIV 2
          END,
          numerology_report_limit = CASE
            WHEN report_limit IS NULL THEN 0
            ELSE report_limit DIV 2
          END,
          product_access = 'both'
        """
    )

    # ---- subscriptions ----
    op.add_column("subscriptions", sa.Column("vastu_reports_limit", sa.Integer(), nullable=True))
    op.add_column("subscriptions", sa.Column("vastu_reports_used", sa.Integer(), nullable=True))
    op.add_column("subscriptions", sa.Column("numerology_reports_limit", sa.Integer(), nullable=True))
    op.add_column("subscriptions", sa.Column("numerology_reports_used", sa.Integer(), nullable=True))
    op.add_column(
        "subscriptions",
        sa.Column("product_access", sa.String(length=20), nullable=True, server_default="both"),
    )

    # Split existing subscription limits; keep historical usage on Vastu
    op.execute(
        """
        UPDATE subscriptions
        SET
          vastu_reports_limit = CASE
            WHEN reports_limit IS NULL THEN 0
            ELSE (reports_limit + 1) DIV 2
          END,
          numerology_reports_limit = CASE
            WHEN reports_limit IS NULL THEN 0
            ELSE reports_limit DIV 2
          END,
          vastu_reports_used = LEAST(
            COALESCE(reports_used, 0),
            CASE
              WHEN reports_limit IS NULL THEN 0
              ELSE (reports_limit + 1) DIV 2
            END
          ),
          numerology_reports_used = 0,
          product_access = 'both'
        """
    )

    # Normalize nulls to 0
    op.execute("UPDATE subscriptions SET vastu_reports_limit = 0 WHERE vastu_reports_limit IS NULL")
    op.execute("UPDATE subscriptions SET vastu_reports_used = 0 WHERE vastu_reports_used IS NULL")
    op.execute(
        "UPDATE subscriptions SET numerology_reports_limit = 0 WHERE numerology_reports_limit IS NULL"
    )
    op.execute(
        "UPDATE subscriptions SET numerology_reports_used = 0 WHERE numerology_reports_used IS NULL"
    )


def downgrade():
    op.drop_column("subscriptions", "product_access")
    op.drop_column("subscriptions", "numerology_reports_used")
    op.drop_column("subscriptions", "numerology_reports_limit")
    op.drop_column("subscriptions", "vastu_reports_used")
    op.drop_column("subscriptions", "vastu_reports_limit")
    op.drop_column("plans", "numerology_report_limit")
    op.drop_column("plans", "vastu_report_limit")
    op.drop_column("plans", "product_access")
