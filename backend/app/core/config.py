from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import URL


class Settings(BaseSettings):
    """Configuration lue depuis les variables d'environnement (ou un fichier .env)."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # --- PostgreSQL ---
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_user: str = "homepedia"
    postgres_password: str = "homepedia"
    postgres_db: str = "homepedia"

    # --- MongoDB ---
    mongo_uri: str = "mongodb://homepedia:homepedia@localhost:27017/?authSource=admin"
    mongo_db: str = "homepedia"

    # --- Schémas (appliqués au démarrage) ---
    postgres_schema_path: Path = Path("schema/postgres.sql")
    mongo_schema_path: Path = Path("schema/mongo.json")

    # --- Scraping (ScrapeUnblocker) ---
    scrape_unblocker_url: str = "https://api.scrapeunblocker.com/getPageSource"
    scrape_unblocker_header: str = "x-scrapeunblocker-key"
    scrape_unblocker_key: str = ""

    # --- Géocodage (Géoplateforme IGN) ---
    geocoding_url: str = "https://data.geopf.fr/geocodage/search"

    @property
    def postgres_url(self) -> URL:
        return URL.create(
            drivername="postgresql+asyncpg",
            username=self.postgres_user,
            password=self.postgres_password,
            host=self.postgres_host,
            port=self.postgres_port,
            database=self.postgres_db,
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
