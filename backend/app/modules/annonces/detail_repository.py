from datetime import datetime
from typing import Annotated, Any

from fastapi import Depends
from pymongo import ReturnDocument

from app.core.database import MongoDb
from app.modules.annonces.models import ListingDetail

COLLECTION = "annonce_details"


class DetailRepository:
    """Fiches complètes des annonces (collection MongoDB `annonce_details`), une par site et identifiant."""

    def __init__(self, mongo: MongoDb) -> None:
        self.collection = mongo[COLLECTION]

    async def find(self, source: str, source_id: str) -> dict[str, Any] | None:
        return await self.collection.find_one({"source": source, "source_id": source_id}, {"_id": 0})

    async def first_images(self, keys: list[tuple[str, str]]) -> dict[tuple[str, str], str]:
        """Première photo des fiches déjà enregistrées, par (source, source_id)."""
        if not keys:
            return {}
        cursor = self.collection.find(
            {"$or": [{"source": s, "source_id": i} for s, i in keys], "images.0": {"$exists": True}},
            {"_id": 0, "source": 1, "source_id": 1, "images": {"$slice": 1}},
        )
        return {(d["source"], d["source_id"]): d["images"][0]["url"] async for d in cursor}

    async def save(self, source: str, source_id: str, url: str, detail: ListingDetail, scraped_at: datetime) -> dict[str, Any]:
        """Remplace la fiche existante (nouveau scraping) ou la crée."""
        document = {"source": source, "source_id": source_id, "url": url, "scraped_at": scraped_at, **detail.model_dump()}
        return await self.collection.find_one_and_replace(
            {"source": source, "source_id": source_id},
            document,
            projection={"_id": 0},
            upsert=True,
            return_document=ReturnDocument.AFTER,
        )


DetailRepositoryDep = Annotated[DetailRepository, Depends(DetailRepository)]
