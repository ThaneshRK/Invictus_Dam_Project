"""Merge multiple heads

Revision ID: 6301d84c1e9f
Revises: 2112455b1377, 308c63f87711
Create Date: 2026-09-19 09:06:45.486127

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import geoalchemy2


# revision identifiers, used by Alembic.
revision: str = '6301d84c1e9f'
down_revision: Union[str, None] = ('2112455b1377', '308c63f87711')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
