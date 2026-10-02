# HomePedia

Plateforme d'analyse du logement et des territoires en France (projet Epitech), pensée pour un usage professionnel :
prix au m² par commune, fiche socio-économique d'une commune, rapport complet d'une adresse.

| Dossier | Rôle |
|---|---|
| `api/` | **Backend Python (FastAPI)** : collecte une cinquantaine de sources, normalise, agrège et stocke |
| `frontend/` | **Interface Streamlit** : tableau de bord, cartes, fiches commune et adresse, annonces, avis |
| `docs/` | Correspondance des données, schéma, architecture, routes |

Stockage : **MariaDB** pour le modèle normalisé (adresses, communes, ventes DVF, indicateurs), **MongoDB** pour ce qui n'a
pas de schéma stable (réponses brutes, annonces scrapées, contours GeoJSON, avis).

## Démarrage rapide

Prérequis : Python 3.12, Docker.

```bash
# 1. Bases de données (MariaDB 11.4 sur le port 3310, MongoDB 8.0 sur le port 27017)
docker compose up -d mariadb mongodb

# 2. API (http://localhost:8000/api — Swagger : http://localhost:8000/api/docs)
cd api
python -m venv .venv && .venv/Scripts/activate      # Linux / macOS : source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env                                 # clés API facultatives
uvicorn app.main:app --port 8000                     # les migrations SQL sont appliquées au démarrage

# 3. Interface (http://localhost:8501)
cd ../frontend
python -m venv .venv && .venv/Scripts/activate
pip install -r requirements.txt
streamlit run app.py
```

Tout en conteneurs :

```bash
cp api/.env.example api/.env
docker compose --profile full up -d --build
```

## Premier essai

Dans l'interface : **Tableau de bord → Charger le référentiel**, puis **Territoires** (choisir un département et le charger)
ou **Analyse d'adresse**. La même chose par l'API :

```bash
# Régions, départements et contours
curl -X POST http://localhost:8000/api/territories/collect

# Un département : communes, contours, ventes DVF de la dernière année, indices de prix communaux
curl -X POST http://localhost:8000/api/departments/80/communes/collect
curl -X POST http://localhost:8000/api/departments/80/contours/collect
curl -X POST http://localhost:8000/api/departments/80/dvf/collect
curl http://localhost:8000/api/departments/80/prices

# Une commune : recensement, emploi, revenus, DVF, énergie, puis sa fiche
curl -X POST http://localhost:8000/api/communes/80021/collect-all
curl http://localhost:8000/api/communes/80021/report

# Une adresse : géocodage + collecte des 11 modules (1 à 3 minutes la première fois), puis son rapport
curl -X POST http://localhost:8000/api/addresses/collect -H 'Content-Type: application/json' \
  -d '{"q": "2 rue de la République, Amiens"}'
curl http://localhost:8000/api/addresses/1/report
```

## Sources de données

| # | Source | Données | Module |
|---|---|---|---|
| 1 | API Géo | Régions, départements, communes | `territory`, `geo` |
| 2 | Contours GeoJSON (API Géo, france-geojson) | Communes, départements, régions | `territory` |
| 3 | INSEE Melodi – populations historiques | Population depuis 1968 | `socio` |
| 4 | INSEE Melodi – recensement population | Tranches d'âge | `socio` |
| 5 | INSEE Melodi – recensement emploi | Actifs, emploi, chômage | `socio` |
| 6 | INSEE Melodi – recensement logement | Logements vacants, résidences secondaires | `socio` |
| 7 | INSEE Melodi – Filosofi | Niveau de vie, pauvreté, Gini | `socio` |
| 8 | DVF géolocalisé (data.gouv) | Transactions, par commune ou par département | `building`, `territory` |
| 9 | Annuaire de l'éducation | Écoles, collèges, lycées, IPS | `services` |
| 10 | Agence ORE | Consommation d'électricité et de gaz par commune | `energy` |
| 11 | Géorisques (GASPAR) | Risques naturels et industriels, CatNat | `risk` |
| 12 | OpenStreetMap (Overpass) | Transports, santé, commerces, nuisances | `services`, `mobility`, `nuisance` |
| 13 | Google Maps Places API | Avis sur des lieux (clé payante) | `reviews` |
| 14 | MeilleursAgents | Avis de quartiers et d'agences (import de fichiers) | `reviews` |

