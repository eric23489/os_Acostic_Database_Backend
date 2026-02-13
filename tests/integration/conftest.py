import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.core.security import hash_password
from app.db.session import get_db
from app.main import app
from app.models.deployment import DeploymentInfo
from app.models.point import PointInfo
from app.models.project import ProjectInfo
from app.models.recorder import RecorderInfo
from app.models.user import UserInfo

# Use a separate database for integration tests
TEST_DATABASE_URL = settings.get_database_url()

engine = create_engine(TEST_DATABASE_URL)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def db_session():
    """
    Pytest fixture for providing a SQLAlchemy database session to a test function,
    with proper transaction handling and dependency overriding for FastAPI.
    """
    connection = engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)

    # Replace the app's get_db dependency with our test session
    app.dependency_overrides[get_db] = lambda: session

    yield session

    # Rollback transaction and close session after test
    session.close()
    transaction.rollback()
    connection.close()
    # Clear the dependency override
    app.dependency_overrides.clear()


@pytest.fixture(scope="module")
def api_client():
    """
    Provides a TestClient for making API requests to the test server.
    """
    with TestClient(app) as client:
        yield client


@pytest.fixture(scope="function")
def auth_headers(api_client, db_session):
    """
    Creates a unique test user, logs in, and returns authentication headers.
    Function-scoped to ensure test isolation.
    """
    unique_id = uuid.uuid4().hex[:6]
    test_user_email = f"test_integration_{unique_id}@example.com"
    test_user_password = "testpassword"

    # Manually create user to avoid UserService's commit
    user = UserInfo(
        email=test_user_email,
        password_hash=hash_password(test_user_password),
        full_name="Integration Test User",
    )
    db_session.add(user)
    db_session.flush()

    response = api_client.post(
        f"{settings.api_prefix}/users/login",
        data={"username": test_user_email, "password": test_user_password},
    )
    response.raise_for_status()
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="function")
def test_deployment(db_session):
    """
    Creates a test Project, Point, and Deployment for a test run.
    Uses unique names to prevent collisions between test runs.
    """
    unique_id = uuid.uuid4().hex[:6]
    project = ProjectInfo(
        name=f"integration-test-project-{unique_id}",
        name_zh=f"整合測試專案 {unique_id}",
    )
    db_session.add(project)
    db_session.flush()

    point = PointInfo(
        name=f"TestPoint{unique_id}",
        project_id=project.id,
        gps_lat_plan=23.5,
        gps_lon_plan=121.0,
    )
    db_session.add(point)
    db_session.flush()

    # SN 必須是純數字 (用於檔名格式驗證: {sn}.{YYMMDDHHMMSS}.wav)
    numeric_sn = str(abs(hash(unique_id)) % 10000000)
    recorder = RecorderInfo(
        brand="TestBrand",
        model="TestModel",
        sn=numeric_sn,
        sensitivity=-150.0,
    )
    db_session.add(recorder)
    db_session.flush()

    deployment = DeploymentInfo(point_id=point.id, recorder_id=recorder.id)
    db_session.add(deployment)
    db_session.flush()

    return {
        "project": project,
        "point": point,
        "deployment": deployment,
        "recorder": recorder,
    }


@pytest.fixture(scope="module")
def s3_client():
    """
    Provides a boto3 client for interacting with MinIO.
    Uses 'minio' hostname for Docker network connectivity.
    """
    import boto3
    from botocore.client import Config

    # 在 Docker 內使用服務名稱 'minio' 而非 'localhost'
    return boto3.client(
        "s3",
        endpoint_url=f"http://minio:{settings.minio_port}",
        aws_access_key_id=settings.aws_access_key_id,
        aws_secret_access_key=settings.aws_secret_access_key,
        config=Config(signature_version="s3v4"),
        region_name="us-east-1",
    )
