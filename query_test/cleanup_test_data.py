import sys
import os

# Add project root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.session import SessionLocal
from app.models.project import ProjectInfo
from app.models.point import PointInfo
from app.models.recorder import RecorderInfo
from app.models.deployment import DeploymentInfo
from app.models.audio import AudioInfo


def cleanup_data():
    db = SessionLocal()
    try:
        print("--- Cleaning up Test Data ---")

        # Find the benchmark project
        project = (
            db.query(ProjectInfo)
            .filter(ProjectInfo.name == "benchmark-project")
            .first()
        )

        if not project:
            print("Benchmark project not found. Nothing to clean.")
            return

        print(f"Found Benchmark Project: {project.name} (ID: {project.id})")

        # Find related points
        points = db.query(PointInfo).filter(PointInfo.project_id == project.id).all()
        point_ids = [p.id for p in points]

        # Find related deployments
        deployments = (
            db.query(DeploymentInfo)
            .filter(DeploymentInfo.point_id.in_(point_ids))
            .all()
        )
        deployment_ids = [d.id for d in deployments]

        # Delete Audios (Hard Delete for cleanup)
        deleted_audios = (
            db.query(AudioInfo)
            .filter(AudioInfo.deployment_id.in_(deployment_ids))
            .delete(synchronize_session=False)
        )
        print(f"Deleted {deleted_audios} Audio records.")

        # Delete Deployments, Points, Project, Recorders (Hard Delete)
        # Note: This is a simplified cleanup. In a real scenario, you might want to be more careful.
        db.query(DeploymentInfo).filter(DeploymentInfo.id.in_(deployment_ids)).delete(
            synchronize_session=False
        )
        db.query(PointInfo).filter(PointInfo.id.in_(point_ids)).delete(
            synchronize_session=False
        )
        db.query(ProjectInfo).filter(ProjectInfo.id == project.id).delete(
            synchronize_session=False
        )

        db.commit()
        print("Cleanup completed.")

    finally:
        db.close()


if __name__ == "__main__":
    cleanup_data()
