# HomePedia — Backend

API Python (FastAPI) connectée à **PostgreSQL** et **MongoDB**, organisée comme une application Nest.js :
des **modules**, chacun avec un **controller** (routes HTTP) qui appelle un **service** (logique métier et accès
aux bases). Chaque base a son propre schéma : [`schema/postgres.sql`](schema/postgres.sql) et
[`schema/mongo.json`](schema/mongo.json). Le frontend est décrit dans [`../frontend/README.md`](../frontend/README.md).

## Démarrage (Docker)

```bash
cd backend
cp .env.example .env          # puis renseigner SCRAPE_UNBLOCKER_KEY (module Annonces)
docker compose up -d --build
```

| Service    | URL / port                                                 |
|------------|------------------------------------------------------------|
| API        | http://127.0.0.1:8000 — Swagger : http://127.0.0.1:8000/docs |
| PostgreSQL | `localhost:${POSTGRES_HOST_PORT}` (5434 dans `.env.example`) |
| MongoDB    | `localhost:27017`                                          |

Puis : `curl 127.0.0.1:8000/geodata/regions`.

> **Windows + WSL** : si `localhost:8000` ne répond pas (requêtes bloquées), un processus WSL (`wslrelay`) occupe
> sans doute `[::1]:8000`. Utiliser `127.0.0.1:8000`, ce que fait déjà le proxy du frontend.

## Services externes

