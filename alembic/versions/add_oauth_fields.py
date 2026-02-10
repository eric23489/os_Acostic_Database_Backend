"""add oauth fields to user

Revision ID: add_oauth_fields
Revises: db16e45b373d
Create Date: 2026-02-06

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "add_oauth_fields"
down_revision: Union[str, Sequence[str], None] = "b8d7330c4ba7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add OAuth fields
    op.add_column(
        "user_info",
        sa.Column("oauth_provider", sa.String(50), nullable=True),
    )
    op.add_column(
        "user_info",
        sa.Column("oauth_sub", sa.String(255), nullable=True),
    )

    # Add password reset fields
    op.add_column(
        "user_info",
        sa.Column("reset_token", sa.String(255), nullable=True),
    )
    op.add_column(
        "user_info",
        sa.Column("reset_token_expires_at", sa.DateTime(timezone=True), nullable=True),
    )

    # Make password_hash nullable for OAuth-only users
    op.alter_column(
        "user_info",
        "password_hash",
        existing_type=sa.String(255),
        nullable=True,
    )

    # Create unique index for oauth_sub (active users only)
    op.create_index(
        "uq_oauth_sub_active",
        "user_info",
        ["oauth_provider", "oauth_sub"],
        unique=True,
        postgresql_where=sa.text("is_deleted = false"),
    )


def downgrade() -> None:
    # Drop the unique index
    op.drop_index(
        "uq_oauth_sub_active",
        table_name="user_info",
        postgresql_where=sa.text("is_deleted = false"),
    )

    # Make password_hash non-nullable again
    op.alter_column(
        "user_info",
        "password_hash",
        existing_type=sa.String(255),
        nullable=False,
    )

    # Drop password reset fields
    op.drop_column("user_info", "reset_token_expires_at")
    op.drop_column("user_info", "reset_token")

    # Drop OAuth fields
    op.drop_column("user_info", "oauth_sub")
    op.drop_column("user_info", "oauth_provider")
