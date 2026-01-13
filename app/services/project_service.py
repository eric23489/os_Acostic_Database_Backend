from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.project import ProjectInfo
from app.schemas.project import ProjectCreate, ProjectUpdate


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

    def create_project(self, project_in: ProjectCreate) -> ProjectInfo:
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

        db_obj = ProjectInfo(**project_in.model_dump())
        self.db.add(db_obj)
        self.db.commit()
        self.db.refresh(db_obj)
        return db_obj

    def update_project(self, project_id: int, project_in: ProjectUpdate) -> ProjectInfo:
        project = self.get_project(project_id)
        update_data = project_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(project, field, value)

        self.db.add(project)
        self.db.commit()
        self.db.refresh(project)
        return project
