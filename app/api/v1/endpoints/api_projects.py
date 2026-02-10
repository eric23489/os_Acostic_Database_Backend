from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException, status
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.db.session import get_db, SessionLocal
from app.models.project import ProjectInfo
from app.models.user import UserRole
from app.schemas.project import ProjectCreate, ProjectResponse, ProjectUpdate
from app.services.project_service import ProjectService

router = APIRouter(prefix="/projects", tags=["projects"])


@router.get("/", response_model=List[ProjectResponse])
def get_projects(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return ProjectService(db).get_projects(skip=skip, limit=limit)


@router.get("/{project_id}", response_model=ProjectResponse)
def get_project(
    project_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return ProjectService(db).get_project(project_id)


@router.post("/", response_model=ProjectResponse)
def create_project(
    project: ProjectCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return ProjectService(db).create_project(project)


@router.put("/{project_id}", response_model=ProjectResponse)
def update_project(
    project_id: int,
    project: ProjectUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return ProjectService(db).update_project(project_id, project)


def background_delete_project_audios(
    project_id: int, user_id: int, deleted_at: datetime
):
    db = SessionLocal()
    try:
        ProjectService(db).delete_project_audios(project_id, user_id, deleted_at)
    finally:
        db.close()


@router.delete("/{project_id}", response_model=ProjectResponse)
def delete_project(
    project_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    project = ProjectService(db).delete_project(project_id, current_user.id)
    background_tasks.add_task(
        background_delete_project_audios,
        project_id,
        current_user.id,
        project.deleted_at,
    )
    return project


@router.post("/{project_id}/restore", response_model=ProjectResponse)
def restore_project(
    project_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    project = db.query(ProjectInfo).filter(ProjectInfo.id == project_id).first()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )
    if (
        current_user.role != UserRole.ADMIN.value
        and current_user.id != project.deleted_by
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the deleter or admin can restore this resource",
        )
    return ProjectService(db).restore_project(project_id)


@router.delete("/{project_id}/permanent", response_model=dict)
def hard_delete_project(
    project_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    永久刪除 Project 及所有相關資料。

    - 刪除 MinIO Bucket 和所有物件
    - 刪除資料庫中的所有相關記錄
    - 釋放名稱，可重新使用

    需要 Admin 權限。
    """
    if current_user.role != UserRole.ADMIN.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin permission required for permanent deletion",
        )
    return ProjectService(db).hard_delete_project(project_id)
