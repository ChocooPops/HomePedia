from dataclasses import asdict
from typing import Annotated, Any

from fastapi import Depends
from sqlalchemy import text

from app.core.database import PgEngine
from app.modules.annonces.models import Listing

_COLUMNS = [
    "source",
    "source_id",
    "url",
    "transaction_type",
    "property_type",
    "price",
    "rooms",
    "bedrooms",
    "surface_m2",
    "floor",
    "floor_label",
    "energy_class",
    "street_number",
    "street",
    "postal_code",
    "city",
    "image_url",
    "geocodage_id",
]
_UPDATED = [c for c in _COLUMNS if c not in ("source", "source_id")]

# Une photo connue n'est pas effacée par un scraping qui n'en trouverait pas.
_SET = {"image_url": "image_url = COALESCE(EXCLUDED.image_url, annonces.image_url)"}

# Une annonce déjà connue (même site, même identifiant) est mise à jour, jamais dupliquée.
# xmax = 0 uniquement pour une ligne qui vient d'être insérée.
_UPSERT = text(
    f"INSERT INTO annonces ({', '.join(_COLUMNS)}) VALUES ({', '.join(':' + c for c in _COLUMNS)}) "
    f"ON CONFLICT (source, source_id) DO UPDATE SET "
    f"{', '.join(_SET.get(c, f'{c} = EXCLUDED.{c}') for c in _UPDATED)}, last_seen_at = now() "
    "RETURNING (xmax = 0) AS inserted"
)

# Filtres de liste autorisés : paramètre → condition SQL.
_FILTERS = {
    "source": "a.source = :source",
    "transaction_type": "a.transaction_type = :transaction_type",
    "property_type": "a.property_type = :property_type",
    "postal_code": "a.postal_code = :postal_code",
    "insee_codes": "g.citycode = ANY(:insee_codes)",
    "min_price": "a.price >= :min_price",
    "max_price": "a.price <= :max_price",
    # Emprise de la carte (annonces géocodées uniquement)
    "west": "g.longitude >= :west",
    "east": "g.longitude <= :east",
    "south": "g.latitude >= :south",
    "north": "g.latitude <= :north",
}


# Paris, Marseille et Lyon : le géocodeur renvoie le code de l'arrondissement, pas celui de la commune.
_ARRONDISSEMENTS = {
    "75056": [str(c) for c in range(75101, 75121)],
    "13055": [str(c) for c in range(13201, 13217)],
    "69123": [str(c) for c in range(69381, 69390)],
}


def commune_citycodes(code: str) -> list[str]:
    """Codes INSEE à chercher dans geocodage.citycode pour une commune (avec ses arrondissements)."""
    code = code.upper()
    return [code, *_ARRONDISSEMENTS.get(code, [])]


def department_of(commune_code: str) -> str:
    """Département d'une commune : 69123 → 69, 2A004 → 2A, 97411 → 974."""
    commune_code = commune_code.upper()
    return commune_code[:3] if commune_code.startswith("97") else commune_code[:2]


class AnnonceRepository:
    def __init__(self, pg: PgEngine) -> None:
        self.pg = pg

    async def upsert(self, listings: list[Listing], geocodage_ids: list[int | None]) -> tuple[int, int]:
        """Enregistre les annonces ; renvoie (insérées, mises à jour)."""
        inserted = 0
        async with self.pg.begin() as conn:
            for listing, geocodage_id in zip(listings, geocodage_ids):
                params = {**asdict(listing), "geocodage_id": geocodage_id}
                params = {c: params[c] for c in _COLUMNS}
                inserted += bool((await conn.execute(_UPSERT, params)).scalar_one())
        return inserted, len(listings) - inserted

    async def find(self, limit: int, offset: int, insee_code: str | None = None, **filters: Any) -> list[dict[str, Any]]:
        if insee_code:
            filters["insee_codes"] = commune_citycodes(insee_code)
        active = {k: v for k, v in filters.items() if v is not None}
        where = " AND ".join(_FILTERS[k] for k in active) or "TRUE"
        async with self.pg.connect() as conn:
            result = await conn.execute(
                text(
                    "SELECT a.*, g.latitude, g.longitude, g.score AS geocoding_score, "
                    "g.label AS geocoded_address, g.citycode AS insee_code "
                    "FROM annonces a LEFT JOIN geocodage g ON g.id = a.geocodage_id "
                    f"WHERE {where} ORDER BY a.last_seen_at DESC, a.id DESC LIMIT :limit OFFSET :offset"
                ),
                {**active, "limit": limit, "offset": offset},
            )
            return [dict(row) for row in result.mappings()]

    async def get(self, annonce_id: int) -> dict[str, Any] | None:
        async with self.pg.connect() as conn:
            result = await conn.execute(
                text("SELECT id, source, source_id, url FROM annonces WHERE id = :id"), {"id": annonce_id}
            )
            row = result.mappings().first()
            return dict(row) if row else None

    async def set_image_if_missing(self, annonce_id: int, image_url: str) -> None:
        async with self.pg.begin() as conn:
            await conn.execute(
                text("UPDATE annonces SET image_url = :url WHERE id = :id AND image_url IS NULL"),
                {"id": annonce_id, "url": image_url},
            )

    async def count_in_department(self, source: str, department_code: str, transaction_type: str) -> int:
        """Annonces géocodées d'un site dans un département (code INSEE de la commune préfixé par le département)."""
        async with self.pg.connect() as conn:
            result = await conn.execute(
                text(
                    "SELECT count(*) FROM annonces a JOIN geocodage g ON g.id = a.geocodage_id "
                    "WHERE a.source = :source AND a.transaction_type = :transaction_type AND g.citycode LIKE :prefix"
                ),
                {"source": source, "transaction_type": transaction_type, "prefix": f"{department_code}%"},
            )
            return result.scalar_one()

    async def log_scrape(self, source: str, zone_level: str, zone_code: str, transaction_type: str,
                         found: int = 0, error: str | None = None) -> None:
        async with self.pg.begin() as conn:
            await conn.execute(
                text(
                    "INSERT INTO scrapes (source, zone_level, zone_code, transaction_type, status, found, error) "
                    "VALUES (:source, :zone_level, :zone_code, :transaction_type, :status, :found, :error)"
                ),
                {
                    "source": source,
                    "zone_level": zone_level,
                    "zone_code": zone_code,
                    "transaction_type": transaction_type,
                    "status": "error" if error else "success",
                    "found": found,
                    "error": error,
                },
            )

    async def scraped_recently(self, source: str, zone_level: str, zone_code: str, transaction_type: str,
                               success_minutes: int, error_minutes: int) -> bool:
        """Un scraping de cette zone a-t-il eu lieu récemment (délai plus court après une erreur) ?"""
        async with self.pg.connect() as conn:
            result = await conn.execute(
                text(
                    "SELECT EXISTS (SELECT 1 FROM scrapes WHERE source = :source AND zone_level = :zone_level "
                    "AND zone_code = :zone_code AND transaction_type = :transaction_type AND scraped_at > now() - "
                    "make_interval(mins => CASE WHEN status = 'success' THEN CAST(:success_minutes AS int) ELSE CAST(:error_minutes AS int) END))"
                ),
                {
                    "source": source,
                    "zone_level": zone_level,
                    "zone_code": zone_code,
                    "transaction_type": transaction_type,
                    "success_minutes": success_minutes,
                    "error_minutes": error_minutes,
                },
            )
            return result.scalar_one()


AnnonceRepositoryDep = Annotated[AnnonceRepository, Depends(AnnonceRepository)]
