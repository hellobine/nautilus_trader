from quantdeck_backend.config import Settings


def test_defaults():
    s = Settings()
    assert s.redis_url == "redis://localhost:6379"
    assert s.runs_dir.endswith("runs")
    assert isinstance(s.cors_origins, list)


def test_env_override(monkeypatch):
    monkeypatch.setenv("QD_REDIS_URL", "redis://example:6380")
    s = Settings()
    assert s.redis_url == "redis://example:6380"


def test_catalog_and_secrets_paths():
    s = Settings()
    assert s.catalog_dir.endswith("catalog")
    assert s.secrets_path.endswith("secrets.enc")


def test_catalog_dir_env_override(monkeypatch):
    monkeypatch.setenv("QD_CATALOG_DIR", "/tmp/qd_cat")
    s = Settings()
    assert s.catalog_dir == "/tmp/qd_cat"
