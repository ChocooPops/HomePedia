"""Connexions aux bases et « providers » injectables dans les services (équivalent des providers Nest)."""

from enum import Enum
from typing import Annotated

from fastapi import Depends, Request
from pymongo import AsyncMongoClient
from pymongo.asynchronous.database import AsyncDatabase
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from app.core.config import Settings


class Database(str, Enum):
    postgres = "postgres"
    mongo = "mongo"


def create_pg_engine(settings: Settings) -> AsyncEngine:
    return create_async_engine(settings.postgres_url, pool_pre_ping=True)


def create_mongo_client(settings: Settings) -> AsyncMongoClient:
    return AsyncMongoClient(settings.mongo_uri, tz_aware=True)


async def execute_script(engine: AsyncEngine, statements: list[str]) -> None:
    """Exécute des scripts SQL bruts (plusieurs instructions par chaîne) dans une seule transaction."""
    async with engine.connect() as conn:
        raw = await conn.get_raw_connection()
        driver = raw.driver_connection  # connexion asyncpg
        async with driver.transaction():
            for sql in statements:
                await driver.execute(sql)


# --- Injection de dépendances ------------------------------------------------


def get_pg_engine(request: Request) -> AsyncEngine:
    return request.app.state.pg_engine


def get_mongo_db(request: Request) -> AsyncDatabase:
    return request.app.state.mongo_db


PgEngine = Annotated[AsyncEngine, Depends(get_pg_engine)]
MongoDb = Annotated[AsyncDatabase, Depends(get_mongo_db)]
