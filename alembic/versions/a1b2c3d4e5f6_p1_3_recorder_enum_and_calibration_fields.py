"""p1_3 recorder enum and calibration fields

Revision ID: a1b2c3d4e5f6
Revises: fix_deployment_idx
Create Date: 2026-03-10 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: str | None = "fix_deployment_idx"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. 新增校正欄位
    op.add_column(
        "recorder_info", sa.Column("measured_sensitivity", sa.Float(), nullable=True)
    )
    op.add_column(
        "recorder_info", sa.Column("standard_sensitivity", sa.Float(), nullable=True)
    )
    op.add_column(
        "recorder_info", sa.Column("calibration_date", sa.Date(), nullable=True)
    )

    # 2. 更新現有 DB 資料的 enum 值
    op.execute(
        "UPDATE recorder_info SET status = 'available' WHERE status = 'in-service'"
    )
    op.execute(
        "UPDATE deployment_info SET status = 'deploying' WHERE status = 'under-monitoring'"
    )


def downgrade() -> None:
    op.execute(
        "UPDATE deployment_info SET status = 'under-monitoring' WHERE status = 'deploying'"
    )
    op.execute(
        "UPDATE recorder_info SET status = 'in-service' WHERE status = 'available'"
    )
    op.drop_column("recorder_info", "calibration_date")
    op.drop_column("recorder_info", "standard_sensitivity")
    op.drop_column("recorder_info", "measured_sensitivity")
