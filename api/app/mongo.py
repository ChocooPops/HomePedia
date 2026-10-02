"""MongoDB : réponses brutes (raw_payloads), annonces scrapées (listings), contours GeoJSON (contours), avis (reviews)."""

from pymongo import ASCENDING, DESCENDING, GEOSPHERE, AsyncMongoClient
from pymongo.asynchronous.collection import AsyncCollection

from .config import settings


class Mongo:
    def __init__(self):
        self.client: AsyncMongoClient | None = None

    async def connect(self):
        self.client = AsyncMongoClient(settings.mongo_uri, serverSelectionTimeoutMS=5000, tz_aware=False)
        await self.raw_payloads.create_index([("sourceCode", ASCENDING), ("targetKey", ASCENDING), ("createdAt", DESCENDING)])
        await self.listings.create_index([("source", ASCENDING), ("sourceId", ASCENDING)], unique=True)
        await self.listings.create_index([("location", GEOSPHERE)])
        await self.listings.create_index([("inseeCode", ASCENDING), ("transactionType", ASCENDING), ("propertyType", ASCENDING)])
        await self.listings.create_index([("departmentCode", ASCENDING), ("transactionType", ASCENDING)])
        await self.listings.create_index([("lastSeenAt", DESCENDING)])

        await self.contours.create_index([("level", ASCENDING), ("code", ASCENDING)], unique=True)
        await self.contours.create_index([("level", ASCENDING), ("parentCode", ASCENDING)])
        await self.reviews.create_index([("source", ASCENDING), ("externalId", ASCENDING)], unique=True)
        await self.reviews.create_index([("inseeCode", ASCENDING), ("source", ASCENDING), ("kind", ASCENDING)])
        await self.reviews.create_index([("location", GEOSPHERE)], sparse=True)

    async def close(self):
        if self.client:
            await self.client.close()

    @property
    def raw_payloads(self) -> AsyncCollection:
        return self.client.get_default_database()["raw_payloads"]

    @property
    def listings(self) -> AsyncCollection:
        return self.client.get_default_database()["listings"]

    @property
    def contours(self) -> AsyncCollection:
        return self.client.get_default_database()["contours"]

    @property
    def reviews(self) -> AsyncCollection:
        return self.client.get_default_database()["reviews"]


mongo = Mongo()
