from typing import Annotated

import httpx
from fastapi import Depends, HTTPException

SEARCH_URL = "https://www.leboncoin.fr/recherche?category=9&real_estate_type=1,2"


class LeboncoinService:
    async def get_search_page(self) -> str:
        """Retourne le HTML complet de la page de recherche (ventes immobilières : maisons et appartements)."""
        async with httpx.AsyncClient(timeout=30, follow_redirects=True, headers={"User-Agent": "HomePedia-API"}) as client:
            response = await client.get(SEARCH_URL)

        if response.status_code != 200:
            blocked = response.headers.get("x-datadome") == "protected"
            reason = " (requête bloquée par la protection anti-robots DataDome)" if blocked else ""
            raise HTTPException(502, f"Leboncoin a répondu {response.status_code}{reason}")
        return response.text


LeboncoinServiceDep = Annotated[LeboncoinService, Depends(LeboncoinService)]
