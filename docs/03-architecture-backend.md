# HomePedia : architecture du backend NestJS

## 1. Arborescence

```text
HomePedia/
├── docker-compose.yml                 MariaDB 11.4 (+ API avec le profil « full »)
├── docs/
│   ├── 01-correspondance-donnees.md   donnée métier -> source -> table
│   ├── 02-schema-base-de-donnees.md   schéma, index, choix de l'ORM
│   ├── 03-architecture-backend.md     ce document
│   └── 04-routes-api.md               routes avec exemples réels
└── backend/
    ├── Dockerfile
    ├── .env.example
    ├── package.json · tsconfig.json · nest-cli.json
    └── src/
        ├── main.ts                    préfixe /api, validation, filtre d'erreurs, Swagger (/api/docs)
        ├── app.module.ts
        ├── config/configuration.ts    lecture typée du .env
        ├── database/
        │   ├── sql/001_initial_schema.sql        schéma de référence (44 tables + registre des sources)
        │   ├── migrations/…-InitialSchema.ts     exécute le fichier SQL
        │   ├── sql-runner.ts                     découpage SQL sûr (chaînes, commentaires)
        │   ├── typeorm-options.ts · data-source.ts (CLI)
        ├── common/
        │   ├── http/          client HTTP commun : timeout, retries, backoff, rate limiting par source
        │   ├── clients/       clients génériques : API tabulaire data.gouv, Opendatasoft, data-fair, Overpass, WFS
        │   ├── geo/           calculs géométriques, requêtes spatiales (rayon, intersection)
        │   ├── entities/      colonnes de traçabilité communes (source, fetched_at, expires_at), transformers
        │   ├── dto/ · filters/ · utils/
        ├── sources/           registre des sources, journal des collectes, cache, réponses brutes
        └── modules/
            ├── geo/           BAN, API Géo, cadastre, PLU/GPU, servitudes, monuments historiques
            ├── building/      RNB, BDNB, DPE, DVF, indice de prix, copropriétés (RNIC)
            ├── risk/          Géorisques, débroussaillement (WFS), risques biologiques
            ├── water/         Hub'Eau (eau potable, nappes), VigiEau
            ├── climate/       Open-Meteo (historique, projections), PVGIS, Atmo
            ├── nuisance/      Overpass, PEB (WFS), OpenSky
            ├── energy/        France Chaleur Urbaine, GRDF, Enedis
            ├── services/      Recherche d'entreprises, OSM, Éducation, IGN itinéraire, FHIR, Sirene
            ├── socio/         INSEE Melodi, fiscalité locale, SSMSI
            ├── mobility/      IRVE, stationnement, arrêts, cyclable, transport.data.gouv
            ├── connectivity/  ARCEP fixe et mobile
            └── collection/    orchestration multi-modules + rapport consolidé
```

Chaque module de domaine suit le même découpage :

| Fichier | Rôle |
|---|---|
| `*.clients.ts` | **Récupération** : appels bruts aux API externes, aucune transformation |
| `*.normalizers.ts` | **Traitement** : fonctions pures réponse brute -> lignes de la base (testées unitairement) |
| `*.entities.ts` | Entités TypeORM, alignées sur le SQL |
| `*.service.ts` | **Stockage** (`collect`) et **consultation** (`read`) |
| `*.controller.ts` | Routes REST : `POST …/collect` (déclenchement) et `GET` (consultation) |

## 2. Cycle d'une collecte

```text
POST /api/addresses/12/water/collect
  └─ WaterService.collect(address)
       └─ CollectorService.run('hubeau_eau_potable', 'commune:80021', { force })
            ├─ fetch_log : collecte réussie non expirée ? -> { status: 'cached' }, sans appel externe
            ├─ HubeauClient.drinkingWater()        récupération (HttpClientService : limite de débit, retries)
            ├─ normalizeWater()                     normalisation
            ├─ repository.upsert()                  stockage idempotent
            ├─ fetch_log (+ raw_payload)            traçabilité
            └─ { source, target, status, items, fetchedAt, expiresAt }
```

Une source en erreur renvoie `status: 'error'` (message conservé dans `fetch_log.error_message`) sans interrompre les autres. Une source à clé non configurée renvoie `status: 'skipped'`.

## 3. Résilience des appels externes

| Mécanisme | Détail |
|---|---|
| Timeout | `HTTP_TIMEOUT_MS` (20 s par défaut), relevé par source quand nécessaire (DVF, ARCEP, Overpass) |
| Retries | `HTTP_MAX_RETRIES` (3) sur erreur réseau, 408, 425, 429, 500, 502, 503, 504 |
| Backoff | Exponentiel + jitter ; `Retry-After` respecté ; sur 429 sans en-tête, attente de la fenêtre suivante (20 s, 40 s, 60 s) |
| Débit | File FIFO par source : concurrence max + intervalle minimal (`common/http/rate-limits.ts`) |
| Repli | Overpass : serveur principal puis miroir `overpass.kumi.systems` |
| Erreurs | `ExternalApiError` (source, statut amont, message) et `MissingApiKeyError`, format JSON uniforme |

## 4. Orchestration

`POST /api/addresses/:id/collect` exécute le module `geo`, puis `building` (qui renseigne le bâtiment RNB utilisé par d'autres modules), puis les 9 autres en parallèle. Sur l'adresse de test, une première collecte complète prend environ 70 s, dont environ 60 s d'attente due au débit limité d'Overpass. Une seconde collecte complète répond depuis le cache en environ 0,2 s.

`GET /api/addresses/:id/report` assemble la lecture de tous les modules, sans aucun appel externe.
