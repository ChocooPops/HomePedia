"""
Exécute une collecte « source × cible » en gérant :
 - le cache : si une collecte réussie non expirée existe, on ne rappelle pas l'API ;
 - la journalisation (fetch_log) : statut, durée, nombre d'éléments, erreur ;
 - l'archivage optionnel de la réponse brute (MongoDB, collection raw_payloads).
Les erreurs sont capturées et renvoyées dans le résultat : une source en panne
n'interrompt pas la collecte des autres.

Un « stamp » est le dict { sourceCode, fetchedAt, expiresAt } à recopier dans chaque ligne persistée.
Un résultat de collecte (« outcome ») est le dict { source, target, status, items, fetchedAt?, expiresAt?, error? },
avec status = success | cached | error | skipped.
"""

import json
import logging
import time
from collections.abc import Awaitable, Callable
from datetime import timedelta

from .config import settings
from .db import db
from .errors import ApiError, ExternalApiError, MissingApiKeyError, NotFound
from .mongo import mongo
from .parse import utcnow

logger = logging.getLogger("collector")
MAX_RAW_PAYLOAD_CHARS = 4 * 1024 * 1024


class Collector:
    def __init__(self):
        self.sources: dict[str, dict] = {}

    async def reload_sources(self):
        self.sources = {s["code"]: s for s in await db.find("data_source")}

    def source(self, code: str) -> dict:
        if code not in self.sources:
            raise NotFound(f"Source inconnue : {code}")
        return self.sources[code]

    def stamp(self, code: str) -> dict:
        at = utcnow()
        return {"sourceCode": code, "fetchedAt": at, "expiresAt": at + timedelta(seconds=self.source(code)["ttlSeconds"])}

    async def fresh_log(self, source_code: str, target_key: str) -> dict | None:
        """Dernière collecte réussie et encore valide pour cette cible."""
        return await db.find_one(
            "fetch_log",
            {"sourceCode": source_code, "targetKey": target_key, "status": "success"},
            where_sql="t.expires_at > :now",
            params={"now": utcnow()},
            order="t.fetched_at DESC",
        )

    async def run(
        self,
        source_code: str,
        target_key: str,
        task: Callable[[dict], Awaitable[dict]],
        *,
        force: bool = False,
    ) -> dict:
        """
        `task(stamp)` fait l'appel externe, normalise, stocke, et renvoie { "items": n, "raw": réponse brute optionnelle }.
        """
        if not force:
            fresh = await self.fresh_log(source_code, target_key)
            if fresh:
                return {
                    "source": source_code, "target": target_key, "status": "cached", "items": fresh["itemsCount"],
                    "fetchedAt": fresh["fetchedAt"], "expiresAt": fresh["expiresAt"],
                }

        stamp = self.stamp(source_code)
        started = time.monotonic()
        try:
            result = await task(stamp)
        except Exception as err:  # noqa: BLE001 - une source en panne ne doit pas interrompre les autres
            skipped = isinstance(err, MissingApiKeyError)
            message = _error_message(err)
            if not skipped:
                logger.warning("[%s] %s : %s", source_code, target_key, message)
                if not isinstance(err, ApiError):
                    logger.debug("Détail de l'erreur", exc_info=err)
            await db.insert("fetch_log", {
                "sourceCode": source_code,
                "targetKey": target_key,
                "status": "skipped" if skipped else "error",
                "httpStatus": err.upstream_status if isinstance(err, ExternalApiError) else None,
                "durationMs": _elapsed_ms(started),
                "errorMessage": message[:1000],
                "fetchedAt": stamp["fetchedAt"],
                "expiresAt": None,
            })
            return {
                "source": source_code, "target": target_key, "status": "skipped" if skipped else "error", "items": 0, "error": message,
            }

        log_id = await db.insert("fetch_log", {
            "sourceCode": source_code,
            "targetKey": target_key,
            "status": "success",
            "itemsCount": result["items"],
            "durationMs": _elapsed_ms(started),
            "fetchedAt": stamp["fetchedAt"],
            "expiresAt": stamp["expiresAt"],
        })
        await self._archive(log_id, source_code, target_key, result.get("raw"))
        return {
            "source": source_code, "target": target_key, "status": "success", "items": result["items"],
            "fetchedAt": stamp["fetchedAt"], "expiresAt": stamp["expiresAt"],
        }

    async def _archive(self, log_id: int, source_code: str, target_key: str, raw):
        if not settings.store_raw_payloads or raw is None:
            return
        try:
            if len(json.dumps(raw, default=str)) > MAX_RAW_PAYLOAD_CHARS:
                return
            await mongo.raw_payloads.insert_one({
                "fetchLogId": log_id, "sourceCode": source_code, "targetKey": target_key, "payload": raw, "createdAt": utcnow(),
            })
        except Exception as err:  # noqa: BLE001
            # L'archive est un confort : son échec ne doit pas faire passer la collecte en erreur.
            logger.warning("[%s] %s : réponse brute non archivée (%s)", source_code, target_key, err)


def _elapsed_ms(started: float) -> int:
    return int((time.monotonic() - started) * 1000)


def _error_message(err: Exception) -> str:
    if isinstance(err, ApiError):
        return err.message if isinstance(err.message, str) else str(err.message)
    return str(err) or type(err).__name__


collector = Collector()
