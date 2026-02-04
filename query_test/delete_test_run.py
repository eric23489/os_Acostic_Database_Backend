import sys
import os
import time
from unittest.mock import patch
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Add project root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from app.main import app
from app.models.project import ProjectInfo
from app.models.point import PointInfo
from app.models.deployment import DeploymentInfo
from app.models.audio import AudioInfo
from app.db.session import get_db
from app.core.security import create_access_token

# Setup independent database connection for the script
SQLALCHEMY_DATABASE_URL = "postgresql://os_user1:os_user1@localhost:5432/acoustic_db"
engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    try:
        db = SessionLocal()
        yield db
    finally:
        db.close()


def test_delete_api():
    print("\n--- Starting Delete API Test ---")
    db = SessionLocal()
    try:
        admin_email = "delete_test_admin@example.com"

        # Find test projects IDs to ensure we only delete test data
        test_projects = (
            db.query(ProjectInfo.id)
            .filter(ProjectInfo.name.like("del-test-proj-%"))
            .all()
        )
        test_project_ids = [p.id for p in test_projects]

        if not test_project_ids:
            print("No test projects found. Please run delete_test_seed.py first.")
            return

        # Override the get_db dependency to use the local connection
        app.dependency_overrides[get_db] = override_get_db

        # Patch SessionLocal in api_projects to use our local session maker
        # This is crucial for the background task which creates its own session
        with patch("app.api.v1.endpoints.api_projects.SessionLocal", SessionLocal):
            client = TestClient(app)

            # Generate Token
            token = create_access_token({"sub": admin_email})
            headers = {"Authorization": f"Bearer {token}"}

            # 1. Test Delete Audio
            print("\n[Test 1] Deleting an Audio...")
            audio = (
                db.query(AudioInfo)
                .join(DeploymentInfo)
                .join(PointInfo)
                .filter(PointInfo.project_id.in_(test_project_ids))
                .filter(AudioInfo.is_deleted == False)
                .first()
            )
            if audio:
                start_time = time.time()
                response = client.delete(f"/api/v1/audio/{audio.id}", headers=headers)
                end_time = time.time()
                if response.status_code == 200:
                    print(
                        f"Successfully deleted Audio ID {audio.id}. Time: {end_time - start_time:.4f}s"
                    )
                else:
                    print(
                        f"Failed to delete Audio ID {audio.id}. Status: {response.status_code}, Error: {response.text}"
                    )
            else:
                print("No active audio found to delete.")

            # 2. Test Delete Deployment
            print("\n[Test 2] Deleting a Deployment...")
            deployment = (
                db.query(DeploymentInfo)
                .join(PointInfo)
                .filter(PointInfo.project_id.in_(test_project_ids))
                .filter(DeploymentInfo.is_deleted == False)
                .first()
            )
            if deployment:
                start_time = time.time()
                response = client.delete(
                    f"/api/v1/deployments/{deployment.id}", headers=headers
                )
                end_time = time.time()
                if response.status_code == 200:
                    print(
                        f"Successfully deleted Deployment ID {deployment.id}. Time: {end_time - start_time:.4f}s"
                    )
                else:
                    print(
                        f"Failed to delete Deployment ID {deployment.id}. Status: {response.status_code}, Error: {response.text}"
                    )
            else:
                print("No active deployment found to delete.")

            # 3. Test Delete Point
            print("\n[Test 3] Deleting a Point...")
            point = (
                db.query(PointInfo)
                .filter(PointInfo.project_id.in_(test_project_ids))
                .filter(PointInfo.is_deleted == False)
                .first()
            )
            if point:
                start_time = time.time()
                response = client.delete(f"/api/v1/points/{point.id}", headers=headers)
                end_time = time.time()
                if response.status_code == 200:
                    print(
                        f"Successfully deleted Point ID {point.id}. Time: {end_time - start_time:.4f}s"
                    )
                else:
                    print(
                        f"Failed to delete Point ID {point.id}. Status: {response.status_code}, Error: {response.text}"
                    )
            else:
                print("No active point found to delete.")

            # 4. Test Delete Project (Delete remaining test projects)
            print("\n[Test 4] Deleting Projects...")
            projects = (
                db.query(ProjectInfo)
                .filter(
                    ProjectInfo.name.like("del-test-proj-%"),
                    ProjectInfo.is_deleted == False,
                )
                .all()
            )

            # Pick one project for detailed async verification
            if projects:
                project_to_verify = projects.pop(0)
                print(
                    f"\n[Test 4.1] Verifying async deletion for Project: {project_to_verify.name} (ID: {project_to_verify.id})"
                )

                # Find a sample audio file from this project to check later
                sample_audio = (
                    db.query(AudioInfo)
                    .join(DeploymentInfo)
                    .join(PointInfo)
                    .filter(PointInfo.project_id == project_to_verify.id)
                    .filter(AudioInfo.is_deleted == False)
                    .first()
                )
                sample_audio_id = sample_audio.id if sample_audio else None

                # Call the delete API
                start_time = time.time()
                response = client.delete(
                    f"/api/v1/projects/{project_to_verify.id}", headers=headers
                )
                end_time = time.time()

                assert response.status_code == 200
                api_response_time = end_time - start_time
                print(f"  - API responded in {api_response_time:.4f}s (asynchronous).")

                # Wait for background task to complete. Adjust time if needed.
                wait_time = 10  # seconds
                print(f"  - Waiting {wait_time}s for background audio deletion...")
                time.sleep(wait_time)

                # Verification step
                print("  - Verifying data state after deletion...")
                db.expire_all()  # Expire session cache to get fresh data from DB

                deleted_project = (
                    db.query(ProjectInfo)
                    .filter(ProjectInfo.id == project_to_verify.id)
                    .first()
                )
                assert deleted_project.is_deleted is True, (
                    "Project should be marked as deleted"
                )
                print("  - OK: Project is marked as deleted.")

                if sample_audio_id:
                    deleted_audio = (
                        db.query(AudioInfo)
                        .filter(AudioInfo.id == sample_audio_id)
                        .first()
                    )
                    assert deleted_audio.is_deleted is True, (
                        "Sample Audio should be marked as deleted"
                    )
                    print(
                        f"  - OK: Sample Audio ID {sample_audio_id} is marked as deleted."
                    )

            # Delete the rest of the projects without detailed verification
            if projects:
                print("\n[Test 4.2] Deleting remaining projects...")
                for project in projects:
                    client.delete(f"/api/v1/projects/{project.id}", headers=headers)
                    print(f"  - Sent delete request for Project ID {project.id}")

        # Clear overrides
        app.dependency_overrides.clear()
    finally:
        db.close()


if __name__ == "__main__":
    test_delete_api()
