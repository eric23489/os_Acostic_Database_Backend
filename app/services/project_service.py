import logging

from fastapi import HTTPException, status
from sqlalchemy.orm import Session, selectinload

from app.core.minio import get_s3_client
from app.models.point import PointInfo
from app.models.project import ProjectInfo
from app.schemas.project import ProjectCreate, ProjectUpdate
from app.utils.naming import generate_slug_from_zh

logger = logging.getLogger(__name__)


class ProjectService:
    def __init__(self, db: Session):
        self.db = db

    def get_project(self, project_id: int) -> ProjectInfo:
        project = (
            self.db.query(ProjectInfo).filter(ProjectInfo.id == project_id).first()
        )
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found",
            )
        return project

    def get_projects(self, skip: int = 0, limit: int = 100) -> list[ProjectInfo]:
        return self.db.query(ProjectInfo).offset(skip).limit(limit).all()

    def get_projects_hierarchy(self) -> list[ProjectInfo]:
        return (
            self.db.query(ProjectInfo)
            .options(
                selectinload(ProjectInfo.points).selectinload(PointInfo.deployments)
            )
            .all()
        )

    def create_project(self, project_in: ProjectCreate) -> ProjectInfo:
        # Auto-generate name from name_zh if name is not provided
        if not project_in.name:
            if not project_in.name_zh:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Either 'name' or 'name_zh' must be provided.",
                )

            base_slug = generate_slug_from_zh(project_in.name_zh)
            candidate_name = base_slug

            # Update the input model
            project_in.name = candidate_name

        # Check if project name exists
        if (
            self.db.query(ProjectInfo)
            .filter(ProjectInfo.name == project_in.name)
            .first()
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Project with this name already exists",
            )

        # Check if Chinese name (name_zh) exists, if provided
        if project_in.name_zh and (
            self.db.query(ProjectInfo)
            .filter(ProjectInfo.name_zh == project_in.name_zh)
            .first()
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Project with this Chinese name (name_zh) already exists",
            )

        db_obj = ProjectInfo(**project_in.model_dump())
        self.db.add(db_obj)
        self.db.commit()
        self.db.refresh(db_obj)

        # Create MinIO bucket
        try:
            s3_client = get_s3_client()
            s3_client.create_bucket(Bucket=db_obj.name)
        except Exception as e:
            # Log error or handle it. For now, we might not want to fail the whole request
            # if bucket creation fails, but it's good practice to ensure consistency.
            logger.error(f"Failed to create MinIO bucket '{db_obj.name}': {e}")

        return db_obj

    def update_project(self, project_id: int, project_in: ProjectUpdate) -> ProjectInfo:
        project = self.get_project(project_id)
        update_data = project_in.model_dump(exclude_unset=True)

        # Check for name_zh uniqueness if it's being updated
        if "name_zh" in update_data and update_data["name_zh"]:
            if (
                self.db.query(ProjectInfo)
                .filter(
                    ProjectInfo.name_zh == update_data["name_zh"],
                    ProjectInfo.id != project_id,
                )
                .first()
            ):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Project with this Chinese name (name_zh) already exists",
                )

        for field, value in update_data.items():
            setattr(project, field, value)

        self.db.add(project)
        self.db.commit()
        self.db.refresh(project)
        return project
