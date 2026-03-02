"""add deploy_personnel and retrieve_personnel to deployment

Revision ID: 2e5b54dbabd1
Revises: fix_deployment_idx
Create Date: 2026-03-02

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "2e5b54dbabd1"
down_revision: Union[str, Sequence[str], None] = "fix_deployment_idx"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "deployment_info", sa.Column("deploy_personnel", sa.String(), nullable=True)
    )
    op.add_column(
        "deployment_info", sa.Column("retrieve_personnel", sa.String(), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("deployment_info", "retrieve_personnel")
    op.drop_column("deployment_info", "deploy_personnel")
