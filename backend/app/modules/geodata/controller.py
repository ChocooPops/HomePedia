from app.core.controller import controller, get
from app.modules.geodata.dto import CommuneDto, DepartmentDto, RegionDto
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
