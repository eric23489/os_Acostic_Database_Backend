"""Add upload jobs tables and audio upload status

Revision ID: add_upload_jobs
Revises: a6437fee202d
Create Date: 2026-02-12

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "add_upload_jobs"
down_revision: str | Sequence[str] | None = "a6437fee202d"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add upload status columns to audio_info
    op.add_column(
        "audio_info",
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.add_column(
        "audio_info",
        sa.Column(
            "upload_status", sa.String(20), server_default=sa.text("'completed'"), nullable=True
        ),
    )
    op.add_column(
        "audio_info", sa.Column("upload_id", sa.String(100), nullable=True)
    )
    op.add_column(
        "audio_info", sa.Column("upload_progress", sa.Integer(), default=0, nullable=True)
    )
    op.add_column(
        "audio_info", sa.Column("upload_total_parts", sa.Integer(), nullable=True)
    )

    # Create upload_jobs table
    op.create_table(
        "upload_jobs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "deployment_id", sa.Integer(), sa.ForeignKey("deployment_info.id"), nullable=False
        ),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("user_info.id"), nullable=False),
        sa.Column("status", sa.String(20), default="pending"),
        sa.Column("priority", sa.Integer(), default=5),
        sa.Column("total_files", sa.Integer(), default=0),
        sa.Column("uploaded_count", sa.Integer(), default=0),
        sa.Column("completed_count", sa.Integer(), default=0),
        sa.Column("failed_count", sa.Integer(), default=0),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now()
        ),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_upload_jobs_deployment_id", "upload_jobs", ["deployment_id"])
    op.create_index("ix_upload_jobs_user_id", "upload_jobs", ["user_id"])
    op.create_index("ix_upload_jobs_status", "upload_jobs", ["status"])

    # Create upload_tasks table
    op.create_table(
        "upload_tasks",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "job_id", sa.String(36), sa.ForeignKey("upload_jobs.id"), nullable=False
        ),
        sa.Column("file_name", sa.String(255), nullable=False),
        sa.Column("object_key", sa.String(1024), nullable=False),
        sa.Column("file_size", sa.Integer(), nullable=True),
        sa.Column("checksum", sa.String(64), nullable=True),
        sa.Column("status", sa.String(20), default="pending"),
        sa.Column("presigned_url", sa.Text(), nullable=True),
        sa.Column("url_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "audio_id", sa.Integer(), sa.ForeignKey("audio_info.id"), nullable=False
        ),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("retry_count", sa.Integer(), default=0),
        sa.Column("upload_id", sa.String(100), nullable=True),
        sa.Column("total_parts", sa.Integer(), nullable=True),
        sa.Column("completed_parts", sa.Integer(), default=0),
        sa.Column("part_size", sa.Integer(), default=104857600),
        sa.Column("part_etags", sa.JSON(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now()
        ),
        sa.Column("uploaded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_upload_tasks_job_id", "upload_tasks", ["job_id"])
    op.create_index("ix_upload_tasks_audio_id", "upload_tasks", ["audio_id"])
    op.create_index("ix_upload_tasks_status", "upload_tasks", ["status"])


def downgrade() -> None:
    """Downgrade schema."""
    # Drop upload_tasks table
    op.drop_index("ix_upload_tasks_status", "upload_tasks")
    op.drop_index("ix_upload_tasks_audio_id", "upload_tasks")
    op.drop_index("ix_upload_tasks_job_id", "upload_tasks")
    op.drop_table("upload_tasks")

    # Drop upload_jobs table
    op.drop_index("ix_upload_jobs_status", "upload_jobs")
    op.drop_index("ix_upload_jobs_user_id", "upload_jobs")
    op.drop_index("ix_upload_jobs_deployment_id", "upload_jobs")
    op.drop_table("upload_jobs")

    # Remove upload status columns from audio_info
    op.drop_column("audio_info", "upload_total_parts")
    op.drop_column("audio_info", "upload_progress")
    op.drop_column("audio_info", "upload_id")
    op.drop_column("audio_info", "upload_status")
    op.drop_column("audio_info", "created_at")
