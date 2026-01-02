from app.core.config import Settings


def test_get_database_url(monkeypatch):
    """Ensure database URL is built from environment variables."""
    monkeypatch.setenv("POSTGRES_USER", "tester")
    monkeypatch.setenv("POSTGRES_PASSWORD", "secret")
    monkeypatch.setenv("POSTGRES_DB", "sample_db")
    monkeypatch.setenv("POSTGRES_IP_ADDRESS", "db-host")
    monkeypatch.setenv("POSTGRES_PORT", "15432")

    cfg = Settings()

    assert (
        cfg.get_database_url()
        == "postgresql://tester:secret@db-host:15432/sample_db"
    )
