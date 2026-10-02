import logging
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from http import HTTPStatus

import fastapi.encoders
from bson import ObjectId
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError
from starlette.exceptions import HTTPException

from . import sources
from .collector import collector
from .db import db
from .errors import ApiError
from .http_client import http
from .migrate import run_migrations
from .modules.building.router import router as building_router
from .modules.climate.router import router as climate_router
from .modules.collection.router import router as collection_router
from .modules.connectivity.router import router as connectivity_router
from .modules.energy.router import router as energy_router
from .modules.geo.router import router as geo_router
from .modules.listings.router import router as listings_router
from .modules.mobility.router import router as mobility_router
from .modules.nuisance.router import router as nuisance_router
from .modules.reviews.router import router as reviews_router
from .modules.risk.router import router as risk_router
from .modules.services.router import router as services_router
from .modules.socio.router import router as socio_router
from .modules.territory.router import router as territory_router
from .modules.water.router import router as water_router
from .mongo import mongo

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s [%(name)s] %(message)s")
logger = logging.getLogger("api")


def _iso_utc(d: datetime) -> str:
    """Les dates de la base sont en UTC sans fuseau : on les publie en ISO 8601 avec « Z »."""
    if d.tzinfo:
        d = d.astimezone(UTC)
    return d.strftime("%Y-%m-%dT%H:%M:%S.") + f"{d.microsecond // 1000:03d}Z"


# Sérialisation JSON des réponses : dates en UTC explicite, identifiants MongoDB en chaîne.
fastapi.encoders.ENCODERS_BY_TYPE[datetime] = _iso_utc
fastapi.encoders.ENCODERS_BY_TYPE[ObjectId] = str


@asynccontextmanager
async def lifespan(_: FastAPI):
    await db.connect()
    # Les migrations sont appliquées au démarrage.
    await run_migrations()
    await db.load_schema()
    await collector.reload_sources()
    await mongo.connect()
    await http.start()
    yield
    await http.close()
    await mongo.close()
    await db.close()


app = FastAPI(
    title="HomePedia API",
    description="Collecte, normalisation et consultation des données publiques et des annonces sur le logement en France",
    version="0.2.0",
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url=None,
    openapi_url="/api/openapi.json",
)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

ROUTERS = (
    # « /addresses/collect » doit précéder « /addresses/{id} ».
    collection_router, geo_router, building_router, risk_router, water_router, climate_router, nuisance_router,
    energy_router, services_router, socio_router, mobility_router, connectivity_router, listings_router,
    territory_router, reviews_router, sources.router,
)
for router in ROUTERS:
    app.include_router(router, prefix="/api")


# Format d'erreur uniforme : { statusCode, error, message, ...détails }.


@app.exception_handler(ApiError)
async def api_error(_: Request, exc: ApiError):
    return JSONResponse(exc.body(), status_code=exc.status)


@app.exception_handler(HTTPException)
async def http_error(_: Request, exc: HTTPException):
    body = {"statusCode": exc.status_code, "error": HTTPStatus(exc.status_code).phrase, "message": exc.detail}
    return JSONResponse(body, status_code=exc.status_code)


@app.exception_handler(RequestValidationError)
async def validation_error(_: Request, exc: RequestValidationError):
    messages = [
        f"{'.'.join(str(p) for p in e['loc'] if p not in ('body', 'query', 'path'))} : {e['msg']}".removeprefix(" : ")
        for e in exc.errors()
    ]
    return JSONResponse({"statusCode": 400, "error": "Bad Request", "message": messages}, status_code=400)


@app.exception_handler(SQLAlchemyError)
async def database_error(_: Request, exc: SQLAlchemyError):
    logger.error("%s", exc)
    body = {"statusCode": 500, "error": "DatabaseError", "message": "Erreur lors de l’accès à la base de données"}
    return JSONResponse(body, status_code=500)


@app.exception_handler(Exception)
async def internal_error(_: Request, exc: Exception):
    logger.exception("Erreur interne", exc_info=exc)
    return JSONResponse({"statusCode": 500, "error": "InternalError", "message": "Erreur interne"}, status_code=500)
