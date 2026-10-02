# HomePedia : architecture

## 1. Arborescence

```text
HomePedia/
├── docker-compose.yml                 MariaDB 11.4, MongoDB 8.0 (+ API et interface avec le profil « full »)
├── docs/
├── api/                               backend Python 3.12 (FastAPI, asynchrone)
│   ├── Dockerfile · requirements.txt · pyproject.toml · .env.example
│   ├── tests/                         pytest : normaliseurs, géométrie, découpage SQL
│   └── app/
│       ├── main.py                    application, préfixe /api, format d'erreur, Swagger (/api/docs)
│       ├── config.py                  lecture typée du .env
│       ├── db.py                      accès MariaDB (SQLAlchemy Core asynchrone, lignes en dicts camelCase)
│       ├── migrate.py · sql/          migrations SQL appliquées au démarrage (00X_*.sql)
│       ├── mongo.py                   MongoDB : raw_payloads, listings, contours, reviews
│       ├── http_client.py             client HTTP commun : timeout, retries, backoff, débit par source
│       ├── open_data.py               clients génériques : API tabulaire data.gouv, Opendatasoft, data-fair, Overpass, WFS
│       ├── collector.py               cache par source × cible, journal des collectes, archivage des réponses brutes
│       ├── geo_utils.py · parse.py    calculs géométriques, normalisation des valeurs
│       ├── schemas.py · errors.py · sources.py
│       └── modules/
│           ├── geo/           BAN, API Géo, cadastre, PLU/GPU, servitudes, monuments historiques
│           ├── building/      RNB, BDNB, DPE, DVF, indice de prix, copropriétés (RNIC)
│           ├── risk/          Géorisques, débroussaillement (WFS), risques biologiques
│           ├── water/         Hub'Eau (eau potable, nappes), VigiEau
│           ├── climate/       Open-Meteo (historique, projections), PVGIS, Atmo
│           ├── nuisance/      Overpass, PEB (WFS), OpenSky
│           ├── energy/        France Chaleur Urbaine, GRDF, Enedis, Agence ORE (commune)
│           ├── services/      Recherche d'entreprises, OSM, Éducation, IGN itinéraire, FHIR, Sirene
│           ├── socio/         INSEE Melodi (recensement, emploi, Filosofi, historique), fiscalité locale, SSMSI
│           ├── mobility/      IRVE, stationnement, arrêts, cyclable, transport.data.gouv
│           ├── connectivity/  ARCEP fixe et mobile
│           ├── collection/    orchestration des 11 modules pour une adresse + rapport consolidé
│           ├── territory/     régions, départements, contours, DVF par département, fiche commune
│           ├── listings/      annonces scrapées (MongoDB) : ingestion par lots, recherche, proximité, statistiques
│           └── reviews/       avis (MongoDB) : Google Maps Places, import MeilleursAgents
└── frontend/                          interface Streamlit
    ├── app.py                         navigation
    ├── lib/                           client de l'API, mise en forme, graphiques
    └── views/                         tableau de bord, territoires, fiche commune, analyse d'adresse, annonces, avis, sources
```

Chaque module de domaine suit le même découpage :

| Fichier | Rôle |
|---|---|
| `clients.py` | **Récupération** : appels bruts aux API externes, aucune transformation |
| `normalizers.py` | **Traitement** : fonctions pures réponse brute -> lignes de la base (testées unitairement) |
| `service.py` | **Stockage** (`collect`) et **consultation** (`read`) |
| `router.py` | Routes REST : `POST …/collect` (déclenchement) et `GET` (consultation) |

Il n'y a pas de classes d'entités : les lignes sont des dicts aux clés camelCase, et `db` déduit du schéma la conversion
des noms (`insee_code` <-> `inseeCode`) et des types (DECIMAL, booléens, colonnes JSON, géométries en WKT / GeoJSON).

## 2. Cycle d'une collecte

```text
POST /api/addresses/12/water/collect
  └─ water.service.collect(address)
       └─ collector.run("hubeau_eau_potable", "commune:80021", task, force=...)
            ├─ fetch_log : collecte réussie non expirée ? -> { status: "cached" }, sans appel externe
            ├─ clients.drinking_water()             récupération (http : limite de débit, retries)
            ├─ normalize_water()                    normalisation
            ├─ db.upsert()                          stockage idempotent
            ├─ fetch_log (+ raw_payloads, MongoDB)  traçabilité
            └─ { source, target, status, items, fetchedAt, expiresAt }
```

