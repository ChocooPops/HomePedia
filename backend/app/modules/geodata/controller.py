from typing import Annotated

from fastapi import Query

from app.core.controller import controller, get
from app.modules.geodata.dto import CommuneDto, DepartmentDto, RegionDto, SearchResultDto
from app.modules.geodata.service import GeoDataServiceDep


@controller("/geodata", tags=["geodata"])
class GeoDataController:
    service: GeoDataServiceDep

    @get("/regions", response_model=list[RegionDto])
    async def get_regions(self):
        return await self.service.get_regions()

    @get("/regions/{code}/departments", response_model=list[DepartmentDto])
    async def get_departments_by_region(self, code: str):
        return await self.service.get_departments_by_region(code)

    @get("/departments/{code}/communes", response_model=list[CommuneDto])
    async def get_communes_by_department(self, code: str):
        return await self.service.get_communes_by_department(code)

    @get("/search", response_model=list[SearchResultDto])
    async def search(self, q: Annotated[str, Query(min_length=2, max_length=200, description="Texte recherché")]):
        """Régions, départements et communes par nom ou code, puis adresses (géocodeur IGN)."""
        return await self.service.search(q)
