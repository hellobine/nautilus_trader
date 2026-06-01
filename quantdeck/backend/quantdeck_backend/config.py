import os

from pydantic_settings import BaseSettings, SettingsConfigDict

_REPO_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..")
)


class Settings(BaseSettings):
    """应用配置。环境变量前缀 QD_，例如 QD_REDIS_URL。"""

    model_config = SettingsConfigDict(env_prefix="QD_", extra="ignore")

    redis_url: str = "redis://localhost:6379"
    runs_dir: str = os.path.join(_REPO_ROOT, "quantdeck", "runs")
    cors_origins: list[str] = ["http://localhost:5173"]
    catalog_dir: str = os.path.join(_REPO_ROOT, "quantdeck", "data", "catalog")
    config_dir: str = os.path.join(_REPO_ROOT, "quantdeck", "config")
    secrets_path: str = os.path.join(
        _REPO_ROOT, "quantdeck", "config", "secrets.enc"
    )


def get_settings() -> Settings:
    return Settings()
