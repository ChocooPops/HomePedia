"""Paramètres de requête et de chemin communs à plusieurs modules."""

from typing import Annotated

from fastapi import Path
from pydantic import BaseModel, ConfigDict, Field

INSEE_PATTERN = r"^(\d{5}|2[AB]\d{3})$"
DEPARTMENT_PATTERN = r"^(\d{2,3}|2[AB])$"

AddressId = Annotated[int, Path(ge=1, description="Identifiant de l'adresse enregistrée")]
InseeCode = Annotated[str, Path(pattern=INSEE_PATTERN, description="Code commune INSEE (5 caractères)")]


class StrictModel(BaseModel):
    """Refuse les paramètres inconnus, comme l'ancien ValidationPipe (forbidNonWhitelisted)."""

    model_config = ConfigDict(extra="forbid")


class CollectQuery(StrictModel):
    force: bool = Field(False, description="Ignore le cache et force un nouvel appel aux API")


class RadiusQuery(CollectQuery):
    radius: int | None = Field(None, ge=50, le=5000, description="Rayon de recherche en mètres")


class PaginationQuery(StrictModel):
    page: int = Field(1, ge=1)
    limit: int = Field(50, ge=1, le=500)

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.limit


class ModulesQuery(CollectQuery):
    modules: str | None = Field(
        None, description="Modules à collecter, séparés par des virgules (défaut : tous)", examples=["geo,risk,water"]
    )
