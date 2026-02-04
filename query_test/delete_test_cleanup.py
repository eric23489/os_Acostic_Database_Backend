import sys
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Add project root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.models.project import ProjectInfo
from app.models.point import PointInfo
from app.models.deployment import DeploymentInfo
from app.models.audio import AudioInfo
from app.models.user import UserInfo
from app.models.recorder import RecorderInfo

# Setup independent database connection for the script
SQLALCHEMY_DATABASE_URL = "postgresql://os_user1:os_user1@localhost:5432/acoustic_db"
engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def cleanup():
    print("\n--- Cleaning up (Hard Delete) ---")
    db = SessionLocal()
    try:
        # 1. Find projects
        projects = (
            db.query(ProjectInfo).filter(ProjectInfo.name.like("del-test-proj-%")).all()
        )
        project_ids = [p.id for p in projects]

        if not project_ids:
            print("No test projects found.")
        else:
            # 2. Find all points (including deleted ones if soft delete was applied)
            # Note: We query directly without is_deleted filter to clean up everything
            points = (
                db.query(PointInfo.id)
                .filter(PointInfo.project_id.in_(project_ids))
                .all()
            )
            point_ids = [p[0] for p in points]

            if point_ids:
                # 3. Find all deployments
                deployments = (
                    db.query(DeploymentInfo.id)
                    .filter(DeploymentInfo.point_id.in_(point_ids))
                    .all()
                )
                deployment_ids = [d[0] for d in deployments]

                if deployment_ids:
                    # 4. Delete Audios
                    deleted_audios = (
                        db.query(AudioInfo)
                        .filter(AudioInfo.deployment_id.in_(deployment_ids))
                        .delete(synchronize_session=False)
                    )
                    print(f"Hard deleted {deleted_audios} Audio records.")

                    # 5. Delete Deployments
                    db.query(DeploymentInfo).filter(
                        DeploymentInfo.id.in_(deployment_ids)
                    ).delete(synchronize_session=False)
                    print(f"Hard deleted {len(deployment_ids)} Deployment records.")

                # 6. Delete Points
                db.query(PointInfo).filter(PointInfo.id.in_(point_ids)).delete(
                    synchronize_session=False
                )
                print(f"Hard deleted {len(point_ids)} Point records.")

            # 7. Delete Projects
            db.query(ProjectInfo).filter(ProjectInfo.id.in_(project_ids)).delete(
                synchronize_session=False
            )
            print(f"Hard deleted {len(project_ids)} Project records.")

        # 8. Delete Recorder
        recorder_sn = "DEL-TEST-REC"
        db.query(RecorderInfo).filter(RecorderInfo.sn == recorder_sn).delete(
            synchronize_session=False
        )
        print("Hard deleted Test Recorder.")

        # 9. Delete Admin User
        admin_email = "delete_test_admin@example.com"
        db.query(UserInfo).filter(UserInfo.email == admin_email).delete(
            synchronize_session=False
        )
        print("Hard deleted Test Admin User.")

        db.commit()
        print("Cleanup completed successfully.")

    except Exception as e:
        print(f"Error during cleanup: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    cleanup()
