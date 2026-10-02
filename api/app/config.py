from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Lecture typée du .env (mêmes variables que l'ancien backend)."""

    model_config = SettingsConfigDict(env_file=Path(__file__).parent.parent / ".env", env_file_encoding="utf-8", extra="ignore")

    port: int = 8000

    db_host: str = "localhost"
    db_port: int = 3306
    db_user: str = "homepedia"
    db_password: str = "homepedia"
    db_name: str = "homepedia"
    db_logging: bool = False

    mongo_uri: str = "mongodb://homepedia:homepedia@localhost:27017/homepedia?authSource=admin"

    http_timeout_ms: int = 20000
    http_max_retries: int = 3
    http_user_agent: str = "HomePedia/0.1 (projet etudiant Epitech)"
    store_raw_payloads: bool = True

    ingest_token: str | None = None

    meteofrance_api_key: str | None = None
    atmo_username: str | None = None
    atmo_password: str | None = None
    insee_sirene_api_key: str | None = None
    insee_api_key: str | None = None
    esante_api_key: str | None = None
    bdnb_api_key: str | None = None
    google_maps_api_key: str | None = None

    @field_validator(
        "ingest_token", "meteofrance_api_key", "atmo_username", "atmo_password",
        "insee_sirene_api_key", "insee_api_key", "esante_api_key", "bdnb_api_key", "google_maps_api_key",
        mode="before",
    )
    @classmethod
    def _blank_is_none(cls, v):
        return v.strip() or None if isinstance(v, str) else v

    @property
    def db_url(self) -> str:
        from sqlalchemy.engine import URL

        return URL.create(
            "mysql+aiomysql", self.db_user, self.db_password, self.db_host, self.db_port, self.db_name,
            query={"charset": "utf8mb4"},
        ).render_as_string(hide_password=False)


settings = Settings()
