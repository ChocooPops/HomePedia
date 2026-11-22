import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.app_module import register_modules
from app.core.config import get_settings
from app.core.database import create_mongo_client, create_pg_engine
from app.core.exceptions import register_exception_handlers
from app.core.schema import apply_mongo_schema, apply_postgres_schema

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    app.state.pg_engine = create_pg_engine(settings)
    app.state.mongo_client = create_mongo_client(settings)
    app.state.mongo_db = app.state.mongo_client[settings.mongo_db]

    # Schémas de chaque base (l'API ne démarre pas si l'un d'eux est invalide).
    await apply_postgres_schema(app.state.pg_engine, settings.postgres_schema_path)
    await apply_mongo_schema(app.state.mongo_db, settings.mongo_schema_path)

    yield

    await app.state.pg_engine.dispose()
    await app.state.mongo_client.close()


app = FastAPI(title="HomePedia API", version="0.1.0", lifespan=lifespan)
register_exception_handlers(app)
register_modules(app)
