"""rename deployment time columns and fix index

Revision ID: fix_deployment_idx
Revises: add_oauth_fields
Create Date: 2026-02-10

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "fix_deployment_idx"
down_revision: Union[str, Sequence[str], None] = "add_oauth_fields"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Step 1: Drop the incorrect index (if it exists)
    op.execute("DROP INDEX IF EXISTS uq_deployment_point_start_time_active")

    # Step 2: Rename columns to match the model
    op.alter_column(
        "deployment_info",
        "start_time",
        new_column_name="report_start_time",
    )
    op.alter_column(
        "deployment_info",
        "end_time",
        new_column_name="report_end_time",
    )

    # Step 3: Create the correct index with report_start_time
    op.create_index(
        "uq_deployment_point_start_time_active",
        "deployment_info",
        ["point_id", "report_start_time"],
        unique=True,
        postgresql_where=sa.text("is_deleted = false"),
    )


def downgrade() -> None:
    # Step 1: Drop the index
    op.execute("DROP INDEX IF EXISTS uq_deployment_point_start_time_active")

    # Step 2: Rename columns back
    op.alter_column(
        "deployment_info",
        "report_start_time",
        new_column_name="start_time",
    )
    op.alter_column(
        "deployment_info",
        "report_end_time",
        new_column_name="end_time",
    )

    # Step 3: Recreate index with original column name
    op.create_index(
        "uq_deployment_point_start_time_active",
        "deployment_info",
        ["point_id", "start_time"],
        unique=True,
        postgresql_where=sa.text("is_deleted = false"),
    )
