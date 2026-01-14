from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session
from geoalchemy2.elements import WKTElement

from app.models.deployment import DeploymentInfo
from app.schemas.deployment import DeploymentCreate, DeploymentUpdate


class DeploymentService:
    def __init__(self, db: Session):
        self.db = db

    def get_deployment(self, deployment_id: int) -> DeploymentInfo:
        deployment = (
            self.db.query(DeploymentInfo)
            .filter(DeploymentInfo.id == deployment_id)
            .first()
        )
        if not deployment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Deployment not found",
            )
        return deployment

    def get_deployments(
        self, point_id: int, skip: int = 0, limit: int = 100
    ) -> list[DeploymentInfo]:
        return (
            self.db.query(DeploymentInfo)
            .filter(DeploymentInfo.point_id == point_id)
            .offset(skip)
            .limit(limit)
            .all()
        )

    def create_deployment(self, deployment_in: DeploymentCreate) -> DeploymentInfo:
        # Auto-calculate Phase: Max phase for this point + 1
        max_phase = (
            self.db.query(func.max(DeploymentInfo.phase))
            .filter(DeploymentInfo.point_id == deployment_in.point_id)
            .scalar()
        )
        new_phase = (max_phase or 0) + 1

        deployment_data = deployment_in.model_dump()
        deployment_data["phase"] = new_phase

        # 自動將經緯度轉換為 PostGIS Geometry
        if (
            deployment_in.gps_lat_exe is not None
            and deployment_in.gps_lon_exe is not None
        ):
            deployment_data["geom_exe"] = WKTElement(
                f"POINT({deployment_in.gps_lon_exe} {deployment_in.gps_lat_exe})",
                srid=4326,
            )

        db_obj = DeploymentInfo(**deployment_data)
        self.db.add(db_obj)
        self.db.commit()
        self.db.refresh(db_obj)
        return db_obj

    def update_deployment(
        self, deployment_id: int, deployment_in: DeploymentUpdate
    ) -> DeploymentInfo:
        deployment = self.get_deployment(deployment_id)
        update_data = deployment_in.model_dump(exclude_unset=True)

        # 若更新了經緯度，同步更新 Geometry
        if "gps_lat_exe" in update_data or "gps_lon_exe" in update_data:
            lat = update_data.get("gps_lat_exe", deployment.gps_lat_exe)
            lon = update_data.get("gps_lon_exe", deployment.gps_lon_exe)
            if lat is not None and lon is not None:
                update_data["geom_exe"] = WKTElement(f"POINT({lon} {lat})", srid=4326)

        for field, value in update_data.items():
            setattr(deployment, field, value)

        self.db.add(deployment)
        self.db.commit()
        self.db.refresh(deployment)
        return deployment
