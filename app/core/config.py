try:
    from pydantic_settings import BaseSettings
except ImportError as exc:  # pragma: no cover - dependency guard
    try:
        from pydantic import BaseSettings  # type: ignore
    except ImportError:
        raise ImportError(
            "Install `pydantic-settings` (for pydantic v2) or ensure pydantic v1 is available."
        ) from exc


class Settings(BaseSettings):
    app_name: str = "OS Acoustic Backend"
    api_prefix: str = "/api/v1"
    database_url: str = "postgresql://user:password@localhost/acoustic_db"

    # Database settings
    
    postgres_user: str
    postgres_password: str
    postgres_db: str
    postgres_ip_address: str = "localhost"
    postgres_port: int = 5432

    # App settings
    app_port: int = 8000

    # MinIO / AWS settings
    minio_ip_address: str | None = None
    minio_port: int = 9000
    aws_access_key_id: str | None = None
    aws_secret_access_key: str | None = None
    minio_bucket_name: str = "data"
    
    def get_database_url(self) -> str:
        return f"postgresql://{self.postgres_user}:{self.postgres_password}@{self.postgres_ip_address}:{self.postgres_port}/{self.postgres_db}"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "ignore" # Ignore unexpected environment variables


settings = Settings()