S'y ajoutent les sources de l'analyse d'adresse (BAN, cadastre, PLU, RNB, BDNB, DPE, Hub'Eau, Open-Meteo, ARCEP,
Enedis, GRDF…) : le registre complet est dans `GET /api/sources` et dans [docs/01](docs/01-correspondance-donnees.md).
Aucune clé n'est obligatoire : une source à clé non configurée est marquée `skipped`, sans bloquer les autres.

## Traitement des données

Chaque module suit la même chaîne : **récupération** (`clients.py`), **normalisation** (`normalizers.py`, fonctions pures
testées), **stockage** et **consultation** (`service.py`). Les principaux traitements :

- **Indice de prix** : à partir des ventes DVF, on ne garde que les mutations d'un seul logement, on écarte les prix hors de
  200 à 30 000 €/m², puis on calcule médiane, quartiles et moyenne par commune, année et type de bien.
- **Indicateurs socio-économiques** : taux de chômage, d'activité et d'emploi, parts par tranche d'âge, vacance, âge moyen
  estimé, calculés à partir des observations brutes du recensement.
- **Énergie** : agrégation des consommations par secteur NAF en grands secteurs, par commune, année et énergie.
- **Annonces et avis** : dédoublonnage, prix au m², historique des changements de prix.
- **Géographie** : distances, rayons, appartenance à une zone (PLU, périmètres de monuments), carte en classes.
- **Fraîcheur** : chaque collecte est journalisée avec une durée de validité ; une source encore valide n'est pas rappelée.

## Annonces et avis

Le service de scraping (à venir) pousse ses annonces par lots ; une annonce est identifiée par `(source, sourceId)`.

```bash
curl -X POST http://localhost:8000/api/listings/ingest -H 'Content-Type: application/json' -H 'X-Ingest-Token: <INGEST_TOKEN>' \
  -d '{"source": "bienici", "items": [{"sourceId": "42", "url": "https://www.bienici.com/annonce/42",
       "transactionType": "sale", "propertyType": "apartment", "priceEur": 189000, "areaM2": 64, "inseeCode": "80021"}]}'
```

Les avis MeilleursAgents s'importent depuis la page **Avis** de l'interface (fichier CSV, association des colonnes) ou par
`POST /api/reviews/import`. Les avis Google se collectent autour d'une adresse analysée (`GOOGLE_MAPS_API_KEY`).

## Commandes

| Commande (dans `api/`) | Effet |
|---|---|
| `uvicorn app.main:app --reload --port 8000` | API en développement |
| `python -m pytest` | Tests unitaires (normaliseurs, géométrie, SQL) |

## Variables d'environnement

Voir [`api/.env.example`](api/.env.example). L'interface lit `HOMEPEDIA_API_URL` (défaut `http://localhost:8000/api`) et
`INGEST_TOKEN` (pour les imports d'avis si l'API en exige un). Overpass refuse un User-Agent contenant un contact factice.

## Documentation

| Document | Contenu |
|---|---|
| [01 – Correspondance des données](docs/01-correspondance-donnees.md) | Donnée métier -> source(s) -> table(s) |
| [02 – Schéma des bases](docs/02-schema-base-de-donnees.md) | Tables MariaDB, collections MongoDB, index |
| [03 – Architecture](docs/03-architecture-backend.md) | Arborescence, cycle de collecte, résilience, interface |
| [04 – Routes de l'API](docs/04-routes-api.md) | Chaque route avec une requête et une réponse réelles |

## Reste à faire (exigences du sujet)

- Service de scraping alimentant `POST /api/listings/ingest` (SeLoger, Bien'ici, Leboncoin).
- Analyse des avis par IA (sentiment, extraction de mentions).
- Traitements lourds sur cluster Spark (indice de prix national, horaires GTFS).