Une source en erreur renvoie `status: "error"` (message conservé dans `fetch_log.error_message`) sans interrompre les
autres. Une source à clé non configurée renvoie `status: "skipped"`.

## 3. Résilience des appels externes

| Mécanisme | Détail |
|---|---|
| Timeout | `HTTP_TIMEOUT_MS` (20 s par défaut), relevé par source quand nécessaire (DVF, ARCEP, Overpass) |
| Retries | `HTTP_MAX_RETRIES` (3) sur erreur réseau, 408, 425, 429, 500, 502, 503, 504 |
| Backoff | Exponentiel + jitter ; `Retry-After` respecté ; sur 429 sans en-tête, attente de la fenêtre suivante |
| Débit | Par source : concurrence max + intervalle minimal entre deux départs (`http_client.RATE_LIMITS`) |
| Repli | Overpass : serveur principal puis miroir `overpass.kumi.systems` |
| Erreurs | `ExternalApiError` (source, statut amont, message) et `MissingApiKeyError`, format JSON uniforme |

## 4. Orchestration

`POST /api/addresses/:id/collect` exécute le module `geo`, puis `building` (qui renseigne le bâtiment RNB utilisé par
d'autres modules), puis les 9 autres en parallèle (`asyncio.gather`). Une première collecte complète prend 1 à 3 minutes,
l'essentiel étant l'attente due au débit limité d'Overpass ; une seconde répond depuis le cache en moins d'une seconde.
`GET /api/addresses/:id/report` assemble la lecture de tous les modules, sans aucun appel externe.

À la maille commune, `POST /api/communes/:insee/collect-all` lance en parallèle le contour, le recensement (population,
âge, emploi, revenus, logement), les ventes DVF et l'énergie ; `GET /api/communes/:insee/report` en fait la fiche.
À la maille département, `POST /api/departments/:dep/dvf/collect` importe le fichier DVF du département et recalcule
l'indice de prix de chaque commune ; `GET /api/departments/:dep/prices` alimente la carte.

## 5. MongoDB

MariaDB garde le modèle normalisé ; MongoDB reçoit ce qui n'a pas de schéma stable.

| Collection | Contenu | Clé / index |
|---|---|---|
| `raw_payloads` | JSON brut d'une collecte (≤ 4 Mo), rattaché à `fetch_log.id`. Désactivable via `STORE_RAW_PAYLOADS`. | `(sourceCode, targetKey, createdAt)` |
| `listings` | Annonces poussées par le scraping, avec l'objet d'origine dans `raw` et l'historique de prix. | unique `(source, sourceId)`, `2dsphere` sur `location` |
| `contours` | Contours GeoJSON des régions, départements et communes. | unique `(level, code)`, `(level, parentCode)` |
| `reviews` | Avis Google Maps et MeilleursAgents (texte, note, lieu ou quartier). | unique `(source, externalId)`, `(inseeCode, source, kind)` |

```text
Scraper ── POST /api/listings/ingest (X-Ingest-Token, 500 annonces max)
  └─ listings.service.ingest(source, items)
       ├─ validation (pydantic)              un élément invalide rejette le lot (400)
       ├─ normalize_listing()                prix au m², département, point GeoJSON, clés absentes omises
       ├─ bulk_write(upsert)                 idempotent sur (source, sourceId)
       │    ├─ firstSeenAt à la création, lastSeenAt à chaque passage
       │    └─ priceHistory complété si le prix a changé
       └─ { source, received, created, updated, priceChanges, ingestedAt }
```

## 6. Interface Streamlit

L'interface ne lit que l'API (`HOMEPEDIA_API_URL`) ; les lectures sont mises en cache deux minutes, toute collecte vide
le cache. Les pages acceptent un lien direct : `/territory?dep=80`, `/commune?insee=80021`, `/address?id=1`.

| Page | Contenu |
|---|---|
| Tableau de bord | Volumes stockés, référentiel, collectes du jour, sources par domaine |
| Territoires | Carte en classes du prix médian au m² par commune d'un département, classement des communes |
| Fiche commune | Démographie, emploi et revenus, logement, marché, énergie, fiscalité et sécurité, risques, avis |
| Analyse d'adresse | Carte, bâtiment et DPE, urbanisme, risques, eau et climat, nuisances, réseaux, services, mobilité, marché |
| Annonces · Avis | Recherche filtrée ; import de fichiers MeilleursAgents, collecte Google |
| Sources et collectes | Registre des sources, journal des collectes |
