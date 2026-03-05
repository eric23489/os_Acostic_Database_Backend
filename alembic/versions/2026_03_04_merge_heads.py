"""merge deploy_personnel branch into main

Revision ID: 2026_03_04_merge_heads
Revises: 8d117cb597a8, 2e5b54dbabd1
Create Date: 2026-03-04

"""

from typing import Sequence, Union

# revision identifiers, used by Alembic.
revision: str = "2026_03_04_merge_heads"
down_revision: Union[str, Sequence[str], None] = ("8d117cb597a8", "2e5b54dbabd1")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
