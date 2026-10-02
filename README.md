# HomePedia

Plateforme d'analyse du logement en France (projet Epitech). Ce dépôt contient pour l'instant le **backend de collecte** : une API NestJS qui interroge une quarantaine de sources publiques, normalise leurs réponses et les stocke dans MariaDB autour d'une entité pivot, l'adresse géolocalisée.

## Démarrage rapide

Prérequis : Node.js 22, Docker.

```bash
# 1. Base de données (MariaDB 11.4 exposée sur le port 3310)
docker compose up -d mariadb

# 2. Backend
cd backend
cp .env.example .env          # renseigner les clés API facultatives si disponibles
npm install
npm run migration:run         # crée les 44 tables et le registre des sources
npm run start:dev             # http://localhost:3000/api — Swagger : http://localhost:3000/api/docs
```

Tout en conteneurs (API comprise) :

```bash
cp backend/.env.example backend/.env
docker compose --profile full up -d --build
```

Les migrations sont aussi appliquées automatiquement au démarrage de l'API.

> Le port hôte de MariaDB est **3310** pour ne pas entrer en conflit avec un MySQL local (3306/3307).
> Il se change avec `DB_HOST_PORT` (docker-compose) et `DB_PORT` (`backend/.env`).

## Premier essai

```bash
# Géocode l'adresse et lance la collecte complète (11 modules, ~70 s la première fois)
curl -X POST http://localhost:3000/api/addresses/collect \
  -H 'Content-Type: application/json' \
  -d '{"q": "2 rue de la République, Amiens"}'

# Rapport consolidé (lecture seule, depuis la base)
curl http://localhost:3000/api/addresses/1/report
```

## Commandes

| Commande | Effet |
|---|---|
| `npm run start:dev` | API en mode watch |
| `npm run build` puis `npm run start:prod` | Build et exécution compilée |
| `npm run migration:run` / `migration:revert` / `migration:show` | Gestion des migrations |
| `npm test` | Tests unitaires (normaliseurs, géométrie, SQL) |
| `npm run typecheck` | Vérification TypeScript |

## Variables d'environnement

Voir [`backend/.env.example`](backend/.env.example). Aucune clé n'est obligatoire : les sources à clé (Atmo, Sirene, Annuaire Santé) sont marquées `skipped` dans le journal des collectes tant qu'elles ne sont pas configurées. Overpass refuse un User-Agent contenant un contact factice (`example.com`).

## Documentation

| Document | Contenu |
|---|---|
| [01 – Correspondance des données](docs/01-correspondance-donnees.md) | Donnée métier -> source(s) -> table(s), vérification des endpoints, données non couvertes |
| [02 – Schéma MariaDB](docs/02-schema-base-de-donnees.md) | Entités, relations, index spatiaux, fraîcheur, choix de TypeORM |
| [03 – Architecture du backend](docs/03-architecture-backend.md) | Arborescence, cycle de collecte, résilience |
| [04 – Routes de l'API](docs/04-routes-api.md) | Chaque route avec une requête et une réponse réelles |

## Reste à faire (exigences du sujet)

- Base non relationnelle (MongoDB) pour les réponses brutes et les données textuelles.
- Source textuelle analysée par IA (sentiment, extraction de mentions).
- Traitements lourds sur cluster Spark (indice de prix national, horaires GTFS).
- Application de visualisation (tableaux, cartes) branchée sur cette API.
