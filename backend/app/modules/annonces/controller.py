from typing import Annotated

from fastapi import Query

from app.core.controller import controller, get, post
from app.modules.annonces.dto import (
    AnnonceDetailDto,
    AnnonceDto,
    AnnonceFiltersDto,
    MapQueryDto,
    MapResultDto,
    ScrapeRequestDto,
    ScrapeResultDto,
)
from app.modules.annonces.service import AnnoncesServiceDep


@controller("/annonces", tags=["annonces"])
class AnnoncesController:
    service: AnnoncesServiceDep

    @post("/scrape", response_model=ScrapeResultDto, response_model_exclude_none=True)
    async def scrape(self, body: ScrapeRequestDto):
        """Récupère une recherche sur un site d'annonces, puis enregistre et géocode les annonces."""
        return await self.service.scrape(body)

    @get("", response_model=list[AnnonceDto])
    async def list_annonces(self, filters: Annotated[AnnonceFiltersDto, Query()]):
        """Annonces enregistrées, les plus récemment vues d'abord."""
        return await self.service.find(filters)

    @get("/map", response_model=MapResultDto, response_model_exclude_none=True)
    async def find_on_map(self, query: Annotated[MapQueryDto, Query()]):
        """Annonces géocodées dans l'emprise de la carte.

        Si `department_code` est donné et qu'aucune annonce de ce département n'est en base,
        les sites sont d'abord interrogés (une page, donc un crédit ScrapeUnblocker par site).
        """
        return await self.service.find_on_map(query)

    @get("/{annonce_id}/details", response_model=AnnonceDetailDto)
    async def get_details(
        self,
        annonce_id: int,
        refresh: Annotated[bool, Query(description="Relire la page même si la fiche est déjà en base")] = False,
    ):
        """Fiche complète d'une annonce (description, caractéristiques, énergie, coûts, photos…).

        Lue dans MongoDB si elle y est déjà ; sinon la page de l'annonce est récupérée
        (un crédit ScrapeUnblocker), lue puis enregistrée.
        """
        return await self.service.get_details(annonce_id, refresh)
