from typing import Annotated

import httpx
from fastapi import Depends, HTTPException

from app.core.config import get_settings


class ScrapeUnblockerClient:
    """Récupère le HTML d'une page via l'API ScrapeUnblocker (commun à tous les sites).

    Chaque appel consomme un crédit du compte ScrapeUnblocker.
    """

    def __init__(self) -> None:
        settings = get_settings()
        self.endpoint = settings.scrape_unblocker_url
        self.header = settings.scrape_unblocker_header
        self.key = settings.scrape_unblocker_key

    async def get_page_source(self, url: str) -> str:
        if not self.key:
            raise HTTPException(503, "SCRAPE_UNBLOCKER_KEY n'est pas configurée")
        # Le rendu de la page par ScrapeUnblocker peut prendre plusieurs dizaines de secondes.
        async with httpx.AsyncClient(timeout=120) as client:
            response = await client.post(self.endpoint, params={"url": url}, headers={self.header: self.key})
        if response.status_code >= 400:
            # Pas de raise_for_status : son message reprend la requête, inutile de l'exposer.
            raise HTTPException(502, f"ScrapeUnblocker a répondu {response.status_code} pour {url}")
        return response.text


ScrapeUnblockerClientDep = Annotated[ScrapeUnblockerClient, Depends(ScrapeUnblockerClient)]
