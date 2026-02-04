import sys
import os
import random
from datetime import datetime, timezone

# Add project root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.session import SessionLocal
from app.models.project import ProjectInfo
from app.models.point import PointInfo
from app.models.recorder import RecorderInfo
from app.models.deployment import DeploymentInfo
from app.models.audio import AudioInfo


def seed_data(num_audios=10000):
    db = SessionLocal()
    try:
        print("--- Seeding Test Data ---")

        # 1. Create Project
        project = ProjectInfo(
            name="benchmark-project",
            name_zh="效能測試專案",
            description="Project for benchmarking query performance",
        )
        db.add(project)
        db.commit()
        db.refresh(project)
        print(f"Created Project: {project.name} (ID: {project.id})")

        # 2. Create Point
        point = PointInfo(
            project_id=project.id,
            name="Benchmark-Point",
            gps_lat_plan=23.5,
            gps_lon_plan=121.5,
        )
        db.add(point)
        db.commit()
        db.refresh(point)
        print(f"Created Point: {point.name} (ID: {point.id})")

        # 3. Create Recorder
        recorder = RecorderInfo(
            brand="Benchmark",
            model="Tester",
            sn=f"BM-{random.randint(1000, 9999)}",
            sensitivity=-170.0,
        )
        db.add(recorder)
        db.commit()
        db.refresh(recorder)
        print(f"Created Recorder: {recorder.sn} (ID: {recorder.id})")

        # 4. Create Deployment
        deployment = DeploymentInfo(
            point_id=point.id,
            recorder_id=recorder.id,
            phase=1,
            start_time=datetime.now(timezone.utc),
            status="benchmark",
        )
        db.add(deployment)
        db.commit()
        db.refresh(deployment)
        print(f"Created Deployment: ID {deployment.id}")

        # 5. Create Audios (Bulk Insert)
        print(f"Generating {num_audios} Audio records...")
        audios = []
        for i in range(num_audios):
            audio = AudioInfo(
                deployment_id=deployment.id,
                file_name=f"20240101_{i:06d}.wav",
                object_key=f"benchmark-project/Benchmark-Point/2024/01/Raw_Data/20240101_{i:06d}.wav",
                file_format="wav",
                file_size=1024 * 1024,  # 1MB
                record_time=datetime.now(timezone.utc),
                record_duration=60.0,
                fs=96000,
                recorder_channel=1,
                audio_channels=1,
            )
            audios.append(audio)

            # Batch insert every 1000 records to avoid memory issues
            if len(audios) >= 1000:
                db.bulk_save_objects(audios)
                db.commit()
                audios = []
                print(f"Inserted {i + 1} records...")

        if audios:
            db.bulk_save_objects(audios)
            db.commit()

        print(
            f"Successfully seeded {num_audios} Audio records for Deployment {deployment.id}"
        )
        return deployment.id

    finally:
        db.close()


if __name__ == "__main__":
    seed_data()