| Service | Rôle | Accès |
|---------|------|-------|
| [Etalab — contours administratifs 2024](https://etalab-datasets.geo.data.gouv.fr/contours-administratifs/2024/geojson/) | contours des régions, départements, communes | gratuit, sans clé |
| [Géocodeur de la Géoplateforme IGN](https://data.geopf.fr/geocodage) | recherche d'adresses ; coordonnées des annonces | gratuit, sans clé (50 requêtes/s) |
| [ScrapeUnblocker](https://scrapeunblocker.com) | téléchargement des pages SeLoger | **payant** : clé dans `.env`, un crédit par page |

Aucun autre service n'est appelé. Les identifiants de lieu SeLoger sont calculés dans le code (départements) ou
fournis par l'appelant : aucun service tiers de résolution n'est utilisé (voir « Limites » du module Annonces).

## Architecture

```
app/
├── main.py                  # bootstrap : connexions, schéma, erreurs, modules
├── app_module.py            # module racine : liste des modules (≈ AppModule)
├── core/                    # partagé par tous les modules
│   ├── config.py            # variables d'environnement
│   ├── controller.py        # @controller / @get / @post : controllers en classe
│   ├── database.py          # PostgreSQL / MongoDB + providers injectables (PgEngine, MongoDb)
│   ├── exceptions.py        # erreurs de base / de source externe -> réponses HTTP
│   └── schema.py            # application des schémas PostgreSQL et MongoDB au démarrage
└── modules/
    ├── annonces/            # annonces immobilières : scraping, géocodage, carte (voir « Module Annonces »)
    └── geodata/
        ├── controller.py    # routes /geodata              (≈ geodata.controller.ts)
        ├── service.py       # Etalab, géocodeur IGN, bases (≈ geodata.service.ts)
        └── dto.py           # modèles d'entrée/sortie      (≈ dto/*.ts)
```

Correspondance avec Nest.js :

| Nest.js                                   | Ici                                                      |
|-------------------------------------------|----------------------------------------------------------|
| `@Controller('geodata') class GeoDataController` | `@controller("/geodata") class GeoDataController`     |
| `@Get('regions')`                         | `@get("/regions")`                                       |
| `constructor(private service: GeoDataService)` | attribut `service: GeoDataServiceDep`               |
| `@Injectable() class GeoDataService`      | `class GeoDataService` + `GeoDataServiceDep`             |
| injection par le constructeur             | `__init__(self, pg: PgEngine, mongo: MongoDb, ...)` résolu par `Depends` |
| DTO + `class-validator`                   | modèles Pydantic dans `dto.py`                           |
| `AppModule.imports`                       | `MODULES` dans `app_module.py`                           |

### Ajouter un module

1. Créer `app/modules/<nom>/` avec `controller.py`, `service.py`, `dto.py` et un `__init__.py` qui exporte
   `router = <Nom>Controller.router`.
2. Le service reçoit ce dont il a besoin dans son constructeur (`PgEngine`, `MongoDb`, autres services…) et expose
   `<Nom>ServiceDep = Annotated[<Nom>Service, Depends(<Nom>Service)]`.
3. Le controller est une classe décorée par `@controller("/<nom>")`, qui déclare `service: <Nom>ServiceDep` comme
   attribut et ses routes comme méthodes (`@get`, `@post`…) utilisant `self.service`.
4. Ajouter le module à `MODULES` dans `app_module.py`, ses tables dans `schema/postgres.sql` et ses collections dans
   `schema/mongo.json`.

## Module GeoData

| Méthode | Route                                 | Description                                              |
|---------|---------------------------------------|----------------------------------------------------------|
| GET     | `/geodata/regions`                    | toutes les régions                                       |
| GET     | `/geodata/regions/{code}/departments` | départements d'une région                                |
| GET     | `/geodata/departments/{code}/communes`| communes d'un département                                |
| GET     | `/geodata/search?q=…`                 | régions, départements, communes (nom ou code), puis adresses (géocodeur IGN) |

Au premier appel, chaque jeu de données Etalab manquant est téléchargé et enregistré en entier (les communes :
~10 Mo, quelques secondes) ; ensuite tout est lu en base. Les réponses viennent de MongoDB.

| Table / collection | PostgreSQL                       | MongoDB                                        |
|--------------------|----------------------------------|------------------------------------------------|
| `regions`          | `code`, `name`                   | `code`, `name`, `coordinates`                  |
| `departments`      | `code`, `name`, `region_code` → `regions` | `code`, `name`, `region_code`, `coordinates` |
| `communes`         | `code`, `name`, `department_code` → `departments` | `code`, `name`, `department_code`, `coordinates` |

`coordinates` est toujours au format MultiPolygon GeoJSON : polygones > anneaux > `[longitude, latitude]`.

## Module Annonces

Récupère des annonces immobilières (SeLoger pour l'instant), les normalise, géocode leurs adresses, les enregistre
dans PostgreSQL et les sert à la carte du frontend. Les pages sont téléchargées via ScrapeUnblocker : renseigner
`SCRAPE_UNBLOCKER_HEADER` et `SCRAPE_UNBLOCKER_KEY` dans `.env`. **Chaque page coûte un crédit.**

| Méthode | Route               | Description |
|---------|---------------------|-------------|
| GET     | `/annonces/map`     | annonces pour la carte : d'une commune (`commune_code`), sinon d'une emprise (`west`, `south`, `east`, `north`). Réponse immédiate avec les annonces en base ; si le département concerné (celui de la commune, sinon `department_code`) n'en a encore aucune, il est scrapé en tâche de fond (`sync.status = pending` : redemander quelques secondes plus tard). Filtres `transaction_type`, `property_type`, `limit` |
| GET     | `/annonces`         | annonces enregistrées, filtres `source`, `transaction_type`, `property_type`, `postal_code`, `insee_code`, `min_price`, `max_price`, `limit`, `offset` |
| GET     | `/annonces/{id}/details` | fiche complète d'une annonce (description, caractéristiques, énergie, coûts, écoles, photos) : lue dans MongoDB, sinon sur la page de l'annonce (1 crédit) puis enregistrée ; `refresh=true` force une nouvelle lecture |
| POST    | `/annonces/scrape`  | scraping manuel d'une recherche (`dry_run: true` : URLs générées seulement, gratuit) |

```json
POST /annonces/scrape
{
  "source": "seloger",
  "transaction": "location",                       // location | vente
  "property_types": ["appartement", "maison"],
  "zone": { "level": "departement", "code": "69" }, // ou { "level": "commune", "place_id": "AD08FR28808" }
  "sort": "recentes",                              // recentes | tendance
  "pages": 1                                       // 1 à 20
}
```

### Parcours d'une annonce (`GET /annonces/map`)

1. **Base d'abord** — pour le département concerné et chaque site : s'il a déjà des annonces en base, rien n'est
   téléchargé (`sync.status = database`). S'il a été interrogé récemment sans résultat (24 h) ou en erreur
   (10 min), non plus (`recently_scraped`). Sinon, le site est interrogé **en tâche de fond** (étapes 2 à 6) et la
   réponse part tout de suite avec les annonces déjà en base (`pending`). Tant que la tâche tourne, les demandes
   suivantes répondent `pending` ; la première demande après sa fin reçoit `scraped` et le nombre d'annonces
   (ou `error`), puis `database`. Un seul scraping à la fois par site, département et transaction.
2. **URL** — `sources/seloger/url_builder.py` traduit les critères : `Rent`/`Buy`, `Apartment,House`, identifiant
   de lieu SeLoger du département (Rhône 69 → `AD06FR70`), tri par date.
3. **Téléchargement** — `client.py` envoie l'URL à ScrapeUnblocker, qui renvoie le HTML. **3 pages** (≈ 90
   annonces, 3 crédits ; constante `AUTO_SCRAPE_PAGES` de `service.py`) : la page 1 donne le nombre de résultats,
   les pages utiles suivantes sont téléchargées en parallèle ; une page en échec n'annule pas les autres.
4. **Lecture** — `sources/seloger/parser.py` lit l'état JSON embarqué dans la page (`__UFRN_FETCHER__`), à défaut
   les cartes HTML. Seules les caractéristiques du bien sont lues, rien sur l'annonceur.
5. **Normalisation** — `normalizer.py` : « 1 940 € » → 1940, « 2ème étage » → 2, « RDC » → 0, `RENT` → `location` ;
   numéro et rue cherchés dans le titre et la description.
6. **Géocodage et enregistrement** — `geocoding.py` n'envoie au géocodeur IGN que les adresses absentes de
   `geocodage` ; `repository.py` insère ou met à jour les annonces ; la tentative est notée dans `scrapes`.
7. **Réponse** — annonces géocodées de la commune (arrondissements de Paris, Lyon, Marseille compris) ou de
   l'emprise, filtrées, avec le nom affichable du site (`source_label`), leur photo et le résumé `sync` de
   l'étape 1. La réponse ne dépend jamais du site : quelques centièmes de seconde.

Premier passage sur un département : 3 crédits, et les annonces arrivent de quelques secondes à une minute plus
tard (le frontend redemande la zone toutes les 4 s tant que `sync.status = pending`). Ensuite : lecture en base.

### Tables

| Table       | Contenu |
|-------------|---------|
| `annonces`  | une ligne par annonce, unique sur `(source, source_id)` : un nouveau scraping la met à jour (`last_seen_at`). `image_url` : photo principale (1re de la galerie des résultats, sinon 1re photo de la fiche MongoDB) |
| `geocodage` | un résultat du géocodeur par adresse normalisée (`address_key`) ; une adresse introuvable est gardée sans coordonnées pour ne pas être redemandée |
| `annonce_details` (MongoDB) | fiche complète lue sur la page de l'annonce, unique sur `(source, source_id)` : texte, caractéristiques, DPE/GES, coûts, prix au m² du secteur, coordonnées précises, écoles, URL des photos et visites virtuelles. Rien sur l'annonceur hormis son type (agence, particulier) |
| `scrapes`   | journal des scrapings (zone, statut, nombre d'annonces, erreur) : évite de repayer une zone vide ou en erreur |

### Organisation

```
modules/annonces/
├── controller.py, service.py, dto.py   # routes et orchestration
├── models.py          # modèle commun : SearchCriteria, RawListing (brut), Listing (normalisé)
├── client.py          # client HTTP ScrapeUnblocker
├── normalizer.py      # libellés → valeurs (« 1 940 € », « 2ème étage », adresse dans le texte…)
├── geocoding.py       # géocodeur IGN, avec la table geocodage comme cache
├── detail_repository.py # fiches complètes (MongoDB annonce_details)
├── repository.py      # annonces (upsert, recherche), journal des scrapings
└── sources/
    ├── base.py        # interface ScraperSource
    ├── __init__.py    # registre des sites
    └── seloger/       # url_builder.py, parser.py (résultats), detail_parser.py (page d'une annonce)
```

**Ajouter un site** : créer `sources/<site>/` avec une classe `ScraperSource` (`name`, `label`,
`build_search_url`, `parse` → `RawListing`, et en option `parse_detail` → `ListingDetail`), puis l'ajouter à `SOURCES` dans `sources/__init__.py`. Le
téléchargement, la normalisation, le géocodage, l'enregistrement et la carte sont communs.

### Limites

- **Identifiants de lieu SeLoger** : SeLoger n'utilise pas les codes INSEE (`AD04…` région, `AD06…` département,
  `AD08…` commune). Seuls les départements métropolitains se calculent (rang du code, Corse 2A/2B comprise :
  69 → `AD06FR70`, 75 → `AD06FR76`). Communes et régions : `place_id` à fournir, visible dans le paramètre
  `locations=` d'une recherche faite sur seloger.com. Les départements d'outre-mer ne sont pas gérés.
- **Pas de scraping par commune** depuis la carte : une petite commune n'a d'annonces que si elle figure parmi les
  ~90 plus récentes de son département. Des services tiers payants proposent une autocomplétion vers ces
  identifiants (par exemple un acteur Apify) ; aucun n'est utilisé.
- **Pas de rafraîchissement** : un département qui a déjà des annonces n'est plus réinterrogé automatiquement.
- **Scrapings en cours gardés en mémoire** : si l'API redémarre pendant un scraping de fond, il est perdu ; le
  département sera simplement réinterrogé à la visite suivante (rien n'est noté dans `scrapes`).
- **Tri « récentes »** : valeur `order=DateDesc` supposée, non confirmée par SeLoger (`ORDERS` dans
  `url_builder.py`).
- **Adresse** : SeLoger donne le code postal et la ville ; la rue n'est trouvée qu'environ une fois sur deux. Sans
  rue, l'annonce est géocodée au centre de la commune ou de l'arrondissement.
- **Conditions d'utilisation** : celles de SeLoger encadrent probablement le scraping ; à vérifier selon l'usage.

## Les schémas

Appliqués à chaque démarrage de l'API, qui refuse de démarrer si l'un d'eux est invalide. Le dossier `schema/` est
monté dans le conteneur : après modification, `docker compose restart api` suffit, sans rebuild.

- **[`schema/postgres.sql`](schema/postgres.sql)** : exécuté tel quel, dans une transaction. Utilisez
  `CREATE TABLE IF NOT EXISTS` ; pour modifier une table existante, ajoutez un `ALTER TABLE`.
- **[`schema/mongo.json`](schema/mongo.json)** : une entrée par collection, avec
  - `validator` : règles `$jsonSchema` (champs obligatoires, types, longueurs…), mises à jour à chaque démarrage ;
  - `indexes` : `{"name", "keys", "unique"…}`, alignés sur le fichier (ajoutés, modifiés ou supprimés).

  Les documents déjà présents ne sont pas revalidés quand le validateur change.

## Développement sans Docker pour l'API

```bash
python -m venv .venv && .venv/Scripts/activate      # Windows ; sinon source .venv/bin/activate
pip install -r requirements.txt
docker compose up -d postgres mongo
# dans .env : POSTGRES_PORT=5434 (= POSTGRES_HOST_PORT)
uvicorn app.main:app --reload
```
