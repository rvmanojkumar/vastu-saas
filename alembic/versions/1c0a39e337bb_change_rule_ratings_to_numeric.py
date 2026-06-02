"""change rule ratings to numeric

Revision ID: 1c0a39e337bb
Revises: 8688ebabe18b
Create Date: 2026-05-29 14:24:01.168076

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '1c0a39e337bb'
down_revision: Union[str, Sequence[str], None] = '8688ebabe18b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
