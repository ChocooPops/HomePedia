from typing import Annotated, Literal

from fastapi import APIRouter, Path, Query
from pydantic import Field, field_validator

from ...schemas import DEPARTMENT_PATTERN, CollectQuery, InseeCode, StrictModel
from . import service

router = APIRouter(tags=["territory"])

Department = Annotated[str, Path(pattern=DEPARTMENT_PATTERN, description="Code département (« 80 », « 2A », « 974 »)")]


class DepartmentListQuery(StrictModel):
    region: str | None = Field(None, pattern=r"^\d{2}$", examples=["32"])


class ContoursQuery(StrictModel):
    region: str | None = Field(None, pattern=r"^\d{2}$", description="Limite les départements à une région")


class DvfDepartmentQuery(CollectQuery):
    years: str | None = Field(None, description="Années séparées par des virgules (défaut : dernière année publiée)", examples=["2023,2024"])

    @field_validator("years")
    @classmethod
    def _years(cls, v: str | None) -> str | None:
        if v is not None and not all(part.strip().isdigit() and len(part.strip()) == 4 for part in v.split(",")):
            raise ValueError("years doit être une liste d'années séparées par des virgules")
        return v

    @property
    def year_list(self) -> list[int] | None:
        return [int(y) for y in self.years.split(",")] if self.years else None


class PricesQuery(StrictModel):
    year: int | None = Field(None, ge=2014, le=2100)
    type: Literal["Ensemble", "Appartement", "Maison"] = "Ensemble"


@router.get("/overview", summary="Volumes stockés et état des sources (tableau de bord)")
async def overview():
    return await service.overview()


@router.post("/territories/collect", status_code=201, summary="Charge les régions, les départements (API Géo) et leurs contours (france-geojson)")
async def collect_reference(q: Annotated[CollectQuery, Query()]):
    return await service.collect_reference(q.force)


@router.get("/regions", summary="Régions")
async def regions():
    return await service.list_regions()


@router.get("/regions/contours", summary="Contours des régions (GeoJSON)")
async def region_contours():
    return await service.contours("region")


@router.get("/departments", summary="Départements (filtre par région)")
async def departments(q: Annotated[DepartmentListQuery, Query()]):
    return await service.list_departments(q.region)


@router.get("/departments/contours", summary="Contours des départements (GeoJSON), éventuellement d’une seule région")
async def department_contours(q: Annotated[ContoursQuery, Query()]):
    return await service.contours("department", q.region)


@router.post("/departments/{dep}/contours/collect", status_code=201, summary="Charge les contours des communes du département (API Géo)")
async def collect_commune_contours(dep: Department, q: Annotated[CollectQuery, Query()]):
    return await service.collect_commune_contours(dep, q.force)


@router.get("/departments/{dep}/communes/contours", summary="Contours des communes du département (GeoJSON)")
async def commune_contours(dep: Department):
    return await service.contours("commune", dep)


@router.post("/departments/{dep}/dvf/collect", status_code=201, summary="Import DVF du département entier + recalcul des indices de prix communaux")
async def collect_department_dvf(dep: Department, q: Annotated[DvfDepartmentQuery, Query()]):
    return await service.collect_department_dvf(dep, q.year_list, q.force)


@router.get("/departments/{dep}/prices", summary="Prix au m² médian par commune du département (année et type de bien)")
async def department_prices(dep: Department, q: Annotated[PricesQuery, Query()]):
    return await service.department_prices(dep, q.year, q.type)


@router.post("/communes/{insee}/collect-all", status_code=201, summary="Collecte de la commune : contour, recensement, emploi, revenus, DVF, énergie")
async def collect_commune(insee: InseeCode, q: Annotated[CollectQuery, Query()]):
    return await service.collect_commune(insee, q.force)


@router.get("/communes/{insee}/report", summary="Fiche commune consolidée : démographie, emploi, revenus, marché, énergie, risques, avis")
async def commune_report(insee: InseeCode):
    return await service.commune_report(insee)
