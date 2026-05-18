"""update_ratings_based_on_result

Revision ID: 64156ddf76aa
Revises: e08051d3ab00
Create Date: 2026-05-18 07:08:30.536089

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '64156ddf76aa'
down_revision: Union[str, Sequence[str], None] = 'e08051d3ab00'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
   op.execute("""
        UPDATE rules 
        SET ratings = CASE 
            WHEN result = 'Best' THEN 10
            WHEN result = 'Good' THEN 8
            WHEN result = 'Ok' THEN 5
            WHEN result = 'Bad' THEN 3
            ELSE ratings
        END
        WHERE result IN ('Best', 'Good', 'Ok', 'Bad')
    """)


def downgrade():
   op.execute("""
        UPDATE rules
        SET ratings = 0
        WHERE result IN ('Best', 'Good', 'Ok', 'Bad')
    """)

