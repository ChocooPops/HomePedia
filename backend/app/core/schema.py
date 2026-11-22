"""Application des schémas au démarrage de l'API.

- PostgreSQL : schema/postgres.sql, exécuté tel quel dans une transaction.
- MongoDB    : schema/mongo.json, { collection: { "validator": {...}, "indexes": [...] } }.
               Chaque collection est créée (ou son validateur mis à jour) et ses index sont
               alignés sur le fichier (ajoutés, modifiés ou supprimés).
"""

import json
import logging
from pathlib import Path
from typing import Any

from pymongo import IndexModel
from pymongo.asynchronous.database import AsyncDatabase
from sqlalchemy.ext.asyncio import AsyncEngine

from app.core.database import execute_script

logger = logging.getLogger(__name__)


async def apply_postgres_schema(engine: AsyncEngine, path: Path) -> None:
    await execute_script(engine, [path.read_text(encoding="utf-8")])
    logger.info("Schéma PostgreSQL appliqué (%s)", path)


async def apply_mongo_schema(db: AsyncDatabase, path: Path) -> None:
    collections: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    existing = set(await db.list_collection_names())

    for name, spec in collections.items():
        options = {"validator": spec.get("validator", {}), "validationLevel": "strict", "validationAction": "error"}
        if name in existing:
            await db.command("collMod", name, **options)
        else:
            await db.create_collection(name, **options)
        await _sync_indexes(db, name, spec.get("indexes", []))

    logger.info("Schéma MongoDB appliqué (%s : %s)", path, ", ".join(collections))


async def _sync_indexes(db: AsyncDatabase, collection: str, specs: list[dict[str, Any]]) -> None:
    wanted = {
        spec["name"]: IndexModel(list(spec["keys"].items()), **{k: v for k, v in spec.items() if k != "keys"})
        for spec in specs
    }
    for name, info in (await db[collection].index_information()).items():
        if name != "_id_" and (name not in wanted or not _same_index(info, wanted[name].document)):
            await db[collection].drop_index(name)
    if wanted:
        await db[collection].create_indexes(list(wanted.values()))


def _same_index(info: dict[str, Any], spec: dict[str, Any]) -> bool:
    options = ("unique", "sparse", "partialFilterExpression", "expireAfterSeconds")
    return [(k, v) for k, v in info["key"]] == list(spec["key"].items()) and all(
        info.get(o) == spec.get(o) for o in options
    )
