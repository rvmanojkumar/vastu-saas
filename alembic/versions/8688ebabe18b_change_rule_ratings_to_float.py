"""change rule ratings to float

Revision ID: 8688ebabe18b
Revises: 7cda7454ae54
Create Date: 2026-05-29 10:07:35.881985

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8688ebabe18b'
down_revision: Union[str, Sequence[str], None] = '7cda7454ae54'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
