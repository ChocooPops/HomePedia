"""Traduction des erreurs (bases de données, sources externes) en réponses HTTP."""

import httpx
from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from pymongo.errors import BulkWriteError
from sqlalchemy.exc import DBAPIError, IntegrityError


def _error(status: int, detail: str, **extra) -> JSONResponse:
    return JSONResponse(status_code=status, content=jsonable_encoder({"detail": detail, **extra}))


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(IntegrityError)
    async def pg_integrity_error(_: Request, exc: IntegrityError):
        return _error(409, str(exc.orig))

    @app.exception_handler(DBAPIError)
    async def pg_error(_: Request, exc: DBAPIError):
        return _error(400, str(exc.orig))

    @app.exception_handler(BulkWriteError)
    async def mongo_bulk_error(_: Request, exc: BulkWriteError):
        errors = [
            {k: e.get(k) for k in ("index", "code", "errmsg")} for e in (exc.details or {}).get("writeErrors", [])[:5]
        ]
        return _error(400, "Documents rejetés par MongoDB", errors=errors)

    @app.exception_handler(httpx.HTTPError)
    async def upstream_error(_: Request, exc: httpx.HTTPError):
        return _error(502, f"Source externe indisponible : {exc}")
