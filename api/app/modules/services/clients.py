"""Récupération brute des sources du module services (santé, commerces, crèches, écoles, temps de trajet)."""

from ...config import settings
from ...errors import MissingApiKeyError
from ...http_client import http
from ...open_data import ods_records, overpass_query
from ...parse import js_round

# Codes NAF -> catégorie de service.
NAF_CATEGORIES: dict[str, str] = {
    "86.21Z": "general_practitioner",
    "47.73Z": "pharmacy",
    "86.10Z": "hospital",
    "10.71C": "bakery",
    "88.91A": "childcare",
    "47.11F": "supermarket",
    "47.11D": "supermarket",
    "53.10Z": "post_office",
}

EDUCATION_BASE = "https://data.education.gouv.fr/api/explore/v2.1"


async def recherche_entreprises_near_point(p: dict, radius_km: float, naf: list[str], max_pages: int = 8) -> list[dict]:
    """Établissements actifs dans un rayon (km), filtrés par code NAF."""
    out: list[dict] = []
    for page in range(1, max_pages + 1):
        res = await http.get(
            "https://recherche-entreprises.api.gouv.fr/near_point",
            source="recherche_entreprises",
            params={
                "lat": p["lat"], "long": p["lon"], "radius": radius_km,
                "activite_principale": ",".join(naf), "per_page": 25, "page": page,
            },
        )
        for ul in res.get("results") or []:
            for e in ul.get("matching_etablissements") or []:
                out.append({**e, "nom_complet": ul.get("nom_complet")})
        total_pages = res.get("total_pages")
        if page >= (total_pages if total_pages is not None else 1):
            break
    return out


async def overpass_around(p: dict, radius_m: int, emergency_radius_m: int) -> list[dict]:
    """Urgences (rayon large), pharmacies, boulangeries et crèches avec horaires OSM."""
    a = f"around:{radius_m},{p['lat']},{p['lon']}"
    e = f"around:{emergency_radius_m},{p['lat']},{p['lon']}"
    return await overpass_query(f"""[out:json][timeout:60];
(
  nwr({e})[amenity=hospital][emergency=yes];
  nwr({e})[healthcare=hospital][emergency=yes];
  nwr({a})[amenity~"^(pharmacy|childcare|kindergarten)$"];
  nwr({a})[shop=bakery];
);
out center tags;""")


async def education_schools_around(p: dict, radius_m: int) -> list[dict]:
    return await ods_records(
        "education", EDUCATION_BASE, "fr-en-annuaire-education",
        {"where": f"within_distance(position, geom'POINT({p['lon']} {p['lat']})', {radius_m}m) AND etat=\"OUVERT\""},
        200,
    )


def _quoted(uais: list[str]) -> str:
    return ",".join(f'"{u}"' for u in uais)


async def education_ips(dataset: str, uais: list[str]) -> list[dict]:
    """IPS : jeux distincts écoles / collèges (fr-en-ips-ecoles-ap2022, fr-en-ips-colleges-ap2023) ; on garde la rentrée la plus récente."""
    if not uais:
        return []
    return await ods_records(
        "education", EDUCATION_BASE, dataset,
        {"where": f"uai IN ({_quoted(uais)})", "select": "uai,ips,rentree_scolaire", "order_by": "rentree_scolaire DESC"},
        500,
    )


async def education_headcounts(uais: list[str]) -> list[dict]:
    if not uais:
        return []
    return await ods_records(
        "education", EDUCATION_BASE, "fr-en-ecoles-effectifs-nb_classes",
        {
            "where": f"numero_ecole IN ({_quoted(uais)})",
            "select": "numero_ecole,rentree_scolaire,nombre_total_classes,nombre_total_eleves",
            "order_by": "rentree_scolaire DESC",
        },
        500,
    )


async def ign_navigation_route(from_: dict, to: dict, profile: str) -> dict:
    """Itinéraire IGN (`profile` : car | pedestrian) -> { durationS, distanceM }."""
    res = await http.get(
        "https://data.geopf.fr/navigation/itineraire",
        source="ign_navigation",
        params={
            "resource": "bdtopo-osrm",
            "start": f"{from_['lon']},{from_['lat']}",
            "end": f"{to['lon']},{to['lat']}",
            "profile": profile,
            "optimization": "fastest",
            "timeUnit": "second",
            "distanceUnit": "meter",
            "getSteps": "false",
            "geometryFormat": "geojson",
        },
    )
    return {"durationS": js_round(res["duration"]), "distanceM": js_round(res["distance"])}


# Sources à clé : non testées sans compte, implémentées d'après la documentation officielle.


async def fhir_organizations_count(postcode: str) -> int:
    """Nombre d'organisations de santé (Annuaire Santé FHIR) sur un code postal."""
    key = settings.esante_api_key
    if not key:
        raise MissingApiKeyError("esante_fhir", "ESANTE_API_KEY")
    res = await http.get(
        "https://gateway.api.esante.gouv.fr/fhir/v2/Organization",
        source="esante_fhir",
        headers={"ESANTE-API-KEY": key},
        params={"address-postalcode": postcode, "_summary": "count"},
    )
    total = res.get("total")
    return total if total is not None else 0


async def sirene_count(insee: str, naf: str) -> int:
    """Nombre d'établissements actifs d'un code NAF dans une commune (Sirene 3.11)."""
    key = settings.insee_sirene_api_key
    if not key:
        raise MissingApiKeyError("sirene", "INSEE_SIRENE_API_KEY")
    res = await http.get(
        "https://api.insee.fr/api-sirene/3.11/siret",
        source="sirene",
        headers={"X-INSEE-Api-Key-Integration": key},
        params={
            "q": f"codeCommuneEtablissement:{insee} AND periode(activitePrincipaleEtablissement:{naf} AND etatAdministratifEtablissement:A)",
            "nombre": 1,
        },
        allow_statuses=(404,),
    )
    header = res.get("header") if isinstance(res, dict) else None
    total = header.get("total") if isinstance(header, dict) else None
    return total if total is not None else 0
