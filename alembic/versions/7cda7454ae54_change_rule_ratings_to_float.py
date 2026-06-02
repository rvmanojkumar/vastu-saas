"""change rule ratings to float

Revision ID: 7cda7454ae54
Revises: f30a4694b0c7
Create Date: 2026-05-29 10:06:02.999654

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7cda7454ae54'
down_revision: Union[str, Sequence[str], None] = 'f30a4694b0c7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
