"""merge_heads

Revision ID: b8d7330c4ba7
Revises: 7ce5aa0ca14d, db16e45b373d
Create Date: 2026-02-04 05:32:26.617169

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import geoalchemy2  


# revision identifiers, used by Alembic.
revision: str = 'b8d7330c4ba7'
down_revision: Union[str, Sequence[str], None] = ('7ce5aa0ca14d', 'db16e45b373d')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
