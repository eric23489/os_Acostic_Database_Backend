from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from geoalchemy2.elements import WKTElement

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
                status_code=400, detail="Point name already exists in this project"
            )

        point_data = point_in.model_dump()
        # 自動將經緯度轉換為 PostGIS Geometry
        if point_in.gps_lat_plan is not None and point_in.gps_lon_plan is not None:
            point_data["geom_plan"] = WKTElement(
                f"POINT({point_in.gps_lon_plan} {point_in.gps_lat_plan})", srid=4326
            )

        db_obj = PointInfo(**point_data)
        self.db.add(db_obj)
        self.db.commit()
        self.db.refresh(db_obj)
        return db_obj

    def update_point(self, point_id: int, point_in: PointUpdate) -> PointInfo:
        point = self.get_point(point_id)
        update_data = point_in.model_dump(exclude_unset=True)

        # 若更新了經緯度，同步更新 Geometry
        if "gps_lat_plan" in update_data or "gps_lon_plan" in update_data:
            lat = update_data.get("gps_lat_plan", point.gps_lat_plan)
            lon = update_data.get("gps_lon_plan", point.gps_lon_plan)
            if lat is not None and lon is not None:
                update_data["geom_plan"] = WKTElement(f"POINT({lon} {lat})", srid=4326)

        for field, value in update_data.items():
            setattr(point, field, value)

        self.db.add(point)
        self.db.commit()
        self.db.refresh(point)
        return point
