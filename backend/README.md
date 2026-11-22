# HomePedia — Backend

API Python (FastAPI) connectée à **PostgreSQL** et **MongoDB**, organisée comme une application Nest.js :
des **modules**, chacun avec un **controller** (routes HTTP) qui appelle un **service** (logique métier et accès
aux bases). Chaque base a son propre schéma : [`schema/postgres.sql`](schema/postgres.sql) et
[`schema/mongo.json`](schema/mongo.json).

## Démarrage (Docker)

```bash
cd backend
cp .env.example .env
docker compose up -d --build
```

| Service    | URL / port                                                 |
|------------|------------------------------------------------------------|
| API        | http://localhost:8000 — Swagger : http://localhost:8000/docs |
| PostgreSQL | `localhost:${POSTGRES_HOST_PORT}` (5434 dans `.env.example`) |
| MongoDB    | `localhost:27017`                                          |

Puis : `curl localhost:8000/geodata/regions`.

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
    ├── geodata/
    │   ├── controller.py    # routes /geodata         (≈ geodata.controller.ts)
    │   ├── service.py       # logique, bases, API Géo (≈ geodata.service.ts)
    │   └── dto.py           # modèles d'entrée/sortie (≈ dto/*.ts)
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

Source : [contours administratifs Etalab 2024](https://etalab-datasets.geo.data.gouv.fr/contours-administratifs/2024/geojson/)
(fichiers `regions-`, `departements-` et `communes-1000m.geojson`).

| Méthode | Route                                | Description                         |
|---------|--------------------------------------|-------------------------------------|
| GET     | `/geodata/regions`                   | toutes les régions                  |
| GET     | `/geodata/regions/{code}/departments`| départements d'une région           |
| GET     | `/geodata/departments/{code}/communes`| communes d'un département          |

Au premier appel, chaque jeu de données manquant est téléchargé et enregistré en entier (les communes : ~10 Mo,
quelques secondes) ; ensuite tout est lu en base. Les réponses viennent de MongoDB.

| Table / collection | PostgreSQL                       | MongoDB                                        |
|--------------------|----------------------------------|------------------------------------------------|
| `regions`          | `code`, `name`                   | `code`, `name`, `coordinates`                  |
| `departments`      | `code`, `name`, `region_code` → `regions` | `code`, `name`, `region_code`, `coordinates` |
| `communes`         | `code`, `name`, `department_code` → `departments` | `code`, `name`, `department_code`, `coordinates` |

`coordinates` est toujours au format MultiPolygon GeoJSON : polygones > anneaux > `[longitude, latitude]`.

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
