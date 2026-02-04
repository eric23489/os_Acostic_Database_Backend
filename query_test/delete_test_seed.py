import sys
import os
from datetime import datetime, timezone
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
from app.core.security import hash_password
from app.enums.enums import UserRole

# Setup independent database connection for the script
SQLALCHEMY_DATABASE_URL = "postgresql://os_user1:os_user1@localhost:5432/acoustic_db"
engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def seed_data():
    db = SessionLocal()
    try:
        print("--- Seeding Delete Test Data ---")

        # 1. Create a Test Admin User for API calls
        admin_email = "delete_test_admin@example.com"
        admin_user = db.query(UserInfo).filter(UserInfo.email == admin_email).first()
        if not admin_user:
            admin_user = UserInfo(
                email=admin_email,
                password_hash=hash_password("password"),
                full_name="Delete Test Admin",
                role=UserRole.ADMIN.value,
                is_active=True,
            )
            db.add(admin_user)
            db.commit()
            db.refresh(admin_user)
        print(f"Using Admin User: {admin_user.email} (ID: {admin_user.id})")

        # 2. Create Recorder (Shared)
        recorder_sn = "DEL-TEST-REC"
        recorder = db.query(RecorderInfo).filter(RecorderInfo.sn == recorder_sn).first()
        if not recorder:
            recorder = RecorderInfo(
                brand="TestBrand",
                model="TestModel",
                sn=recorder_sn,
                sensitivity=-170.0,
            )
            db.add(recorder)
            db.commit()
            db.refresh(recorder)
        print(f"Using Recorder: {recorder.sn} (ID: {recorder.id})")

        # 3. Create Projects structure
        # 5 Projects
        for p_idx in range(5):
            project_name = f"del-test-proj-{p_idx}"
            project = (
                db.query(ProjectInfo).filter(ProjectInfo.name == project_name).first()
            )
            if not project:
                project = ProjectInfo(
                    name=project_name,
                    name_zh=f"刪除測試專案-{p_idx}",
                    description="Project for delete API testing",
                )
                db.add(project)
                db.commit()
                db.refresh(project)
                print(
                    f"Created Project {p_idx + 1}/5: {project.name} (ID: {project.id})"
                )

                # 5 Points per Project
                for pt_idx in range(5):
                    point = PointInfo(
                        project_id=project.id,
                        name=f"Pt-{pt_idx}",
                        gps_lat_plan=23.5,
                        gps_lon_plan=121.5,
                    )
                    db.add(point)
                    db.commit()
                    db.refresh(point)

                    # 2 Deployments per Point
                    for d_idx in range(2):
                        deployment = DeploymentInfo(
                            point_id=point.id,
                            recorder_id=recorder.id,
                            phase=d_idx + 1,
                            start_time=datetime.now(timezone.utc),
                            status="test",
                        )
                        db.add(deployment)
                        db.commit()
                        db.refresh(deployment)

                        # 10000 Audios per Deployment
                        audios = []
                        for a_idx in range(10000):
                            audio = AudioInfo(
                                deployment_id=deployment.id,
                                file_name=f"test_{a_idx}.wav",
                                object_key=f"{project.name}/{point.name}/{deployment.phase}/{a_idx}.wav",
                                file_format="wav",
                                file_size=1024,
                                record_time=datetime.now(timezone.utc),
                            )
                            audios.append(audio)

                        db.bulk_save_objects(audios)
                        db.commit()
                        print(
                            f"  - Populated Deployment {d_idx + 1}/2 for Point {pt_idx + 1} with 10,000 audios."
                        )
            else:
                print(f"Project {project.name} already exists.")

    finally:
        db.close()


if __name__ == "__main__":
    seed_data()
