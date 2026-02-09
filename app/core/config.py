try:
    from pydantic_settings import BaseSettings, SettingsConfigDict
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

    # Auth settings
    secret_key: str
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30

    # MinIO / AWS settings
    minio_ip_address: str | None = None
    minio_port: int = 9000
    aws_access_key_id: str | None = None
    aws_secret_access_key: str | None = None
    minio_bucket_name: str = "data"

    # Google OAuth settings
    google_oauth_client_id: str | None = None
    google_oauth_client_secret: str | None = None
    google_oauth_redirect_uri: str = "http://localhost:8000/api/v1/oauth/google/callback"

    # Password reset settings
    password_reset_token_expire_minutes: int = 30

    # Email settings (for password reset)
    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_user: str | None = None
    smtp_password: str | None = None
    smtp_from_email: str | None = None

    def get_database_url(self) -> str:
        return f"postgresql://{self.postgres_user}:{self.postgres_password}@{self.postgres_ip_address}:{self.postgres_port}/{self.postgres_db}"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


settings = Settings()
