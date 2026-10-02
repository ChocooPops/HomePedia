"""
Client HTTP commun à toutes les sources externes :
timeout, retries avec backoff exponentiel + jitter (respect de Retry-After),
limitation de débit par source, erreurs normalisées.
"""

import asyncio
import json
import logging
import random
from dataclasses import dataclass
from typing import Any

import httpx

from .config import settings
from .errors import ExternalApiError

logger = logging.getLogger("http")

# Limites de débit appliquées côté client, par source : (requêtes simultanées, intervalle minimal entre deux départs en ms).
# Valeurs volontairement prudentes, sous les quotas publiés :
#  - BAN / API Géo : 50 req/s ; recherche-entreprises : 7 req/s
#  - Overpass : 2 requêtes simultanées max par IP, on reste à 1
#  - Sirene : 30 req/min ; Melodi (anonyme) : 30 req/min
#  - Open-Meteo gratuit : 600 req/min
DEFAULT_RATE_LIMIT = (4, 100)
RATE_LIMITS: dict[str, tuple[int, int]] = {
    "ban": (5, 25),
    "geo_api": (5, 25),
    "apicarto_cadastre": (2, 200),
    "apicarto_gpu": (2, 200),
    "overpass": (1, 1500),
    "opensky": (1, 10000),
    "recherche_entreprises": (2, 150),
    "sirene": (1, 2100),
    "insee_melodi": (1, 2100),
    "open_meteo_archive": (2, 200),
    "open_meteo_climate": (1, 500),
    "pvgis": (2, 100),
    "georisques": (3, 100),
    "tabular": (2, 200),
    "ign_navigation": (2, 100),
    "bdnb": (1, 500),
}

RETRYABLE_STATUSES = {408, 425, 429, 500, 502, 503, 504}


class RateLimiter:
    """Limiteur simple : concurrence max + espacement minimal entre deux départs."""

    def __init__(self, concurrency: int, min_interval_ms: int):
        self._slots = asyncio.Semaphore(concurrency)
        self._gate = asyncio.Lock()
        self._interval = min_interval_ms / 1000
        self._last_start = 0.0

    async def schedule(self, task):
        async with self._slots:
            async with self._gate:
                loop = asyncio.get_running_loop()
                wait = self._last_start + self._interval - loop.time()
                if wait > 0:
                    await asyncio.sleep(wait)
                self._last_start = loop.time()
            return await task()


@dataclass
class HttpResult:
    status: int
    data: Any
    headers: httpx.Headers


class HttpClient:
    def __init__(self):
        self._client: httpx.AsyncClient | None = None
        self._limiters: dict[str, RateLimiter] = {}

    async def start(self):
        self._client = httpx.AsyncClient(
            timeout=settings.http_timeout_ms / 1000,
            headers={"User-Agent": settings.http_user_agent, "Accept": "application/json"},
            follow_redirects=True,
            max_redirects=5,
        )

    async def close(self):
        if self._client:
            await self._client.aclose()

    async def get(self, url: str, *, source: str, **kwargs) -> Any:
        return (await self.request("GET", url, source=source, **kwargs)).data

    async def post(self, url: str, body: Any = None, *, source: str, **kwargs) -> Any:
        return (await self.request("POST", url, source=source, body=body, **kwargs)).data

    async def request(
        self,
        method: str,
        url: str,
        *,
        source: str,
        limiter_key: str | None = None,
        params: dict | None = None,
        headers: dict | None = None,
        body: Any = None,
        timeout_ms: int | None = None,
        allow_statuses: tuple[int, ...] | list[int] = (),
        text: bool = False,
        binary: bool = False,
        auth: tuple[str, str] | None = None,
    ) -> HttpResult:
        """
        `source` : code de la source (data_source.code), sert au débit et aux erreurs.
        `limiter_key` : clé de débit si différente de la source (ex. « tabular », partagé par plusieurs sources).
        `params` : les valeurs None sont ignorées. `body` : dict/list -> JSON, str/bytes -> envoyé tel quel.
        `allow_statuses` : statuts HTTP considérés comme « pas de donnée » plutôt que comme une erreur.
        `text` : renvoie le corps en texte (CSV, HTML) au lieu de le décoder en JSON ; `binary` : en octets (fichiers compressés).
        """
        limiter = self._limiter(limiter_key or source)
        kwargs: dict = {"headers": headers, "auth": auth}
        # Un dict vide effacerait la query string déjà présente dans l'URL (liens « next » des API paginées).
        if query := {k: v for k, v in (params or {}).items() if v is not None}:
            kwargs["params"] = query
        if timeout_ms:
            kwargs["timeout"] = timeout_ms / 1000
        if isinstance(body, (str, bytes)):
            kwargs["content"] = body
        elif body is not None:
            kwargs["json"] = body

        attempt = 1
        while True:
            res: httpx.Response | None = None
            network_error: Exception | None = None
            try:
                res = await limiter.schedule(lambda: self._client.request(method, url, **kwargs))
            except httpx.HTTPError as err:
                network_error = err

            if res is not None and (res.status_code < 400 or res.status_code in allow_statuses):
                data = res.content if binary else res.text if text else _decode(res)
                return HttpResult(res.status_code, data, res.headers)

            status = res.status_code if res is not None else None
            retryable = True if network_error else status in RETRYABLE_STATUSES
            if not retryable or attempt > settings.http_max_retries:
                raise ExternalApiError(source, _describe(url, res, network_error), status, retryable)
            delay = _backoff(attempt, res)
            logger.warning(
                "[%s] %s sur %s - tentative %s/%s, nouvel essai dans %s ms",
                source, status or type(network_error).__name__, url, attempt, settings.http_max_retries, delay,
            )
            await asyncio.sleep(delay / 1000)
            attempt += 1

    def _limiter(self, key: str) -> RateLimiter:
        if key not in self._limiters:
            self._limiters[key] = RateLimiter(*RATE_LIMITS.get(key, DEFAULT_RATE_LIMIT))
        return self._limiters[key]


def _decode(res: httpx.Response) -> Any:
    """JSON si le corps en est, texte sinon (certaines API répondent en JSON sans le bon Content-Type)."""
    try:
        return res.json()
    except ValueError:
        return res.text


def _backoff(attempt: int, res: httpx.Response | None) -> int:
    retry_after = res.headers.get("retry-after") if res is not None else None
    if retry_after:
        try:
            return int(min(float(retry_after) * 1000, 60000))
        except ValueError:
            pass
    # Quota « par minute » sans Retry-After (ex. Open-Meteo) : attendre la fenêtre suivante.
    if res is not None and res.status_code == 429:
        return min(20000 * attempt, 61000)
    return min(500 * 2 ** (attempt - 1) + random.randrange(250), 15000)


def _describe(url: str, res: httpx.Response | None, err: Exception | None) -> str:
    if err is not None:
        if isinstance(err, httpx.TimeoutException):
            return f"Timeout sur {url}"
        return f"Erreur réseau sur {url} : {type(err).__name__} {err}".rstrip()
    data = _decode(res)
    body = data if isinstance(data, str) else json.dumps(data, ensure_ascii=False)
    return f"HTTP {res.status_code} sur {url} : {body[:300]}"


http = HttpClient()
