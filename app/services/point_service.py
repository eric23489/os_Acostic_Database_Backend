from fastapi import HTTPException, status
from sqlalchemy.orm import Session, joinedload

from app.models.point import PointInfo
from app.schemas.point import PointCreate, PointUpdate


class PointService:
    def __init__(self, db: Session):
        self.db = db

    def get_point(self, point_id: int) -> PointInfo:
        point = self.db.query(PointInfo).filter(PointInfo.id == point_id).first()
        if not point:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Point not found",
            )
        return point

    def get_point_details(self, point_id: int) -> PointInfo:
        """
        Get a single point with its associated project details.
        Uses joinedload to prevent N+1 query problem.
        """
        point = (
            self.db.query(PointInfo)
            .options(joinedload(PointInfo.project))
            .filter(PointInfo.id == point_id)
            .first()
        )
        if not point:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Point not found"
            )
        return point

    def get_points(
        self, project_id: int, skip: int = 0, limit: int = 100
    ) -> list[PointInfo]:
        return (
            self.db.query(PointInfo)
            .filter(PointInfo.project_id == project_id)
            .offset(skip)
            .limit(limit)
            .all()
        )

    def create_point(self, point_in: PointCreate) -> PointInfo:
        # Check unique constraint (project_id, name)
        if (
            self.db.query(PointInfo)
            .filter(
                PointInfo.project_id == point_in.project_id,
                PointInfo.name == point_in.name,
            )
            .first()
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Point name already exists in this project",
            )

        point_data = point_in.model_dump()

        db_obj = PointInfo(**point_data)
        self.db.add(db_obj)
        self.db.commit()
        self.db.refresh(db_obj)
        return db_obj

    def update_point(self, point_id: int, point_in: PointUpdate) -> PointInfo:
        point = self.get_point(point_id)
        update_data = point_in.model_dump(exclude_unset=True)

        # Check for duplicates if name or project_id is updated
        if "name" in update_data or "project_id" in update_data:
            new_name = update_data.get("name", point.name)
            new_project_id = update_data.get("project_id", point.project_id)

            if (
                self.db.query(PointInfo)
                .filter(
                    PointInfo.project_id == new_project_id,
                    PointInfo.name == new_name,
                    PointInfo.id != point_id,
                )
                .first()
            ):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Point name already exists in this project",
                )

        for field, value in update_data.items():
            setattr(point, field, value)

        self.db.add(point)
        self.db.commit()
        self.db.refresh(point)
        return point
