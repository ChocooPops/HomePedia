from typing import Annotated, Literal

from fastapi import APIRouter, Query
from pydantic import Field

from .db import db
from .schemas import PaginationQuery

router = APIRouter(prefix="/sources", tags=["sources"])


class FetchLogQuery(PaginationQuery):
    source: str | None = None
    status: Literal["success", "error", "skipped"] | None = None
    target: str | None = Field(None, description="Préfixe de cible, ex. « address:12 »")


@router.get("", summary="Registre des sources (statut de vérification, TTL, clé requise)")
async def list_sources():
    return await db.find("data_source", order="t.domain ASC, t.code ASC")


@router.get("/fetch-logs", summary="Journal des collectes (traçabilité, erreurs, durées)")
async def fetch_logs(q: Annotated[FetchLogQuery, Query()]):
    where = {k: v for k, v in {"sourceCode": q.source, "status": q.status}.items() if v}
    where_sql = "t.target_key LIKE :target" if q.target else None
    params = {"target": f"{q.target}%"} if q.target else None
    items = await db.find(
        "fetch_log", where, where_sql=where_sql, params=params, order="t.fetched_at DESC", limit=q.limit, offset=q.offset
    )
    total = await db.count("fetch_log", where, where_sql=where_sql, params=params)
    return {"total": total, "page": q.page, "limit": q.limit, "items": items}
