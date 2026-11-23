from typing import Literal

from pydantic import BaseModel, Field

# MultiPolygon GeoJSON : polygones > anneaux > points [longitude, latitude]
MultiPolygonCoordinates = list[list[list[list[float]]]]


class RegionDto(BaseModel):
    code: str = Field(description="Code INSEE de la région")
    name: str
    coordinates: MultiPolygonCoordinates = Field(description="Contour (MultiPolygon GeoJSON)")


class DepartmentDto(BaseModel):
    code: str = Field(description="Code INSEE du département")
    name: str
    region_code: str
    coordinates: MultiPolygonCoordinates = Field(description="Contour (MultiPolygon GeoJSON)")


class CommuneDto(BaseModel):
    code: str = Field(description="Code INSEE de la commune")
    name: str
    department_code: str
    coordinates: MultiPolygonCoordinates = Field(description="Contour (MultiPolygon GeoJSON)")


class SearchResultDto(BaseModel):
    kind: Literal["region", "department", "commune", "address"]
    code: str | None = Field(None, description="Code INSEE (absent pour une adresse)")
    name: str
    context: str | None = Field(None, description="Précision affichée sous le nom (région, département…)")
    bbox: list[float] = Field(
        description="Emprise [lon_min, lat_min, lon_max, lat_max] ; pour une adresse, le point répété"
    )
