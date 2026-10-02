# HomePedia : routes de l’API

> Généré à partir d’appels réels sur l’API locale (adresse de test : 2 rue de la République, Amiens).
> Préfixe commun : `/api`. Documentation interactive Swagger : `http://localhost:3000/api/docs`.
> Les tableaux des réponses sont tronqués (« … (n éléments) »).

## Conventions

- **Collecte** (`POST …/collect`) : appelle les API externes, normalise, stocke, puis renvoie une liste de résultats par source :
  `status` = `success` | `cached` (donnée encore valide, pas d’appel) | `skipped` (clé API absente) | `error` (erreur de la source, n’interrompt pas les autres).
  `?force=true` ignore le cache.
- **Lecture** (`GET`) : ne lit que la base, sans aucun appel externe.
- **Erreurs** : `{ statusCode, error, message }`. 400 validation, 404 ressource inconnue, 422 géocodage ambigu, 502 source externe en échec.

## Sommaire des routes

| Méthode | Route | Rôle |
|---|---|---|
| GET | `/geo/search` | Autocomplétion BAN, sans enregistrement. |
| POST | `/addresses` | Géocode une adresse (texte `q` ou `lat`/`lon`) et l’enregistre avec sa commune et sa parcelle. `?force=true` ignore le cache. |
| GET | `/addresses` | Adresses enregistrées, paginées (`page`, `limit`), filtrables par `insee`. |
| GET | `/addresses/:id` | Adresse pivot + commune + parcelle (géométrie GeoJSON). |
| GET | `/addresses/:id/indicators` | Indicateurs calculés à l’adresse, tous domaines (climat, mobilité, services). |
| POST | `/addresses/:id/urbanism/collect` | Collecte zones PLU, prescriptions, servitudes (AC1) et monuments historiques. |
| GET | `/addresses/:id/urbanism` | Zone PLU au point et alentours, emplacements réservés, éléments protégés, périmètres MH. |
| GET | `/communes` | Communes enregistrées (filtres `department`, `region`). |
| GET | `/communes/:insee` | Commune (collectée à la volée si absente). |
| POST | `/communes/:insee/collect` | Recharge une commune depuis l’API Géo. |
| POST | `/departments/:dep/communes/collect` | Importe toutes les communes d’un département. |
| GET | `/parcels/:idu` | Parcelle cadastrale avec géométrie (collectée à la volée si absente). |
| POST | `/addresses/:id/building/collect` | Collecte RNB, BDNB, DPE, copropriété (RNIC) et DVF de la commune. |
| GET | `/addresses/:id/building` | Bâtiment, DPE de référence et voisins, copropriété, présomptions plomb/amiante, interdiction de louer. |
| GET | `/addresses/:id/dvf` | Ventes DVF dans un rayon (`radius`, défaut 500 m), avec prix au m². |
| POST | `/communes/:insee/dvf/collect` | Import DVF d’une commune (`years=2023,2024`, défaut : toutes les années publiées) + recalcul de l’indice. |
| GET | `/communes/:insee/dvf` | Ventes DVF de la commune (filtres `year`, `type`, pagination). |
| GET | `/communes/:insee/price-index` | Prix au m² médian, moyen et quartiles par année et type de bien. |
| POST | `/communes/:insee/price-index/compute` | Recalcule l’indice de prix à partir des ventes stockées. |
| POST | `/addresses/:id/risks/collect` | Collecte Géorisques (rapport à l’adresse, radon, sismicité, CatNat, sites) + OLD (WFS IGN). |
| GET | `/addresses/:id/risks` | Synthèse des risques : aléas présents, profil communal, CatNat, sites proches, risques biologiques. |
| GET | `/communes/:insee/catnat` | Historique complet des arrêtés CatNat de la commune. |
| POST | `/bio-risks` | Saisie de risques biologiques (aucune API nationale) : moustique tigre, termites, loup… |
| GET | `/bio-risks` | Risques biologiques saisis (filtres `areaCode`, `species`). |
| POST | `/addresses/:id/water/collect` | Collecte qualité de l’eau (Hub’Eau), nappes, restrictions sécheresse (VigiEau). |
| GET | `/addresses/:id/water` | Dernières analyses (nitrates, pesticides, PFAS, dureté) avec dépassement de seuil, sécheresse, nappes. |
| GET | `/communes/:insee/water-quality` | Historique d’un paramètre (`parameter` = code SANDRE : 1340, 6276, 1345, 8847, 9268). |
| POST | `/addresses/:id/climate/collect` | Collecte climat observé (10 ans), projections 2041-2050, PVGIS, Atmo. |
| GET | `/addresses/:id/climate` | Gel, nuits tropicales, neige, vent, ensoleillement, projections multi-modèles, solaire, air/pollens. |
| POST | `/addresses/:id/nuisances/collect` | Collecte OSM (Overpass), plans d’exposition au bruit (WFS), survols (OpenSky). `radius` en mètres. |
| GET | `/addresses/:id/nuisances` | Nuisances par catégorie (nombre, plus proche), lignes HT, antennes, PEB, survols. |
| POST | `/addresses/:id/energy/collect` | Collecte réseau de chaleur (FCU), desserte gaz (GRDF), consommation électrique (Enedis). |
| GET | `/addresses/:id/energy` | Réseaux disponibles et consommation résidentielle (adresse ou moyenne communale). |
| POST | `/addresses/:id/services/collect` | Collecte établissements (Recherche d’entreprises, OSM), écoles, temps de trajet IGN. |
| GET | `/addresses/:id/services` | Services par catégorie, urgences, boulangeries ouvertes le dimanche, temps de trajet. |
| GET | `/addresses/:id/schools` | Établissements scolaires proches avec IPS et taille moyenne des classes. |
| POST | `/communes/:insee/socio/collect` | Collecte recensement (Melodi), fiscalité locale (DGFiP), délinquance (SSMSI). |
| GET | `/communes/:insee/socio` | Démographie (séries + dernière valeur), taxes et évolution, délinquance. |
| POST | `/addresses/:id/mobility/collect` | Collecte bornes IRVE, parkings, arrêts, aménagements cyclables, flux GTFS. |
| GET | `/addresses/:id/mobility` | Arrêts à moins de 800 m, bornes, parkings, pistes cyclables, flux GTFS couvrant la commune. |
| POST | `/connectivity/fixed/import` | Import national ARCEP de l’éligibilité fixe par commune. |
| POST | `/connectivity/mobile-sites/import` | Import national ARCEP des sites mobiles (2G à 5G) par opérateur. |
| POST | `/addresses/:id/connectivity/collect` | S’assure que les deux référentiels ARCEP sont chargés et à jour. |
| GET | `/addresses/:id/connectivity` | Taux de fibre communal, proximité des sites 4G/5G par opérateur. |
| POST | `/addresses/:id/collect` | Collecte tous les modules, ou une sélection (`modules=risk,water`). `force=true` ignore le cache. |
| POST | `/addresses/collect` | Géocode puis collecte (one-shot), avec sélection de modules. |
| GET | `/addresses/:id/report` | Rapport consolidé (tous modules), lecture seule. |
| GET | `/sources` | Registre des sources : statut de vérification, TTL, clé requise. |
| GET | `/sources/fetch-logs` | Journal des collectes (filtres `source`, `status`, `target`, pagination). |
| DELETE | `/addresses/:id` | Supprime une adresse et ses données rattachées (cascade). |

## Géo : adresses, communes, parcelles, urbanisme

### `GET /geo/search`

Autocomplétion BAN, sans enregistrement.

**Requête**

```http
GET /api/geo/search?q=2 rue de la republique amiens&limit=2
```

**Réponse** `200`

```json
[
  {
    "label": "2 Rue de la République 80000 Amiens",
    "score": 0.9759727272727271,
    "type": "housenumber",
    "banId": "80021_6820_00002",
    "inseeCode": "80021",
    "latitude": 49.892808,
    "longitude": 2.297087
  },
  {
    "label": "Rue de la République 80000 Amiens",
    "score": 0.8166348051948051,
    "type": "street",
    "banId": "80021_4wm6pe",
    "inseeCode": "80021",
    "latitude": 49.892079,
    "longitude": 2.296913
  }
]
```

### `POST /addresses`

Géocode une adresse (texte `q` ou `lat`/`lon`) et l’enregistre avec sa commune et sa parcelle. `?force=true` ignore le cache.

**Requête**

```http
POST /api/addresses
Content-Type: application/json

{
  "q": "2 rue de la République, Amiens"
}
```

**Réponse** `201`

```json
{
  "address": {
    "sourceCode": "ban",
    "fetchedAt": "2026-10-02T00:00:37.228Z",
    "expiresAt": "2026-11-01T00:00:37.228Z",
    "id": 1,
    "banId": "80021_6820_00002",
    "label": "2 Rue de la République 80000 Amiens",
    "housenumber": "2",
    "street": "Rue de la République",
    "postcode": "80000",
    "city": "Amiens",
    "inseeCode": "80021",
    "latitude": 49.892808,
    "longitude": 2.297087,
    "geocodeScore": 0.976,
    "geocodeType": "housenumber",
    "parcelIdu": "80021000VD0027",
    "rnbId": "QSQYSSG72D3F",
    "createdAt": "2026-10-01T23:55:42.554Z",
    "updatedAt": "2026-10-02T00:00:37.228Z"
  },
  "outcomes": [
    {
      "source": "ban",
      "target": "address:1",
      "status": "success",
      "items": 1,
      "fetchedAt": "2026-10-02T00:00:37.228Z",
      "expiresAt": "2026-11-01T00:00:37.228Z"
    },
    {
      "source": "geo_api",
      "target": "commune:80021",
      "status": "cached",
      "items": 1,
      "fetchedAt": "2026-10-01T23:55:42.450Z",
      "expiresAt": "2026-12-30T23:55:42.450Z"
    },
    "… (3 éléments)"
  ]
}
```

### `GET /addresses`

Adresses enregistrées, paginées (`page`, `limit`), filtrables par `insee`.

**Requête**

```http
GET /api/addresses?insee=80021&limit=2
```

**Réponse** `200`

```json
{
  "total": 1,
  "page": 1,
  "limit": 2,
  "items": [
    {
      "sourceCode": "ban",
      "fetchedAt": "2026-10-02T00:00:37.228Z",
      "expiresAt": "2026-11-01T00:00:37.228Z",
      "id": 1,
      "banId": "80021_6820_00002",
      "label": "2 Rue de la République 80000 Amiens",
      "housenumber": "2",
      "street": "Rue de la République",
      "postcode": "80000",
      "city": "Amiens",
      "inseeCode": "80021",
      "latitude": 49.892808,
      "longitude": 2.297087,
      "geocodeScore": 0.976,
      "geocodeType": "housenumber",
      "parcelIdu": "80021000VD0027",
      "rnbId": "QSQYSSG72D3F",
      "createdAt": "2026-10-01T23:55:42.554Z",
      "updatedAt": "2026-10-02T00:00:37.228Z"
    }
  ]
}
```

### `GET /addresses/:id`

Adresse pivot + commune + parcelle (géométrie GeoJSON).

**Requête**

```http
GET /api/addresses/1
```

**Réponse** `200`

```json
{
  "sourceCode": "ban",
  "fetchedAt": "2026-10-02T00:00:37.228Z",
  "expiresAt": "2026-11-01T00:00:37.228Z",
  "id": 1,
  "banId": "80021_6820_00002",
  "label": "2 Rue de la République 80000 Amiens",
  "housenumber": "2",
  "street": "Rue de la République",
  "postcode": "80000",
  "city": "Amiens",
  "inseeCode": "80021",
  "latitude": 49.892808,
  "longitude": 2.297087,
  "geocodeScore": 0.976,
  "geocodeType": "housenumber",
  "parcelIdu": "80021000VD0027",
  "rnbId": "QSQYSSG72D3F",
  "createdAt": "2026-10-01T23:55:42.554Z",
  "updatedAt": "2026-10-02T00:00:37.228Z",
  "commune": {
    "sourceCode": "geo_api",
    "fetchedAt": "2026-10-01T23:59:25.750Z",
    "expiresAt": "2026-12-30T23:59:25.750Z",
    "inseeCode": "80021",
    "name": "Amiens",
    "departmentCode": "80",
    "departmentName": "Somme",
    "regionCode": "32",
    "regionName": "Hauts-de-France",
    "epciCode": "248000531",
    "postalCodes": [
      "80000",
      "80080",
      "… (3 éléments)"
    ],
    "population": 136449,
    "surfaceHa": 5040.16,
    "latitude": 49.8987,
    "longitude": 2.2847
  },
  "parcel": {
    "sourceCode": "apicarto_cadastre",
    "fetchedAt": "2026-10-01T23:55:42.558Z",
    "expiresAt": "2026-12-30T23:55:42.558Z",
    "idu": "80021000VD0027",
    "inseeCode": "80021",
    "prefix": "000",
    "section": "VD",
    "numero": "0027",
    "sheet": 1,
    "areaM2": 870,
    "geometry": {
      "type": "MultiPolygon",
      "coordinates": [
        [
          [
            [
              2.29667773,
              49.89300052
            ],
            [
              2.29673243,
              49.89298691
            ],
            "… (13 éléments)"
          ]
        ]
      ]
    }
  }
}
```

### `GET /addresses/:id/indicators`

Indicateurs calculés à l’adresse, tous domaines (climat, mobilité, services).

**Requête**

```http
GET /api/addresses/1/indicators
```

**Réponse** `200`

```json
[
  {
    "sourceCode": "open_meteo_archive",
    "fetchedAt": "2026-10-01T23:55:50.795Z",
    "expiresAt": "2027-10-01T23:55:50.795Z",
    "id": 1,
    "addressId": 1,
    "domain": "climate",
    "indicator": "frost_days_per_year",
    "valueNum": 33.6,
    "valueText": null,
    "unit": "jours/an",
    "details": {
      "period": "2016-2025",
      "gridLat": 49.876976,
      "gridLon": 2.347826,
      "elevation": 37
    }
  },
  {
    "sourceCode": "open_meteo_archive",
    "fetchedAt": "2026-10-01T23:55:50.795Z",
    "expiresAt": "2027-10-01T23:55:50.795Z",
    "id": 4,
    "addressId": 1,
    "domain": "climate",
    "indicator": "hot_days_per_year",
    "valueNum": 6.5,
    "valueText": null,
    "unit": "jours/an",
    "details": {
      "period": "2016-2025",
      "gridLat": 49.876976,
      "gridLon": 2.347826,
      "elevation": 37
    }
  },
  {
    "sourceCode": "open_meteo_archive",
    "fetchedAt": "2026-10-01T23:55:50.795Z",
    "expiresAt": "2027-10-01T23:55:50.795Z",
    "id": 10,
    "addressId": 1,
    "domain": "climate",
    "indicator": "precipitation_per_year",
    "valueNum": 767.2,
    "valueText": null,
    "unit": "mm/an",
    "details": {
      "period": "2016-2025",
      "gridLat": 49.876976,
      "gridLon": 2.347826,
      "elevation": 37
    }
  },
  "… (12 éléments)"
]
```

### `POST /addresses/:id/urbanism/collect`

Collecte zones PLU, prescriptions, servitudes (AC1) et monuments historiques.

**Requête**

```http
POST /api/addresses/1/urbanism/collect
```

**Réponse** `201`

```json
[
  {
    "source": "apicarto_gpu",
    "target": "address:1:zone-urba",
    "status": "cached",
    "items": 4,
    "fetchedAt": "2026-10-01T23:55:42.683Z",
    "expiresAt": "2026-10-31T23:55:42.683Z"
  },
  {
    "source": "apicarto_gpu",
    "target": "address:1:prescriptions",
    "status": "cached",
    "items": 100,
    "fetchedAt": "2026-10-01T23:55:42.933Z",
    "expiresAt": "2026-10-31T23:55:42.933Z"
  },
  {
    "source": "apicarto_gpu",
    "target": "address:1:sup",
    "status": "cached",
    "items": 14,
    "fetchedAt": "2026-10-01T23:55:43.679Z",
    "expiresAt": "2026-10-31T23:55:43.679Z"
  },
  "… (4 éléments)"
]
```

### `GET /addresses/:id/urbanism`

Zone PLU au point et alentours, emplacements réservés, éléments protégés, périmètres MH.

**Requête**

```http
GET /api/addresses/1/urbanism?radius=250
```

**Réponse** `200`

```json
{
  "currentZone": {
    "sourceCode": "apicarto_gpu",
    "fetchedAt": "2026-10-01T23:55:42.683Z",
    "expiresAt": "2026-10-31T23:55:42.683Z",
    "id": 1,
    "gpuId": "zone_urba.3462417",
    "inseeCode": "80021",
    "documentId": "80021_PLU_20251211",
    "label": "UAa",
    "labelLong": "Quartier reconstruit sud ouest du centre-ville",
    "zoneType": "U",
    "approvedAt": "2025-12-11",
    "regulationFile": "80021_reglement_20251211.pdf",
    "containsAddress": true,
    "distanceM": 0
  },
  "neighbouringZones": [
    {
      "sourceCode": "apicarto_gpu",
      "fetchedAt": "2026-10-01T23:55:42.683Z",
      "expiresAt": "2026-10-31T23:55:42.683Z",
      "id": 2,
      "gpuId": "zone_urba.3462465",
      "inseeCode": "80021",
      "documentId": "80021_PLU_20251211",
      "label": "UAd",
      "labelLong": "Quartier ancien Est du centre-ville",
      "zoneType": "U",
      "approvedAt": "2025-12-11",
      "regulationFile": "80021_reglement_20251211.pdf",
      "containsAddress": false,
      "distanceM": 42
    },
    {
      "sourceCode": "apicarto_gpu",
      "fetchedAt": "2026-10-01T23:55:42.683Z",
      "expiresAt": "2026-10-31T23:55:42.683Z",
      "id": 3,
      "gpuId": "zone_urba.3462472",
      "inseeCode": "80021",
      "documentId": "80021_PLU_20251211",
      "label": "UFe",
      "labelLong": "Emprises d'équipements d'enseignement et administratifs",
      "zoneType": "U",
      "approvedAt": "2025-12-11",
      "regulationFile": "80021_reglement_20251211.pdf",
      "containsAddress": false,
      "distanceM": 201
    },
    "… (3 éléments)"
  ],
  "reservedLocations": [],
  "protectedLandscape": [
    {
      "sourceCode": "apicarto_gpu",
      "fetchedAt": "2026-10-01T23:55:42.933Z",
      "expiresAt": "2026-10-31T23:55:42.933Z",
      "id": 36,
      "gpuId": "prescription_surf.14412272",
      "inseeCode": "80021",
      "documentId": "80021_PLU_20251211",
      "geometryKind": "surface",
      "typeCode": "07",
      "subtypeCode": "01",
      "label": "Bati ou ensemble bati",
      "nature": "Bati_patrimo",
      "typeLabel": "Patrimoine bâti, paysager ou éléments de paysage à protéger",
      "distanceM": 6
    },
    {
      "sourceCode": "apicarto_gpu",
      "fetchedAt": "2026-10-01T23:55:42.933Z",
      "expiresAt": "2026-10-31T23:55:42.933Z",
      "id": 21,
      "gpuId": "prescription_surf.14412273",
      "inseeCode": "80021",
      "documentId": "80021_PLU_20251211",
      "geometryKind": "surface",
      "typeCode": "07",
      "subtypeCode": "01",
      "label": "Bati ou ensemble bati",
      "nature": "Bati_patrimo",
      "typeLabel": "Patrimoine bâti, paysager ou éléments de paysage à protéger",
      "distanceM": 10
    },
    "… (44 éléments)"
  ],
  "otherPrescriptions": [
    {
      "sourceCode": "apicarto_gpu",
      "fetchedAt": "2026-10-01T23:55:42.933Z",
      "expiresAt": "2026-10-31T23:55:42.933Z",
      "id": 1,
      "gpuId": "prescription_surf.14411362",
      "inseeCode": "80021",
      "documentId": "80021_PLU_20251211",
      "geometryKind": "surface",
      "typeCode": "44",
      "subtypeCode": "01",
      "label": "PERIMETRE CENTRE VILLE",
      "nature": "Perim_CV",
      "typeLabel": null,
      "distanceM": 0
    },
    {
      "sourceCode": "apicarto_gpu",
      "fetchedAt": "2026-10-01T23:55:42.933Z",
      "expiresAt": "2026-10-31T23:55:42.933Z",
      "id": 43,
      "gpuId": "prescription_surf.14412463",
      "inseeCode": "80021",
      "documentId": "80021_PLU_20251211",
      "geometryKind": "surface",
      "typeCode": "23",
      "subtypeCode": "00",
      "label": "Secteur avec taille minimale des logements en zone U et AU STL",
      "nature": null,
      "typeLabel": null,
      "distanceM": 0
    },
    "… (45 éléments)"
  ],
  "historicMonumentPerimeter": [
    {
      "sourceCode": "apicarto_gpu",
      "fetchedAt": "2026-10-01T23:55:43.679Z",
      "expiresAt": "2026-10-31T23:55:43.679Z",
      "id": 13,
      "gpuId": "assiette_sup_s.5793398",
      "supType": "ac1",
      "name": "Périmètre délimité de l'ancien hôtel Christophle",
      "assietteType": "Périmètre des abords",
      "generatorId": "AC1-172014607-1906270892-1"
    },
    {
      "sourceCode": "apicarto_gpu",
      "fetchedAt": "2026-10-01T23:55:43.679Z",
      "expiresAt": "2026-10-31T23:55:43.679Z",
      "id": 7,
      "gpuId": "assiette_sup_s.6030992",
      "supType": "ac1",
      "name": "Périmètre délimité églises Saint-Remi et des cordeliers",
      "assietteType": "Périmètre des abords",
      "generatorId": "AC1-172014607-1906270884-1"
    },
    "… (7 éléments)"
  ],
  "otherEasements": [],
  "monuments": [
    {
      "sourceCode": "monuments",
      "fetchedAt": "2026-10-01T23:55:44.540Z",
      "expiresAt": "2026-12-30T23:55:44.540Z",
      "reference": "PA00116059",
      "name": "Ancien hôtel Christophle",
      "inseeCode": "80021",
      "denomination": "hôtel",
      "protectionType": "inscrit MH partiellement",
      "protectionText": "Façade (cad. AK 123) : inscription par arrêté du 8 septembre 1988",
      "latitude": 49.892328,
      "longitude": 2.298031,
      "distanceM": 86
    },
    {
      "sourceCode": "monuments",
      "fetchedAt": "2026-10-01T23:55:44.540Z",
      "expiresAt": "2026-12-30T23:55:44.540Z",
      "reference": "PA80000025",
      "name": "Église Saint-Remi et couvent des Cordeliers",
      "inseeCode": "80021",
      "denomination": "couvent;église",
      "protectionType": "inscrit MH partiellement",
      "protectionText": "L'église, sa sacristie et l'ancienne nef du couvent (cad. VE 107) : inscription par arrêté du 17 août 2001",
      "latitude": 49.891987,
      "longitude": 2.296573,
      "distanceM": 98
    },
    "… (20 éléments)"
  ]
}
```

### `GET /communes`

Communes enregistrées (filtres `department`, `region`).

**Requête**

```http
GET /api/communes?department=80&limit=2
```

**Réponse** `200`

```json
{
  "total": 771,
  "page": 1,
  "limit": 2,
  "items": [
    {
      "sourceCode": "geo_api",
      "fetchedAt": "2026-10-01T23:59:25.750Z",
      "expiresAt": "2026-12-30T23:59:25.750Z",
      "inseeCode": "80001",
      "name": "Abbeville",
      "departmentCode": "80",
      "departmentName": "Somme",
      "regionCode": "32",
      "regionName": "Hauts-de-France",
      "epciCode": "200070993",
      "postalCodes": [
        "80100"
      ],
      "population": 22395,
      "surfaceHa": 2624.09,
      "latitude": 50.1101,
      "longitude": 1.8319
    },
    {
      "sourceCode": "geo_api",
      "fetchedAt": "2026-10-01T23:59:25.750Z",
      "expiresAt": "2026-12-30T23:59:25.750Z",
      "inseeCode": "80002",
      "name": "Ablaincourt-Pressoir",
      "departmentCode": "80",
      "departmentName": "Somme",
      "regionCode": "32",
      "regionName": "Hauts-de-France",
      "epciCode": "200070928",
      "postalCodes": [
        "80320"
      ],
      "population": 263,
      "surfaceHa": 951.63,
      "latitude": 49.8412,
      "longitude": 2.8266
    }
  ]
}
```

### `GET /communes/:insee`

Commune (collectée à la volée si absente).

**Requête**

```http
GET /api/communes/80021
```

**Réponse** `200`

```json
{
  "sourceCode": "geo_api",
  "fetchedAt": "2026-10-01T23:59:25.750Z",
  "expiresAt": "2026-12-30T23:59:25.750Z",
  "inseeCode": "80021",
  "name": "Amiens",
  "departmentCode": "80",
  "departmentName": "Somme",
  "regionCode": "32",
  "regionName": "Hauts-de-France",
  "epciCode": "248000531",
  "postalCodes": [
    "80000",
    "80080",
    "… (3 éléments)"
  ],
  "population": 136449,
  "surfaceHa": 5040.16,
  "latitude": 49.8987,
  "longitude": 2.2847
}
```

### `POST /communes/:insee/collect`

Recharge une commune depuis l’API Géo.

**Requête**

```http
POST /api/communes/80021/collect
```

**Réponse** `201`

```json
{
  "source": "geo_api",
  "target": "commune:80021",
  "status": "cached",
  "items": 1,
  "fetchedAt": "2026-10-01T23:55:42.450Z",
  "expiresAt": "2026-12-30T23:55:42.450Z"
}
```

### `POST /departments/:dep/communes/collect`

Importe toutes les communes d’un département.

**Requête**

```http
POST /api/departments/80/communes/collect
```

**Réponse** `201`

```json
{
  "source": "geo_api",
  "target": "department:80",
  "status": "cached",
  "items": 771,
  "fetchedAt": "2026-10-01T23:59:25.750Z",
  "expiresAt": "2026-12-30T23:59:25.750Z"
}
```

### `GET /parcels/:idu`

Parcelle cadastrale avec géométrie (collectée à la volée si absente).

**Requête**

```http
GET /api/parcels/80021000VD0027
```

**Réponse** `200`

```json
{
  "sourceCode": "apicarto_cadastre",
  "fetchedAt": "2026-10-01T23:55:42.558Z",
  "expiresAt": "2026-12-30T23:55:42.558Z",
  "idu": "80021000VD0027",
  "inseeCode": "80021",
  "prefix": "000",
  "section": "VD",
  "numero": "0027",
  "sheet": 1,
  "areaM2": 870,
  "geometry": {
    "type": "MultiPolygon",
    "coordinates": [
      [
        [
          [
            2.29667773,
            49.89300052
          ],
          [
            2.29673243,
            49.89298691
          ],
          "… (13 éléments)"
        ]
      ]
    ]
  }
}
```

## Bâtiment et marché

### `POST /addresses/:id/building/collect`

Collecte RNB, BDNB, DPE, copropriété (RNIC) et DVF de la commune.

**Requête**

```http
POST /api/addresses/1/building/collect
```

**Réponse** `201`

```json
[
  {
    "source": "rnb",
    "target": "address:1",
    "status": "cached",
    "items": 1,
    "fetchedAt": "2026-10-01T23:55:44.839Z",
    "expiresAt": "2026-10-31T23:55:44.839Z"
  },
  {
    "source": "bdnb",
    "target": "rnb:QSQYSSG72D3F",
    "status": "cached",
    "items": 1,
    "fetchedAt": "2026-10-01T23:55:44.999Z",
    "expiresAt": "2026-12-30T23:55:44.999Z"
  },
  {
    "source": "ademe_dpe",
    "target": "address:1",
    "status": "cached",
    "items": 26,
    "fetchedAt": "2026-10-01T23:55:45.705Z",
    "expiresAt": "2026-10-31T23:55:45.705Z"
  },
  "… (9 éléments)"
]
```

### `GET /addresses/:id/building`

Bâtiment, DPE de référence et voisins, copropriété, présomptions plomb/amiante, interdiction de louer.

**Requête**

```http
GET /api/addresses/1/building
```

**Réponse** `200`

```json
{
  "building": {
    "sourceCode": "rnb",
    "fetchedAt": "2026-10-01T23:55:44.839Z",
    "expiresAt": "2026-10-31T23:55:44.839Z",
    "rnbId": "QSQYSSG72D3F",
    "bdnbGroupId": "bdnb-bg-66L6-LSZ5-2YK9",
    "status": "constructed",
    "inseeCode": "80021",
    "constructionYear": 1955,
    "heightM": 13,
    "levels": 6,
    "dwellings": 17,
    "wallMaterial": "BRIQUES",
    "roofMaterial": "ARDOISES",
    "mainUsage": "Résidentiel collectif",
    "dpeClassBdnb": "E",
    "condoRegistration": "AC6175483",
    "irisCode": "800211301",
    "footprintM2": 814,
    "groundAltitudeM": 33,
    "latitude": 49.892901,
    "longitude": 2.296932
  },
  "dpe": {
    "reference": {
      "sourceCode": "ademe_dpe",
      "fetchedAt": "2026-10-01T23:55:45.705Z",
      "expiresAt": "2026-10-31T23:55:45.705Z",
      "numeroDpe": "2680E0005882N",
      "rnbId": null,
      "banId": "80021_6820_00002",
      "addressLabel": "2 Rue de la République 80000 Amiens",
      "inseeCode": "80021",
      "issuedAt": "2026-01-03",
      "energyClass": "E",
      "ghgClass": "C",
      "energyKwhM2": 267,
      "ghgKgM2": 17,
      "constructionYear": null,
      "constructionPeriod": "1948-1974",
      "buildingType": "immeuble",
      "livingAreaM2": null,
      "ceilingHeightM": 2.7,
      "heatingEnergy": "Électricité",
      "annualCostEur": 39035.1,
      "latitude": 49.892808,
      "longitude": 2.297087,
      "sameAddress": true,
      "distanceM": 0
    },
    "all": [
      {
        "sourceCode": "ademe_dpe",
        "fetchedAt": "2026-10-01T23:55:45.705Z",
        "expiresAt": "2026-10-31T23:55:45.705Z",
        "numeroDpe": "2680E1531118L",
        "rnbId": null,
        "banId": "80021_2810_00002",
        "addressLabel": "2 Rue Duméril 80000 Amiens",
        "inseeCode": "80021",
        "issuedAt": "2026-06-08",
        "energyClass": "D",
        "ghgClass": "B",
        "energyKwhM2": 272,
        "ghgKgM2": 10,
        "constructionYear": null,
        "constructionPeriod": "avant 1948",
        "buildingType": "appartement",
        "livingAreaM2": 14.4,
        "ceilingHeightM": 2.5,
        "heatingEnergy": "Électricité",
        "annualCostEur": 549.3,
        "latitude": 49.892775,
        "longitude": 2.296794,
        "sameAddress": false,
        "distanceM": 21
      },
      {
        "sourceCode": "ademe_dpe",
        "fetchedAt": "2026-10-01T23:55:45.705Z",
        "expiresAt": "2026-10-31T23:55:45.705Z",
        "numeroDpe": "2680E0005882N",
        "rnbId": null,
        "banId": "80021_6820_00002",
        "addressLabel": "2 Rue de la République 80000 Amiens",
        "inseeCode": "80021",
        "issuedAt": "2026-01-03",
        "energyClass": "E",
        "ghgClass": "C",
        "energyKwhM2": 267,
        "ghgKgM2": 17,
        "constructionYear": null,
        "constructionPeriod": "1948-1974",
        "buildingType": "immeuble",
        "livingAreaM2": null,
        "ceilingHeightM": 2.7,
        "heatingEnergy": "Électricité",
        "annualCostEur": 39035.1,
        "latitude": 49.892808,
        "longitude": 2.297087,
        "sameAddress": true,
        "distanceM": 0
      },
      "… (26 éléments)"
    ]
  },
  "condominium": {
    "sourceCode": "rnic",
    "fetchedAt": "2026-10-01T23:55:45.845Z",
    "expiresAt": "2026-12-30T23:55:45.845Z",
    "registrationNumber": "AC6175483",
    "name": "2 REPUBLIQUE / 2 DUMERIL",
    "addressLabel": "2 r de la republique 80000 Amiens",
    "inseeCode": "80021",
    "totalLots": 65,
    "housingLots": 26,
    "parkingLots": 0,
    "syndicType": "professionnel",
    "syndicName": "MASSET FRERES",
    "mandateStatus": "Mandat en cours",
    "mandateEndDate": "2025-12-13",
    "constructionPeriod": "DE_1961_A_1974",
    "regulationDate": "1962-04-05",
    "isAided": false,
    "priorityDistrict": null,
    "cadastralRefs": [
      "80021000VD0027"
    ],
    "latitude": 49.892752,
    "longitude": 2.296769
  },
  "ceilingHeightM": 2.7,
  "presumptions": {
    "leadRisk": false,
    "asbestosRisk": true,
    "rentalBanDate": "2034-01-01",
    "rentalBanned": false,
    "notes": [
      "Plomb : constat (CREP) obligatoire pour les logements construits avant le 01/01/1949.",
      "Amiante : repérage obligatoire si le permis de construire est antérieur au 01/07/1997."
    ]
  }
}
```

### `GET /addresses/:id/dvf`

Ventes DVF dans un rayon (`radius`, défaut 500 m), avec prix au m².

**Requête**

```http
GET /api/addresses/1/dvf?radius=150
```

**Réponse** `200`

```json
[
  {
    "sourceCode": "dvf",
    "fetchedAt": "2026-10-01T23:55:49.870Z",
    "expiresAt": "2027-03-30T23:55:49.870Z",
    "id": 30992,
    "rowHash": "3498fd3a15b611a5569e26ce13e8da303c16d73e",
    "mutationId": "2025-1046976",
    "mutationDate": "2025-12-22",
    "nature": "Vente",
    "priceEur": 4800000,
    "inseeCode": "80021",
    "parcelIdu": "80021000VD0035",
    "addressLabel": "8 RUE DUMERIL 80000 Amiens",
    "propertyType": null,
    "builtAreaM2": null,
    "rooms": null,
    "landAreaM2": null,
    "lotsCount": 0,
    "latitude": 49.893131,
    "longitude": 2.29584,
    "priceM2": null,
    "distanceM": 96
  },
  {
    "sourceCode": "dvf",
    "fetchedAt": "2026-10-01T23:55:49.870Z",
    "expiresAt": "2027-03-30T23:55:49.870Z",
    "id": 30993,
    "rowHash": "91ac7edb7e5dcffcafa9caf0275dbe25ec31c36a",
    "mutationId": "2025-1046976",
    "mutationDate": "2025-12-22",
    "nature": "Vente",
    "priceEur": 4800000,
    "inseeCode": "80021",
    "parcelIdu": "80021000VD0035",
    "addressLabel": "11 RUE DELAMBRE 80000 Amiens",
    "propertyType": null,
    "builtAreaM2": null,
    "rooms": null,
    "landAreaM2": null,
    "lotsCount": 0,
    "latitude": 49.893131,
    "longitude": 2.29584,
    "priceM2": null,
    "distanceM": 96
  },
  {
    "sourceCode": "dvf",
    "fetchedAt": "2026-10-01T23:55:49.870Z",
    "expiresAt": "2027-03-30T23:55:49.870Z",
    "id": 30994,
    "rowHash": "e2e2ce96e9b189ebea30226de362cf4c32c91e96",
    "mutationId": "2025-1046976",
    "mutationDate": "2025-12-22",
    "nature": "Vente",
    "priceEur": 4800000,
    "inseeCode": "80021",
    "parcelIdu": "80021000VD0035",
    "addressLabel": "11 RUE DELAMBRE 80000 Amiens",
    "propertyType": null,
    "builtAreaM2": null,
    "rooms": null,
    "landAreaM2": null,
    "lotsCount": 0,
    "latitude": 49.893131,
    "longitude": 2.29584,
    "priceM2": null,
    "distanceM": 96
  },
  "… (296 éléments)"
]
```

### `POST /communes/:insee/dvf/collect`

Import DVF d’une commune (`years=2023,2024`, défaut : toutes les années publiées) + recalcul de l’indice.

**Requête**

```http
POST /api/communes/80021/dvf/collect?years=2024
```

**Réponse** `201`

```json
[
  {
    "source": "dvf",
    "target": "commune:80021:2024",
    "status": "cached",
    "items": 4967,
    "fetchedAt": "2026-10-01T23:55:49.164Z",
    "expiresAt": "2027-03-30T23:55:49.164Z"
  }
]
```

### `GET /communes/:insee/dvf`

Ventes DVF de la commune (filtres `year`, `type`, pagination).

**Requête**

```http
GET /api/communes/80021/dvf?year=2024&type=Appartement&limit=2
```

**Réponse** `200`

```json
{
  "total": 1197,
  "page": 1,
  "limit": 2,
  "items": [
    {
      "sourceCode": "dvf",
      "fetchedAt": "2026-10-01T23:55:49.164Z",
      "expiresAt": "2027-03-30T23:55:49.164Z",
      "id": 25761,
      "rowHash": "c093e3ef7fe9c70c9b0291a6096c697b22ca720b",
      "mutationId": "2024-984091",
      "mutationDate": "2024-12-30",
      "nature": "Vente en l'état futur d'achèvement",
      "priceEur": 176890,
      "inseeCode": "80021",
      "parcelIdu": "80021000IN0554",
      "addressLabel": "34 RUE HAUTE DES CHAMPS 80000 Amiens",
      "propertyType": "Appartement",
      "builtAreaM2": 44,
      "rooms": 2,
      "landAreaM2": null,
      "lotsCount": 1,
      "latitude": 49.899646,
      "longitude": 2.259284
    },
    {
      "sourceCode": "dvf",
      "fetchedAt": "2026-10-01T23:55:49.164Z",
      "expiresAt": "2027-03-30T23:55:49.164Z",
      "id": 25759,
      "rowHash": "0537df17c6bd41d40995ae5690f5b7ee0f22503c",
      "mutationId": "2024-984088",
      "mutationDate": "2024-12-30",
      "nature": "Vente en l'état futur d'achèvement",
      "priceEur": 235000,
      "inseeCode": "80021",
      "parcelIdu": "80021000IN0554",
      "addressLabel": "34 RUE HAUTE DES CHAMPS 80000 Amiens",
      "propertyType": "Appartement",
      "builtAreaM2": 67,
      "rooms": 3,
      "landAreaM2": null,
      "lotsCount": 1,
      "latitude": 49.899646,
      "longitude": 2.259284
    }
  ]
}
```

### `GET /communes/:insee/price-index`

Prix au m² médian, moyen et quartiles par année et type de bien.

**Requête**

```http
GET /api/communes/80021/price-index
```

**Réponse** `200`

```json
[
  {
    "inseeCode": "80021",
    "year": 2021,
    "propertyType": "Appartement",
    "salesCount": 943,
    "medianPriceM2": 2291.67,
    "meanPriceM2": 2434.77,
    "q1PriceM2": 1807.07,
    "q3PriceM2": 2813.39,
    "computedAt": "2026-10-01T23:59:26.529Z"
  },
  {
    "inseeCode": "80021",
    "year": 2021,
    "propertyType": "Ensemble",
    "salesCount": 1920,
    "medianPriceM2": 2250,
    "meanPriceM2": 2384.44,
    "q1PriceM2": 1817.34,
    "q3PriceM2": 2785.69,
    "computedAt": "2026-10-01T23:59:26.529Z"
  },
  {
    "inseeCode": "80021",
    "year": 2021,
    "propertyType": "Maison",
    "salesCount": 977,
    "medianPriceM2": 2226.19,
    "meanPriceM2": 2335.85,
    "q1PriceM2": 1825,
    "q3PriceM2": 2725,
    "computedAt": "2026-10-01T23:59:26.529Z"
  },
  "… (15 éléments)"
]
```

### `POST /communes/:insee/price-index/compute`

Recalcule l’indice de prix à partir des ventes stockées.

**Requête**

```http
POST /api/communes/80021/price-index/compute
```

**Réponse** `201`

```json
[
  {
    "inseeCode": "80021",
    "year": 2021,
    "propertyType": "Appartement",
    "salesCount": 943,
    "medianPriceM2": 2291.67,
    "meanPriceM2": 2434.77,
    "q1PriceM2": 1807.07,
    "q3PriceM2": 2813.39,
    "computedAt": "2026-10-02T00:00:37.621Z"
  },
  {
    "inseeCode": "80021",
    "year": 2021,
    "propertyType": "Ensemble",
    "salesCount": 1920,
    "medianPriceM2": 2250,
    "meanPriceM2": 2384.44,
    "q1PriceM2": 1817.34,
    "q3PriceM2": 2785.69,
    "computedAt": "2026-10-02T00:00:37.621Z"
  },
  {
    "inseeCode": "80021",
    "year": 2021,
    "propertyType": "Maison",
    "salesCount": 977,
    "medianPriceM2": 2226.19,
    "meanPriceM2": 2335.85,
    "q1PriceM2": 1825,
    "q3PriceM2": 2725,
    "computedAt": "2026-10-02T00:00:37.621Z"
  },
  "… (15 éléments)"
]
```

## Risques

### `POST /addresses/:id/risks/collect`

Collecte Géorisques (rapport à l’adresse, radon, sismicité, CatNat, sites) + OLD (WFS IGN).

**Requête**

```http
POST /api/addresses/1/risks/collect
```

**Réponse** `201`

```json
[
  {
    "source": "georisques",
    "target": "address:1:report",
    "status": "cached",
    "items": 18,
    "fetchedAt": "2026-10-01T23:55:50.776Z",
    "expiresAt": "2026-10-31T23:55:50.776Z"
  },
  {
    "source": "georisques",
    "target": "commune:80021:profile",
    "status": "cached",
    "items": 1,
    "fetchedAt": "2026-10-01T23:55:50.774Z",
    "expiresAt": "2026-10-31T23:55:50.774Z"
  },
  {
    "source": "georisques",
    "target": "commune:80021:catnat",
    "status": "cached",
    "items": 14,
    "fetchedAt": "2026-10-01T23:55:50.784Z",
    "expiresAt": "2026-10-31T23:55:50.784Z"
  },
  "… (5 éléments)"
]
```

### `GET /addresses/:id/risks`

Synthèse des risques : aléas présents, profil communal, CatNat, sites proches, risques biologiques.

**Requête**

```http
GET /api/addresses/1/risks
```

**Réponse** `200`

```json
{
  "atAddress": [
    {
      "sourceCode": "georisques",
      "fetchedAt": "2026-10-01T23:55:50.776Z",
      "expiresAt": "2026-10-31T23:55:50.776Z",
      "id": 2,
      "addressId": 1,
      "hazardCode": "inondation",
      "category": "natural",
      "label": "Inondation",
      "present": true,
      "communeStatus": "Risque Existant",
      "addressStatus": "Risque non Connu",
      "details": null
    },
    {
      "sourceCode": "georisques",
      "fetchedAt": "2026-10-01T23:55:50.776Z",
      "expiresAt": "2026-10-31T23:55:50.776Z",
      "id": 13,
      "addressId": 1,
      "hazardCode": "radon",
      "category": "natural",
      "label": "Radon",
      "present": true,
      "communeStatus": "Risque Existant - faible",
      "addressStatus": "Risque Existant - faible",
      "details": null
    },
    "… (8 éléments)"
  ],
  "notPresent": [
    "avalanche",
    "cyclone",
    "… (11 éléments)"
  ],
  "commune": {
    "sourceCode": "georisques",
    "fetchedAt": "2026-10-01T23:55:50.774Z",
    "expiresAt": "2026-10-31T23:55:50.774Z",
    "inseeCode": "80021",
    "radonClass": 1,
    "seismicZone": "1 - TRES FAIBLE",
    "knownRisks": [
      "Inondation",
      "Par ruissellement et coulée de boue",
      "… (8 éléments)"
    ],
    "floodAtlases": [
      {
        "code": "80DDTM20010005",
        "label": "Selle (département de la Somme)",
        "published": "2001-01-01"
      },
      {
        "code": "80DDTM20030002",
        "label": "Somme (département de la Somme)",
        "published": "2003-01-01"
      },
      "… (3 éléments)"
    ]
  },
  "catnat": {
    "total": 10,
    "byHazard": {
      "Mouvement de Terrain": 4,
      "Inondations et/ou Coulées de Boue": 5,
      "Inondations Remontée Nappe": 1
    },
    "latest": [
      {
        "sourceCode": "georisques",
        "fetchedAt": "2026-10-01T23:55:50.784Z",
        "expiresAt": "2026-10-31T23:55:50.784Z",
        "codeNational": "INTE2207961A",
        "inseeCode": "80021",
        "hazardLabel": "Mouvement de Terrain",
        "eventStart": "2021-02-09",
        "eventEnd": "2021-02-09",
        "decreeDate": "2022-03-14",
        "journalDate": "2022-03-30"
      },
      {
        "sourceCode": "georisques",
        "fetchedAt": "2026-10-01T23:55:50.784Z",
        "expiresAt": "2026-10-31T23:55:50.784Z",
        "codeNational": "INTE1731318A",
        "inseeCode": "80021",
        "hazardLabel": "Inondations et/ou Coulées de Boue",
        "eventStart": "2017-06-02",
        "eventEnd": "2017-06-02",
        "decreeDate": "2017-11-21",
        "journalDate": "2017-12-15"
      },
      "… (10 éléments)"
    ]
  },
  "sites": {
    "seveso": [],
    "icpe": [
      {
        "sourceCode": "georisques",
        "fetchedAt": "2026-10-01T23:55:50.784Z",
        "expiresAt": "2026-10-31T23:55:50.784Z",
        "id": 66,
        "siteType": "icpe",
        "externalId": "0003801169",
        "name": "PICARD",
        "inseeCode": "80021",
        "status": "Non ICPE",
        "sevesoStatus": null,
        "subtype": null,
        "details": {
          "regime": "Non ICPE",
          "naf": null,
          "siret": "78493968805071",
          "ied": false,
          "priority": false
        },
        "latitude": 49.894658,
        "longitude": 2.296637,
        "distanceM": 208
      },
      {
        "sourceCode": "georisques",
        "fetchedAt": "2026-10-01T23:55:50.784Z",
        "expiresAt": "2026-10-31T23:55:50.784Z",
        "id": 67,
        "siteType": "icpe",
        "externalId": "0003801279",
        "name": "SARL CENTRALE FRAIS",
        "inseeCode": "80021",
        "status": "Autres régimes",
        "sevesoStatus": null,
        "subtype": "10",
        "details": {
          "regime": "Autres régimes",
          "naf": "10",
          "siret": "50890512200034",
          "ied": false,
          "priority": false
        },
        "latitude": 49.894658,
        "longitude": 2.296637,
        "distanceM": 208
      },
      "… (50 éléments)"
    ],
    "pollutedSoils": [
      {
        "sourceCode": "georisques",
        "fetchedAt": "2026-10-01T23:55:50.784Z",
        "expiresAt": "2026-10-31T23:55:50.784Z",
        "id": 22,
        "siteType": "casias",
        "externalId": "SSP4022716",
        "name": "rue Duméril",
        "inseeCode": "80021",
        "status": "En arrêt",
        "sevesoStatus": null,
        "subtype": "casias",
        "details": {
          "address": "rue Duméril",
          "sheet": "https://fiches-risques.brgm.fr/georisques/casias/SSP4022716"
        },
        "latitude": 49.893169,
        "longitude": 2.296195,
        "distanceM": 75
      },
      {
        "sourceCode": "georisques",
        "fetchedAt": "2026-10-01T23:55:50.784Z",
        "expiresAt": "2026-10-31T23:55:50.784Z",
        "id": 46,
        "siteType": "casias",
        "externalId": "SSP4022818",
        "name": "Fabrique de chandelles",
        "inseeCode": "80021",
        "status": "En arrêt",
        "sevesoStatus": null,
        "subtype": "casias",
        "details": {
          "address": "11 rue Alphonse Paillat",
          "sheet": "https://fiches-risques.brgm.fr/georisques/casias/SSP4022818"
        },
        "latitude": 49.891549,
        "longitude": 2.297516,
        "distanceM": 143
      },
      "… (55 éléments)"
    ],
    "cavities": [
      {
        "sourceCode": "georisques",
        "fetchedAt": "2026-10-01T23:55:50.784Z",
        "expiresAt": "2026-10-31T23:55:50.784Z",
        "id": 3,
        "siteType": "cavity",
        "externalId": "PICAW0004163",
        "name": "Rue des sergents",
        "inseeCode": "80021",
        "status": null,
        "sevesoStatus": null,
        "subtype": "cave",
        "details": null,
        "latitude": 49.89449,
        "longitude": 2.298798,
        "distanceM": 224
      },
      {
        "sourceCode": "georisques",
        "fetchedAt": "2026-10-01T23:55:50.784Z",
        "expiresAt": "2026-10-31T23:55:50.784Z",
        "id": 4,
        "siteType": "cavity",
        "externalId": "PICAW0004164",
        "name": "Rue du Cloître de la Barge",
        "inseeCode": "80021",
        "status": null,
        "sevesoStatus": null,
        "subtype": "cave",
        "details": null,
        "latitude": 49.8935,
        "longitude": 2.300411,
        "distanceM": 250
      },
      "… (6 éléments)"
    ],
    "groundMovements": [
      {
        "sourceCode": "georisques",
        "fetchedAt": "2026-10-01T23:55:50.784Z",
        "expiresAt": "2026-10-31T23:55:50.784Z",
        "id": 7,
        "siteType": "ground_movement",
        "externalId": "11900607",
        "name": "58 rue Béranger - Point n°2",
        "inseeCode": "80021",
        "status": null,
        "sevesoStatus": null,
        "subtype": "Effondrement / Affaissement",
        "details": {
          "date": "2007-03-01",
          "reliability": "Fort",
          "comment": "limon"
        },
        "latitude": 49.890526,
        "longitude": 2.285918,
        "distanceM": 839
      },
      {
        "sourceCode": "georisques",
        "fetchedAt": "2026-10-01T23:55:50.784Z",
        "expiresAt": "2026-10-31T23:55:50.784Z",
        "id": 8,
        "siteType": "ground_movement",
        "externalId": "11900608",
        "name": "74/76 rue Béranger - Point n°3",
        "inseeCode": "80021",
        "status": null,
        "sevesoStatus": null,
        "subtype": "Effondrement / Affaissement",
        "details": {
          "date": "2004-02-01",
          "reliability": "Fort",
          "comment": "limon"
        },
        "latitude": 49.890354,
        "longitude": 2.285779,
        "distanceM": 855
      }
    ]
  },
  "biological": [
    {
      "sourceCode": "manual",
      "fetchedAt": "2026-10-01T23:59:26.586Z",
      "expiresAt": "2027-10-01T23:59:26.586Z",
      "id": 1,
      "scope": "department",
      "areaCode": "80",
      "species": "tiger_mosquito",
      "status": "implanté",
      "year": 2026,
      "referenceUrl": "https://sante.gouv.fr/sante-et-environnement/risques-microbiologiques-physiques-et-chimiques/especes-nuisibles-et-parasites/article/cartes-de-presence-du-mou…",
      "notes": null
    }
  ]
}
```

### `GET /communes/:insee/catnat`

Historique complet des arrêtés CatNat de la commune.

**Requête**

```http
GET /api/communes/80021/catnat
```

**Réponse** `200`

```json
[
  {
    "sourceCode": "georisques",
    "fetchedAt": "2026-10-01T23:55:50.784Z",
    "expiresAt": "2026-10-31T23:55:50.784Z",
    "codeNational": "INTE2207961A",
    "inseeCode": "80021",
    "hazardLabel": "Mouvement de Terrain",
    "eventStart": "2021-02-09",
    "eventEnd": "2021-02-09",
    "decreeDate": "2022-03-14",
    "journalDate": "2022-03-30"
  },
  {
    "sourceCode": "georisques",
    "fetchedAt": "2026-10-01T23:55:50.784Z",
    "expiresAt": "2026-10-31T23:55:50.784Z",
    "codeNational": "INTE1731318A",
    "inseeCode": "80021",
    "hazardLabel": "Inondations et/ou Coulées de Boue",
    "eventStart": "2017-06-02",
    "eventEnd": "2017-06-02",
    "decreeDate": "2017-11-21",
    "journalDate": "2017-12-15"
  },
  {
    "sourceCode": "georisques",
    "fetchedAt": "2026-10-01T23:55:50.784Z",
    "expiresAt": "2026-10-31T23:55:50.784Z",
    "codeNational": "INTE0200650A",
    "inseeCode": "80021",
    "hazardLabel": "Mouvement de Terrain",
    "eventStart": "2001-04-01",
    "eventEnd": "2001-04-27",
    "decreeDate": "2002-12-17",
    "journalDate": "2003-01-08"
  },
  "… (10 éléments)"
]
```

### `POST /bio-risks`

Saisie de risques biologiques (aucune API nationale) : moustique tigre, termites, loup…

**Requête**

```http
POST /api/bio-risks
Content-Type: application/json

{
  "items": [
    {
      "scope": "department",
      "areaCode": "80",
      "species": "tiger_mosquito",
      "status": "implanté",
      "year": 2026,
      "referenceUrl": "https://sante.gouv.fr/sante-et-environnement/risques-microbiologiques-physiques-et-chimiques/especes-nuisibles-et-parasites/article/cartes-de-presence-du-moustique-tigre-aedes-albopictus-en-france-metropolitaine"
    }
  ]
}
```

**Réponse** `201`

```json
{
  "upserted": 1
}
```

### `GET /bio-risks`

Risques biologiques saisis (filtres `areaCode`, `species`).

**Requête**

```http
GET /api/bio-risks?areaCode=80
```

**Réponse** `200`

```json
[
  {
    "sourceCode": "manual",
    "fetchedAt": "2026-10-02T00:00:37.665Z",
    "expiresAt": "2027-10-02T00:00:37.665Z",
    "id": 1,
    "scope": "department",
    "areaCode": "80",
    "species": "tiger_mosquito",
    "status": "implanté",
    "year": 2026,
    "referenceUrl": "https://sante.gouv.fr/sante-et-environnement/risques-microbiologiques-physiques-et-chimiques/especes-nuisibles-et-parasites/article/cartes-de-presence-du-mou…",
    "notes": null
  }
]
```

## Eau

### `POST /addresses/:id/water/collect`

Collecte qualité de l’eau (Hub’Eau), nappes, restrictions sécheresse (VigiEau).

**Requête**

```http
POST /api/addresses/1/water/collect
```

**Réponse** `201`

```json
[
  {
    "source": "hubeau_eau_potable",
    "target": "commune:80021",
    "status": "cached",
    "items": 207,
    "fetchedAt": "2026-10-01T23:55:50.790Z",
    "expiresAt": "2026-10-08T23:55:50.790Z"
  },
  {
    "source": "hubeau_nappes",
    "target": "address:1",
    "status": "cached",
    "items": 33,
    "fetchedAt": "2026-10-01T23:55:50.788Z",
    "expiresAt": "2026-10-08T23:55:50.788Z"
  },
  {
    "source": "vigieau",
    "target": "address:1",
    "status": "cached",
    "items": 3,
    "fetchedAt": "2026-10-01T23:55:50.793Z",
    "expiresAt": "2026-10-02T23:55:50.793Z"
  }
]
```

### `GET /addresses/:id/water`

Dernières analyses (nitrates, pesticides, PFAS, dureté) avec dépassement de seuil, sécheresse, nappes.

**Requête**

```http
GET /api/addresses/1/water
```

**Réponse** `200`

```json
{
  "drinkingWater": {
    "network": "AMIENS UDI",
    "distributor": "AMIENS METROPOLE",
    "lastConclusion": "Eau d’alimentation non conforme aux limites de qualité en vigueur pour les paramètres pesticides Desphényl-Chloridazone, et le total des pesticides analysés.…",
    "parameters": [
      {
        "key": "nitrates",
        "code": "1340",
        "label": "Nitrates (en NO3)",
        "value": 32.6,
        "rawValue": "32,6",
        "unit": "mg/L",
        "sampledAt": "2026-07-16T09:12:00.000Z",
        "exceedsLimit": false,
        "reference": "Limite de qualité : 50 mg/L"
      },
      {
        "key": "hardness",
        "code": "1345",
        "label": "Titre hydrotimétrique",
        "value": 31,
        "rawValue": "31,0",
        "unit": "°f",
        "sampledAt": "2025-12-18T09:53:00.000Z",
        "exceedsLimit": null,
        "reference": "Dureté : < 15 °f eau douce, > 30 °f eau très calcaire"
      },
      "… (5 éléments)"
    ]
  },
  "drought": [
    {
      "sourceCode": "vigieau",
      "fetchedAt": "2026-10-01T23:55:50.793Z",
      "expiresAt": "2026-10-02T23:55:50.793Z",
      "id": 1,
      "inseeCode": "80021",
      "zoneId": 6010234,
      "zoneCode": "22_80_7",
      "zoneName": "BASSIN DE LA  SELLE",
      "zoneType": "SUP",
      "severity": "alerte",
      "decreeStart": "2026-08-21",
      "decreeEnd": null,
      "decreeUrl": "https://regleau.s3.gra.perf.cloud.ovh.net/arrete-restriction/37849/bd3d6623-c4f4-45b5-aa4c-f4069b678da4/Arr%C3%83%C2%AAt%C3%83%C2%A9_sign%C3%83%C2%A9.pdf",
      "usages": [
        {
          "name": "Alimentation des fontaines publiques et privées d’ornement",
          "theme": "Alimenter des fontaines et autres usages de loisirs",
          "description": "L'alimentation des fontaines publiques et privées en circuit ouvert est interdite"
        },
        {
          "name": "Arrosage des golfs(Conformément à l'accord cadre golf et environnement 2019-2024",
          "theme": "Arroser",
          "description": "Interdiction d'arroser les terrains de golf de 8 heures à 20 heures de façon à diminuer la consommation d'eau sur le volume hebdomadaire de 15 à 30%. Tenue d…"
        },
        "… (13 éléments)"
      ]
    },
    {
      "sourceCode": "vigieau",
      "fetchedAt": "2026-10-01T23:55:50.793Z",
      "expiresAt": "2026-10-02T23:55:50.793Z",
      "id": 2,
      "inseeCode": "80021",
      "zoneId": 6010245,
      "zoneCode": "22_80_7",
      "zoneName": "BASSIN DE LA  SELLE",
      "zoneType": "SOU",
      "severity": "alerte",
      "decreeStart": "2026-08-21",
      "decreeEnd": null,
      "decreeUrl": "https://regleau.s3.gra.perf.cloud.ovh.net/arrete-restriction/37849/bd3d6623-c4f4-45b5-aa4c-f4069b678da4/Arr%C3%83%C2%AAt%C3%83%C2%A9_sign%C3%83%C2%A9.pdf",
      "usages": [
        {
          "name": "Alimentation des fontaines publiques et privées d’ornement",
          "theme": "Alimenter des fontaines et autres usages de loisirs",
          "description": "L'alimentation des fontaines publiques et privées en circuit ouvert est interdite"
        },
        {
          "name": "Arrosage des golfs(Conformément à l'accord cadre golf et environnement 2019-2024",
          "theme": "Arroser",
          "description": "Interdiction d'arroser les terrains de golf de 8 heures à 20 heures de façon à diminuer la consommation d'eau sur le volume hebdomadaire de 15 à 30%. Tenue d…"
        },
        "… (9 éléments)"
      ]
    },
    "… (3 éléments)"
  ],
  "groundwater": [
    {
      "sourceCode": "hubeau_nappes",
      "fetchedAt": "2026-10-01T23:55:50.788Z",
      "expiresAt": "2026-10-08T23:55:50.788Z",
      "codeBss": "00463X0036/H1",
      "bssId": "BSS000DXBD",
      "inseeCode": "80173",
      "communeName": "Cardonnette",
      "altitudeM": 87,
      "depthM": 48.75,
      "measuresCount": 7923,
      "firstMeasureDate": "1970-01-07",
      "lastMeasureDate": "2026-09-29",
      "lastWaterDepthM": 45.59,
      "lastLevelNgfM": 41.37,
      "latitude": 49.950686,
      "longitude": 2.35976,
      "distanceM": 7845,
      "active": true
    },
    {
      "sourceCode": "hubeau_nappes",
      "fetchedAt": "2026-10-01T23:55:50.788Z",
      "expiresAt": "2026-10-08T23:55:50.788Z",
      "codeBss": "00465X0007/F",
      "bssId": "BSS000DXKH",
      "inseeCode": "80305",
      "communeName": "Ferrières",
      "altitudeM": 107,
      "depthM": 112,
      "measuresCount": 7403,
      "firstMeasureDate": "1997-05-25",
      "lastMeasureDate": "2026-09-29",
      "lastWaterDepthM": 73.75,
      "lastLevelNgfM": 33.49,
      "latitude": 49.895282,
      "longitude": 2.177815,
      "distanceM": 8548,
      "active": true
    },
    "… (5 éléments)"
  ],
  "sanitation": {
    "covered": false,
    "note": "Raccordement à l’assainissement collectif : aucune source ouverte à l’adresse"
  }
}
```

### `GET /communes/:insee/water-quality`

Historique d’un paramètre (`parameter` = code SANDRE : 1340, 6276, 1345, 8847, 9268).

**Requête**

```http
GET /api/communes/80021/water-quality?parameter=1340
```

**Réponse** `200`

```json
[
  {
    "sourceCode": "hubeau_eau_potable",
    "fetchedAt": "2026-10-01T23:55:50.790Z",
    "expiresAt": "2026-10-08T23:55:50.790Z",
    "id": 207,
    "inseeCode": "80021",
    "sampleCode": "08000121806",
    "parameterCode": "1340",
    "parameterLabel": "Nitrates (en NO3)",
    "resultNumeric": 30.1,
    "resultText": "30,1",
    "unit": "mg/L",
    "qualityLimit": "<=50 mg/L",
    "sampledAt": "2023-10-19T08:51:00.000Z",
    "networkName": "AMIENS UDI",
    "distributor": "AMIENS METROPOLE",
    "physchemCompliance": "C",
    "bacterioCompliance": "C",
    "conclusion": "Eau d'alimentation conforme aux exigences de qualité en vigueur pour l'ensemble des paramètres mesurés."
  },
  {
    "sourceCode": "hubeau_eau_potable",
    "fetchedAt": "2026-10-01T23:55:50.790Z",
    "expiresAt": "2026-10-08T23:55:50.790Z",
    "id": 205,
    "inseeCode": "80021",
    "sampleCode": "08000121808",
    "parameterCode": "1340",
    "parameterLabel": "Nitrates (en NO3)",
    "resultNumeric": 34.2,
    "resultText": "34,2",
    "unit": "mg/L",
    "qualityLimit": "<=50 mg/L",
    "sampledAt": "2023-10-19T10:01:00.000Z",
    "networkName": "AMIENS UDI",
    "distributor": "AMIENS METROPOLE",
    "physchemCompliance": "C",
    "bacterioCompliance": "C",
    "conclusion": "Eau d'alimentation conforme aux exigences de qualité en vigueur pour l'ensemble des paramètres mesurés."
  },
  {
    "sourceCode": "hubeau_eau_potable",
    "fetchedAt": "2026-10-01T23:55:50.790Z",
    "expiresAt": "2026-10-08T23:55:50.790Z",
    "id": 203,
    "inseeCode": "80021",
    "sampleCode": "08000121807",
    "parameterCode": "1340",
    "parameterLabel": "Nitrates (en NO3)",
    "resultNumeric": 29.4,
    "resultText": "29,4",
    "unit": "mg/L",
    "qualityLimit": "<=50 mg/L",
    "sampledAt": "2023-10-19T10:15:00.000Z",
    "networkName": "AMIENS UDI",
    "distributor": "AMIENS METROPOLE",
    "physchemCompliance": "C",
    "bacterioCompliance": "C",
    "conclusion": "Eau d'alimentation conforme aux exigences de qualité en vigueur pour l'ensemble des paramètres mesurés."
  },
  "… (107 éléments)"
]
```

## Climat, air, soleil

### `POST /addresses/:id/climate/collect`

Collecte climat observé (10 ans), projections 2041-2050, PVGIS, Atmo.

**Requête**

```http
POST /api/addresses/1/climate/collect
```

**Réponse** `201`

```json
[
  {
    "source": "open_meteo_archive",
    "target": "address:1",
    "status": "cached",
    "items": 10,
    "fetchedAt": "2026-10-01T23:55:50.795Z",
    "expiresAt": "2027-10-01T23:55:50.795Z"
  },
  {
    "source": "open_meteo_climate",
    "target": "address:1",
    "status": "cached",
    "items": 30,
    "fetchedAt": "2026-10-01T23:55:50.797Z",
    "expiresAt": "2027-10-01T23:55:50.797Z"
  },
  {
    "source": "pvgis",
    "target": "address:1",
    "status": "cached",
    "items": 1,
    "fetchedAt": "2026-10-01T23:55:50.778Z",
    "expiresAt": "2027-10-01T23:55:50.778Z"
  },
  "… (4 éléments)"
]
```

### `GET /addresses/:id/climate`

Gel, nuits tropicales, neige, vent, ensoleillement, projections multi-modèles, solaire, air/pollens.

**Requête**

```http
GET /api/addresses/1/climate
```

**Réponse** `200`

```json
{
  "observed": {
    "frost_days_per_year": {
      "value": 33.6,
      "unit": "jours/an"
    },
    "hot_days_per_year": {
      "value": 6.5,
      "unit": "jours/an"
    },
    "precipitation_per_year": {
      "value": 767.2,
      "unit": "mm/an"
    },
    "severe_frost_days_per_year": {
      "value": 2.4,
      "unit": "jours/an"
    },
    "snow_days_per_year": {
      "value": 2.4,
      "unit": "jours/an"
    },
    "snowfall_per_year": {
      "value": 9.5,
      "unit": "cm/an"
    },
    "strong_wind_days_per_year": {
      "value": 5,
      "unit": "jours/an"
    },
    "sunshine_hours_per_year": {
      "value": 2866.6,
      "unit": "h/an"
    },
    "tropical_nights_per_year": {
      "value": 1.5,
      "unit": "nuits/an"
    },
    "winter_sunshine_hours": {
      "value": 363.4,
      "unit": "h/hiver"
    }
  },
  "observedMeta": {
    "period": "2016-2025",
    "gridLat": 49.876976,
    "gridLon": 2.347826,
    "elevation": 37
  },
  "projections2050": {
    "models": [
      "MRI_AGCM3_2_S",
      "CMCC_CM2_VHR4",
      "… (3 éléments)"
    ],
    "ensemble": {
      "mean_tmax": {
        "2005-2014": 14.7,
        "2041-2050": 16.3,
        "change": 1.6
      },
      "hot_days_per_year": {
        "2005-2014": 7.3,
        "2041-2050": 15.1,
        "change": 7.8
      },
      "tropical_nights_per_year": {
        "2005-2014": 2.3,
        "2041-2050": 7.3,
        "change": 5
      },
      "frost_days_per_year": {
        "2005-2014": 33.7,
        "2041-2050": 18.8,
        "change": -14.9
      },
      "precipitation_per_year": {
        "2005-2014": 735.9,
        "2041-2050": 717.6,
        "change": -18.3
      }
    },
    "perModel": [
      {
        "sourceCode": "open_meteo_climate",
        "fetchedAt": "2026-10-01T23:55:50.797Z",
        "expiresAt": "2027-10-01T23:55:50.797Z",
        "id": 1,
        "addressId": 1,
        "model": "MRI_AGCM3_2_S",
        "period": "2005-2014",
        "indicator": "mean_tmax",
        "value": 14.4,
        "unit": "°C"
      },
      {
        "sourceCode": "open_meteo_climate",
        "fetchedAt": "2026-10-01T23:55:50.797Z",
        "expiresAt": "2027-10-01T23:55:50.797Z",
        "id": 2,
        "addressId": 1,
        "model": "MRI_AGCM3_2_S",
        "period": "2005-2014",
        "indicator": "hot_days_per_year",
        "value": 7.5,
        "unit": "jours/an"
      },
      "… (30 éléments)"
    ]
  },
  "solar": {
    "sourceCode": "pvgis",
    "fetchedAt": "2026-10-01T23:55:50.778Z",
    "expiresAt": "2027-10-01T23:55:50.778Z",
    "id": 1,
    "addressId": 1,
    "tiltDeg": 39,
    "azimuthDeg": -2,
    "yearlyKwhPerKwp": 1111.8,
    "yearlyIrradiationKwhM2": 1379.23,
    "winterKwhPerKwp": 143.18,
    "monthly": [
      {
        "month": 1,
        "kwh": 41.83,
        "irradiation": 48.68
      },
      {
        "month": 2,
        "kwh": 61.6,
        "irradiation": 72.02
      },
      "… (12 éléments)"
    ]
  },
  "airQuality": [],
  "pollens": [],
  "caveats": [
    "Réanalyse ERA5 (maille ~10 km) : l’îlot de chaleur urbain et les effets de relief local sont lissés.",
    "sunshine_duration ERA5 surestime nettement l’ensoleillement mesuré par héliographe : à utiliser en comparaison entre adresses, pas en valeur absolue."
  ],
  "notCovered": [
    "Brouillard (pas de climatologie ouverte à l’adresse)",
    "Masques solaires dus aux bâtiments voisins"
  ]
}
```

## Nuisances

### `POST /addresses/:id/nuisances/collect`

Collecte OSM (Overpass), plans d’exposition au bruit (WFS), survols (OpenSky). `radius` en mètres.

**Requête**

```http
POST /api/addresses/1/nuisances/collect?radius=1000
```

**Réponse** `201`

```json
[
  {
    "source": "overpass",
    "target": "address:1:r1000",
    "status": "cached",
    "items": 194,
    "fetchedAt": "2026-10-01T23:55:50.781Z",
    "expiresAt": "2026-10-31T23:55:50.781Z"
  },
  {
    "source": "geopf_wfs",
    "target": "address:1:peb",
    "status": "cached",
    "items": 2,
    "fetchedAt": "2026-10-01T23:55:59.075Z",
    "expiresAt": "2026-12-30T23:55:59.075Z"
  },
  {
    "source": "opensky",
    "target": "address:1",
    "status": "cached",
    "items": 0,
    "fetchedAt": "2026-10-01T23:55:59.272Z",
    "expiresAt": "2026-10-02T00:10:59.272Z"
  }
]
```

### `GET /addresses/:id/nuisances`

Nuisances par catégorie (nombre, plus proche), lignes HT, antennes, PEB, survols.

**Requête**

```http
GET /api/addresses/1/nuisances?radius=1000
```

**Réponse** `200`

```json
{
  "radiusM": 1000,
  "summary": {
    "nightlife": {
      "count": 78,
      "nearestM": 51,
      "nearest": {
        "name": "Le Piccadilly",
        "subcategory": "bar",
        "distanceM": 51
      }
    },
    "place_of_worship": {
      "count": 17,
      "nearestM": 105,
      "nearest": {
        "name": "Église Saint-Remi",
        "subcategory": "place_of_worship",
        "distanceM": 105
      }
    },
    "marketplace": {
      "count": 5,
      "nearestM": 287,
      "nearest": {
        "name": "Marché Hebdomadaire",
        "subcategory": "marketplace",
        "distanceM": 287
      }
    },
    "concert_venue": {
      "count": 10,
      "nearestM": 393,
      "nearest": {
        "name": "La Comédie de Picardie",
        "subcategory": "theatre",
        "distanceM": 393
      }
    },
    "railway": {
      "count": 71,
      "nearestM": 494,
      "nearest": {
        "name": "Ligne de Longueau à Boulogne-Ville",
        "subcategory": "25 kV",
        "distanceM": 494
      }
    },
    "power_line": {
      "count": 12,
      "nearestM": 2121,
      "nearest": {
        "name": null,
        "subcategory": "20 kV",
        "distanceM": 2121
      }
    }
  },
  "powerLines": [
    {
      "sourceCode": "overpass",
      "fetchedAt": "2026-10-01T23:55:50.781Z",
      "expiresAt": "2026-10-31T23:55:50.781Z",
      "id": 42,
      "externalId": "osm:way/621582981",
      "category": "power_line",
      "subcategory": "20 kV",
      "name": null,
      "tags": {
        "operator": "Enedis",
        "voltage": "20000"
      },
      "distanceM": 2121
    },
    {
      "sourceCode": "overpass",
      "fetchedAt": "2026-10-01T23:55:50.781Z",
      "expiresAt": "2026-10-31T23:55:50.781Z",
      "id": 45,
      "externalId": "osm:way/621582995",
      "category": "power_line",
      "subcategory": "225 kV",
      "name": null,
      "tags": {
        "operator": "RTE",
        "voltage": "225000"
      },
      "distanceM": 2127
    },
    "… (5 éléments)"
  ],
  "mobileAntennas": [
    {
      "sourceCode": "arcep_mobile",
      "fetchedAt": "2026-10-01T23:55:52.932Z",
      "expiresAt": "2026-12-30T23:55:52.932Z",
      "operatorCode": "20801",
      "siteNumber": "00029500A1",
      "operatorName": "Orange",
      "anfrStationId": "802290240",
      "inseeCode": "80021",
      "has2g": false,
      "has3g": false,
      "has4g": true,
      "has5g": false,
      "has5g3500": false,
      "latitude": 49.8925,
      "longitude": 2.29945,
      "distanceM": 173
    },
    {
      "sourceCode": "arcep_mobile",
      "fetchedAt": "2026-10-01T23:55:52.932Z",
      "expiresAt": "2026-12-30T23:55:52.932Z",
      "operatorCode": "20810",
      "siteNumber": "800662",
      "operatorName": "SFR",
      "anfrStationId": "802700150",
      "inseeCode": "80021",
      "has2g": true,
      "has3g": true,
      "has4g": true,
      "has5g": false,
      "has5g3500": false,
      "latitude": 49.89207,
      "longitude": 2.3,
      "distanceM": 224
    },
    "… (12 éléments)"
  ],
  "airportNoisePlans": [
    {
      "sourceCode": "geopf_wfs",
      "fetchedAt": "2026-10-01T23:55:59.075Z",
      "expiresAt": "2026-12-30T23:55:59.075Z",
      "id": 112,
      "externalId": "peb:LFAY",
      "category": "airport_noise_plan",
      "subcategory": "LFAY",
      "name": "LFAY - AMIENS",
      "tags": {
        "arrete": "http://piece-jointe-carto.developpement-durable.gouv.fr/NAT003/PEB/PEB_LFAY_01_12_1982.pdf"
      },
      "latitude": 49.873104,
      "longitude": 2.386986,
      "distanceM": 6804
    },
    {
      "sourceCode": "geopf_wfs",
      "fetchedAt": "2026-10-01T23:55:59.075Z",
      "expiresAt": "2026-12-30T23:55:59.075Z",
      "id": 113,
      "externalId": "peb:LFAQ",
      "category": "airport_noise_plan",
      "subcategory": "LFAQ",
      "name": "LFAQ - ALBERT",
      "tags": {
        "arrete": "http://piece-jointe-carto.developpement-durable.gouv.fr/NAT003/PEB/PEB_LFAQ_05_10_2005.pdf"
      },
      "latitude": 49.970062,
      "longitude": 2.692617,
      "distanceM": 29585
    }
  ],
  "flights": {
    "snapshotAt": null,
    "aircraftWithin15km": 0,
    "lowestAltitudeM": null,
    "closest": [],
    "note": "Instantané OpenSky : à échantillonner dans le temps pour estimer un couloir aérien"
  },
  "notCovered": [
    "Pollution lumineuse",
    "Livraisons et fret de nuit",
    "… (4 éléments)"
  ]
}
```

## Énergie

### `POST /addresses/:id/energy/collect`

Collecte réseau de chaleur (FCU), desserte gaz (GRDF), consommation électrique (Enedis).

**Requête**

```http
POST /api/addresses/1/energy/collect
```

**Réponse** `201`

```json
[
  {
    "source": "fcu",
    "target": "address:1",
    "status": "cached",
    "items": 1,
    "fetchedAt": "2026-10-01T23:55:50.783Z",
    "expiresAt": "2026-10-31T23:55:50.783Z"
  },
  {
    "source": "grdf",
    "target": "address:1",
    "status": "cached",
    "items": 5,
    "fetchedAt": "2026-10-01T23:55:50.799Z",
    "expiresAt": "2026-12-30T23:55:50.799Z"
  },
  {
    "source": "enedis",
    "target": "address:1",
    "status": "cached",
    "items": 1,
    "fetchedAt": "2026-10-01T23:55:50.801Z",
    "expiresAt": "2026-12-30T23:55:50.801Z"
  }
]
```

### `GET /addresses/:id/energy`

Réseaux disponibles et consommation résidentielle (adresse ou moyenne communale).

**Requête**

```http
GET /api/addresses/1/energy
```

**Réponse** `200`

```json
{
  "heatNetwork": {
    "sourceCode": "fcu",
    "fetchedAt": "2026-10-01T23:55:50.783Z",
    "expiresAt": "2026-10-31T23:55:50.783Z",
    "id": 1,
    "addressId": 1,
    "networkType": "heat",
    "available": true,
    "distanceM": 164,
    "operatorName": "Amiens Energies (ENGIE SOLUTIONS)",
    "networkName": "Réseau de la ville d'Amiens",
    "details": {
      "networkId": "8002C",
      "renewableRate": 53.4,
      "co2Rate": 0.124,
      "futureNetwork": false,
      "priorityZone": true
    }
  },
  "gasNetwork": {
    "sourceCode": "grdf",
    "fetchedAt": "2026-10-01T23:55:50.799Z",
    "expiresAt": "2026-12-30T23:55:50.799Z",
    "id": 2,
    "addressId": 1,
    "networkType": "gas",
    "available": true,
    "distanceM": null,
    "operatorName": "GRDF",
    "networkName": null,
    "details": {
      "scope": "commune",
      "propane": null,
      "note": "Commune desservie par GRDF ; le raccordement du logement n’est pas publié"
    }
  },
  "electricity": {
    "atAddress": [],
    "communeAverage": [
      {
        "sourceCode": "enedis",
        "fetchedAt": "2026-10-01T23:55:50.801Z",
        "expiresAt": "2026-12-30T23:55:50.801Z",
        "id": 1,
        "inseeCode": "80021",
        "addressKey": "__COMMUNE__",
        "year": 2024,
        "irisCode": null,
        "dwellings": null,
        "totalMwh": null,
        "avgPerSiteMwh": null,
        "communeAvgMwh": 2.619
      }
    ]
  },
  "notCovered": [
    "Historique des coupures électriques à l’adresse"
  ]
}
```

## Services, santé, éducation

### `POST /addresses/:id/services/collect`

Collecte établissements (Recherche d’entreprises, OSM), écoles, temps de trajet IGN.

**Requête**

```http
POST /api/addresses/1/services/collect
```

**Réponse** `201`

```json
[
  {
    "source": "recherche_entreprises",
    "target": "address:1",
    "status": "cached",
    "items": 96,
    "fetchedAt": "2026-10-01T23:55:50.803Z",
    "expiresAt": "2026-10-31T23:55:50.803Z"
  },
  {
    "source": "overpass",
    "target": "address:1:services",
    "status": "cached",
    "items": 70,
    "fetchedAt": "2026-10-01T23:55:50.804Z",
    "expiresAt": "2026-10-31T23:55:50.804Z"
  },
  {
    "source": "education",
    "target": "address:1",
    "status": "cached",
    "items": 56,
    "fetchedAt": "2026-10-01T23:55:50.805Z",
    "expiresAt": "2026-12-30T23:55:50.805Z"
  },
  "… (6 éléments)"
]
```

### `GET /addresses/:id/services`

Services par catégorie, urgences, boulangeries ouvertes le dimanche, temps de trajet.

**Requête**

```http
GET /api/addresses/1/services
```

**Réponse** `200`

```json
{
  "byCategory": {
    "bakery": {
      "countWithin2km": 51,
      "nearest": [
        {
          "sourceCode": "overpass",
          "fetchedAt": "2026-10-01T23:55:50.804Z",
          "expiresAt": "2026-10-31T23:55:50.804Z",
          "id": 154,
          "externalId": "osm:node/11917606769",
          "category": "bakery",
          "name": "Mamatte Boulangerie Café",
          "addressLabel": "2 Place Gambetta Amiens",
          "inseeCode": null,
          "openingHours": "Mo-Sa 07:00-20:00; Su 07:30-19:00",
          "details": {
            "opensOnSunday": true,
            "operator": null
          },
          "latitude": 49.892939,
          "longitude": 2.297318,
          "distanceM": 22
        },
        {
          "sourceCode": "overpass",
          "fetchedAt": "2026-10-01T23:55:50.804Z",
          "expiresAt": "2026-10-31T23:55:50.804Z",
          "id": 145,
          "externalId": "osm:node/4857531131",
          "category": "bakery",
          "name": "La Mie Câline",
          "addressLabel": "1 bis Place Gambetta Amiens",
          "inseeCode": null,
          "openingHours": "Mo-Sa 07:30-19:45; Su off",
          "details": {
            "opensOnSunday": false,
            "operator": null
          },
          "latitude": 49.893017,
          "longitude": 2.297038,
          "distanceM": 23
        },
        "… (3 éléments)"
      ]
    },
    "childcare": {
      "countWithin2km": 18,
      "nearest": [
        {
          "sourceCode": "recherche_entreprises",
          "fetchedAt": "2026-10-01T23:55:50.803Z",
          "expiresAt": "2026-10-31T23:55:50.803Z",
          "id": 26,
          "externalId": "siret:83809878800030",
          "category": "childcare",
          "name": "HESTIA HZ",
          "addressLabel": "7 RUE DES CORDELIERS 80000 AMIENS",
          "inseeCode": "80021",
          "openingHours": null,
          "details": {
            "siret": "83809878800030",
            "naf": "88.91A",
            "createdAt": "2018-10-29"
          },
          "latitude": 49.892357,
          "longitude": 2.295597,
          "distanceM": 118
        },
        {
          "sourceCode": "recherche_entreprises",
          "fetchedAt": "2026-10-01T23:55:50.803Z",
          "expiresAt": "2026-10-31T23:55:50.803Z",
          "id": 4,
          "externalId": "siret:52337105200417",
          "category": "childcare",
          "name": "KINOUGARDE",
          "addressLabel": "18 PLACE DE L'HOTEL DE VILLE 80000 AMIENS",
          "inseeCode": "80021",
          "openingHours": null,
          "details": {
            "siret": "52337105200417",
            "naf": "88.91A",
            "createdAt": "2023-04-03"
          },
          "latitude": 49.892916,
          "longitude": 2.295185,
          "distanceM": 137
        },
        "… (3 éléments)"
      ]
    },
    "general_practitioner": {
      "countWithin2km": 51,
      "nearest": [
        {
          "sourceCode": "recherche_entreprises",
          "fetchedAt": "2026-10-01T23:55:50.803Z",
          "expiresAt": "2026-10-31T23:55:50.803Z",
          "id": 87,
          "externalId": "siret:51829092900026",
          "category": "general_practitioner",
          "name": "CRISTINA SMETANCA",
          "addressLabel": "12 RUE DUSEVEL 80000 AMIENS",
          "inseeCode": "80021",
          "openingHours": null,
          "details": {
            "siret": "51829092900026",
            "naf": "86.21Z",
            "createdAt": "2019-07-11"
          },
          "latitude": 49.894242,
          "longitude": 2.299496,
          "distanceM": 235
        },
        {
          "sourceCode": "recherche_entreprises",
          "fetchedAt": "2026-10-01T23:55:50.803Z",
          "expiresAt": "2026-10-31T23:55:50.803Z",
          "id": 51,
          "externalId": "siret:98207610100012",
          "category": "general_practitioner",
          "name": "THIBAUT DEHEDIN",
          "addressLabel": "APPARTEMENT 2 8 RUE ALBERT ROZE 80000 AMIENS",
          "inseeCode": "80021",
          "openingHours": null,
          "details": {
            "siret": "98207610100012",
            "naf": "86.21Z",
            "createdAt": "2023-12-01"
          },
          "latitude": 49.891956,
          "longitude": 2.293455,
          "distanceM": 277
        },
        "… (3 éléments)"
      ]
    },
    "hospital": {
      "countWithin2km": 3,
      "nearest": [
        {
          "sourceCode": "recherche_entreprises",
          "fetchedAt": "2026-10-01T23:55:50.803Z",
          "expiresAt": "2026-10-31T23:55:50.803Z",
          "id": 5,
          "externalId": "siret:26800029600114",
          "category": "hospital",
          "name": "CMP 80I01 PEDOPSYCHIATRIE",
          "addressLabel": "2 PLACE AU FEURRE 80000 AMIENS",
          "inseeCode": "80021",
          "openingHours": null,
          "details": {
            "siret": "26800029600114",
            "naf": "86.10Z",
            "createdAt": "1995-01-01"
          },
          "latitude": 49.896807,
          "longitude": 2.298176,
          "distanceM": 451
        },
        {
          "sourceCode": "recherche_entreprises",
          "fetchedAt": "2026-10-01T23:55:50.803Z",
          "expiresAt": "2026-10-31T23:55:50.803Z",
          "id": 6,
          "externalId": "siret:26800014800042",
          "category": "hospital",
          "name": "CENTRE GYNECOLOGIE OBSTETRIQUE",
          "addressLabel": "124 RUE CAMILLE DESMOULINS 80000 AMIENS",
          "inseeCode": "80021",
          "openingHours": null,
          "details": {
            "siret": "26800014800042",
            "naf": "86.10Z",
            "createdAt": "1983-12-01"
          },
          "latitude": 49.881719,
          "longitude": 2.300705,
          "distanceM": 1260
        },
        "… (3 éléments)"
      ]
    },
    "pharmacy": {
      "countWithin2km": 33,
      "nearest": [
        {
          "sourceCode": "overpass",
          "fetchedAt": "2026-10-01T23:55:50.804Z",
          "expiresAt": "2026-10-31T23:55:50.804Z",
          "id": 101,
          "externalId": "osm:node/1229685381",
          "category": "pharmacy",
          "name": "Pharmacie Lafayette",
          "addressLabel": "4 Place Gambetta Amiens",
          "inseeCode": null,
          "openingHours": "Mo-Sa 09:00-19:30",
          "details": {
            "opensOnSunday": false,
            "operator": null
          },
          "latitude": 49.893164,
          "longitude": 2.297816,
          "distanceM": 66
        },
        {
          "sourceCode": "overpass",
          "fetchedAt": "2026-10-01T23:55:50.804Z",
          "expiresAt": "2026-10-31T23:55:50.804Z",
          "id": 116,
          "externalId": "osm:node/3100404842",
          "category": "pharmacy",
          "name": "Pharmacie de l'Hotel de Ville",
          "addressLabel": "18 Rue de Beauvais",
          "inseeCode": null,
          "openingHours": "Mo-Fr 09:00-19:00; Sa 09:00-18:00; Su off",
          "details": {
            "opensOnSunday": false,
            "operator": null
          },
          "latitude": 49.893042,
          "longitude": 2.294107,
          "distanceM": 215
        },
        "… (3 éléments)"
      ]
    },
    "supermarket": {
      "countWithin2km": 6,
      "nearest": [
        {
          "sourceCode": "recherche_entreprises",
          "fetchedAt": "2026-10-01T23:55:50.803Z",
          "expiresAt": "2026-10-31T23:55:50.803Z",
          "id": 52,
          "externalId": "siret:91909694100035",
          "category": "supermarket",
          "name": "CARREFOUR CITY",
          "addressLabel": "13 RUE DES VERGEAUX 80000 AMIENS",
          "inseeCode": "80021",
          "openingHours": null,
          "details": {
            "siret": "91909694100035",
            "naf": "47.11D",
            "createdAt": "2024-06-07"
          },
          "latitude": 49.8949,
          "longitude": 2.297446,
          "distanceM": 234
        },
        {
          "sourceCode": "recherche_entreprises",
          "fetchedAt": "2026-10-01T23:55:50.803Z",
          "expiresAt": "2026-10-31T23:55:50.803Z",
          "id": 10,
          "externalId": "siret:48226545100054",
          "category": "supermarket",
          "name": "RIVERY EXPLOITATION",
          "addressLabel": "12-16 RUE GRESSET 80000 AMIENS",
          "inseeCode": "80021",
          "openingHours": null,
          "details": {
            "siret": "48226545100054",
            "naf": "47.11D",
            "createdAt": "2023-02-01"
          },
          "latitude": 49.894113,
          "longitude": 2.294086,
          "distanceM": 259
        },
        "… (3 éléments)"
      ]
    }
  },
  "emergency": [
    {
      "sourceCode": "overpass",
      "fetchedAt": "2026-10-01T23:55:50.804Z",
      "expiresAt": "2026-10-31T23:55:50.804Z",
      "id": 166,
      "externalId": "osm:relation/8271449",
      "category": "emergency",
      "name": "Clinique de l'Europe",
      "addressLabel": null,
      "inseeCode": null,
      "openingHours": "24/7",
      "details": {
        "opensOnSunday": true,
        "operator": null
      },
      "latitude": 49.87083,
      "longitude": 2.295548,
      "distanceM": 2446
    },
    {
      "sourceCode": "overpass",
      "fetchedAt": "2026-10-01T23:55:50.804Z",
      "expiresAt": "2026-10-31T23:55:50.804Z",
      "id": 163,
      "externalId": "osm:way/332382649",
      "category": "emergency",
      "name": "Hôpital Psychiatrique Philippe Pinel",
      "addressLabel": "74410 Route d'Amiens Amiens",
      "inseeCode": null,
      "openingHours": null,
      "details": {
        "opensOnSunday": null,
        "operator": null
      },
      "latitude": 49.870509,
      "longitude": 2.275593,
      "distanceM": 2919
    },
    "… (3 éléments)"
  ],
  "sundayBakeries": [
    {
      "sourceCode": "overpass",
      "fetchedAt": "2026-10-01T23:55:50.804Z",
      "expiresAt": "2026-10-31T23:55:50.804Z",
      "id": 154,
      "externalId": "osm:node/11917606769",
      "category": "bakery",
      "name": "Mamatte Boulangerie Café",
      "addressLabel": "2 Place Gambetta Amiens",
      "inseeCode": null,
      "openingHours": "Mo-Sa 07:00-20:00; Su 07:30-19:00",
      "details": {
        "opensOnSunday": true,
        "operator": null
      },
      "latitude": 49.892939,
      "longitude": 2.297318,
      "distanceM": 22
    },
    {
      "sourceCode": "overpass",
      "fetchedAt": "2026-10-01T23:55:50.804Z",
      "expiresAt": "2026-10-31T23:55:50.804Z",
      "id": 137,
      "externalId": "osm:node/3902535180",
      "category": "bakery",
      "name": "Les Saveurs du Pain",
      "addressLabel": "9 Rue du Maréchal de Lattre de Tassigny",
      "inseeCode": null,
      "openingHours": "Mo-Su 06:30-21:00",
      "details": {
        "opensOnSunday": true,
        "operator": null
      },
      "latitude": 49.892036,
      "longitude": 2.2924,
      "distanceM": 347
    },
    "… (5 éléments)"
  ],
  "travelTimes": [
    {
      "sourceCode": "ign_navigation",
      "fetchedAt": "2026-10-01T23:56:51.281Z",
      "expiresAt": "2026-10-31T23:56:51.281Z",
      "id": 5,
      "addressId": 1,
      "destinationKind": "nearest_emergency",
      "profile": "car",
      "destinationLabel": "Clinique de l'Europe",
      "destinationLat": 49.87083,
      "destinationLon": 2.295548,
      "durationS": 659,
      "distanceM": 2891
    },
    {
      "sourceCode": "ign_navigation",
      "fetchedAt": "2026-10-01T23:56:51.281Z",
      "expiresAt": "2026-10-31T23:56:51.281Z",
      "id": 1,
      "addressId": 1,
      "destinationKind": "nearest_general_practitioner",
      "profile": "car",
      "destinationLabel": "CRISTINA SMETANCA",
      "destinationLat": 49.894242,
      "destinationLon": 2.299496,
      "durationS": 228,
      "distanceM": 1115
    },
    "… (5 éléments)"
  ],
  "schools": [
    {
      "sourceCode": "education",
      "fetchedAt": "2026-10-01T23:55:50.805Z",
      "expiresAt": "2026-12-30T23:55:50.805Z",
      "uai": "0801479Y",
      "name": "Lycée Saint-Rémi",
      "schoolType": "Lycée",
      "natureLabel": "LYCEE ENSEIGNT GENERAL ET TECHNOLOGIQUE",
      "sector": "Privé",
      "inseeCode": "80021",
      "hasPreschool": null,
      "hasElementary": null,
      "hasCanteen": true,
      "priorityEducation": null,
      "ips": null,
      "ipsSchoolYear": null,
      "classesCount": null,
      "studentsCount": null,
      "avgClassSize": null,
      "headcountYear": null,
      "latitude": 49.893842,
      "longitude": 2.298264,
      "distanceM": 143
    },
    {
      "sourceCode": "education",
      "fetchedAt": "2026-10-01T23:55:50.805Z",
      "expiresAt": "2026-12-30T23:55:50.805Z",
      "uai": "0801950K",
      "name": "Lycée professionnel Saint-Rémi",
      "schoolType": "Lycée",
      "natureLabel": "LYCEE PROFESSIONNEL",
      "sector": "Privé",
      "inseeCode": "80021",
      "hasPreschool": null,
      "hasElementary": null,
      "hasCanteen": true,
      "priorityEducation": null,
      "ips": null,
      "ipsSchoolYear": null,
      "classesCount": null,
      "studentsCount": null,
      "avgClassSize": null,
      "headcountYear": null,
      "latitude": 49.893842,
      "longitude": 2.298264,
      "distanceM": 143
    },
    "… (56 éléments)"
  ],
  "indicators": [],
  "notCovered": [
    "Médecins acceptant de nouveaux patients",
    "Pharmacie de garde",
    "… (5 éléments)"
  ]
}
```

### `GET /addresses/:id/schools`

Établissements scolaires proches avec IPS et taille moyenne des classes.

**Requête**

```http
GET /api/addresses/1/schools?radius=600
```

**Réponse** `200`

```json
[
  {
    "sourceCode": "education",
    "fetchedAt": "2026-10-01T23:55:50.805Z",
    "expiresAt": "2026-12-30T23:55:50.805Z",
    "uai": "0801479Y",
    "name": "Lycée Saint-Rémi",
    "schoolType": "Lycée",
    "natureLabel": "LYCEE ENSEIGNT GENERAL ET TECHNOLOGIQUE",
    "sector": "Privé",
    "inseeCode": "80021",
    "hasPreschool": null,
    "hasElementary": null,
    "hasCanteen": true,
    "priorityEducation": null,
    "ips": null,
    "ipsSchoolYear": null,
    "classesCount": null,
    "studentsCount": null,
    "avgClassSize": null,
    "headcountYear": null,
    "latitude": 49.893842,
    "longitude": 2.298264,
    "distanceM": 143
  },
  {
    "sourceCode": "education",
    "fetchedAt": "2026-10-01T23:55:50.805Z",
    "expiresAt": "2026-12-30T23:55:50.805Z",
    "uai": "0801950K",
    "name": "Lycée professionnel Saint-Rémi",
    "schoolType": "Lycée",
    "natureLabel": "LYCEE PROFESSIONNEL",
    "sector": "Privé",
    "inseeCode": "80021",
    "hasPreschool": null,
    "hasElementary": null,
    "hasCanteen": true,
    "priorityEducation": null,
    "ips": null,
    "ipsSchoolYear": null,
    "classesCount": null,
    "studentsCount": null,
    "avgClassSize": null,
    "headcountYear": null,
    "latitude": 49.893842,
    "longitude": 2.298264,
    "distanceM": 143
  },
  {
    "sourceCode": "education",
    "fetchedAt": "2026-10-01T23:55:50.805Z",
    "expiresAt": "2026-12-30T23:55:50.805Z",
    "uai": "0801208D",
    "name": "Collège Sainte-Clotilde",
    "schoolType": "Collège",
    "natureLabel": "COLLEGE",
    "sector": "Privé",
    "inseeCode": "80021",
    "hasPreschool": null,
    "hasElementary": null,
    "hasCanteen": true,
    "priorityEducation": null,
    "ips": 124.3,
    "ipsSchoolYear": "2025-2026",
    "classesCount": null,
    "studentsCount": null,
    "avgClassSize": null,
    "headcountYear": null,
    "latitude": 49.890137,
    "longitude": 2.300203,
    "distanceM": 372
  },
  "… (12 éléments)"
]
```

## Socio-démographie, fiscalité, sécurité

### `POST /communes/:insee/socio/collect`

Collecte recensement (Melodi), fiscalité locale (DGFiP), délinquance (SSMSI).

**Requête**

```http
POST /api/communes/80021/socio/collect
```

**Réponse** `201`

```json
[
  {
    "source": "insee_melodi",
    "target": "commune:80021",
    "status": "cached",
    "items": 33,
    "fetchedAt": "2026-10-01T23:55:50.822Z",
    "expiresAt": "2027-03-30T23:55:50.822Z"
  },
  {
    "source": "fiscalite_locale",
    "target": "commune:80021",
    "status": "cached",
    "items": 5,
    "fetchedAt": "2026-10-01T23:55:50.821Z",
    "expiresAt": "2027-03-30T23:55:50.821Z"
  },
  {
    "source": "ssmsi",
    "target": "commune:80021",
    "status": "cached",
    "items": 150,
    "fetchedAt": "2026-10-01T23:55:50.823Z",
    "expiresAt": "2027-03-30T23:55:50.823Z"
  }
]
```

### `GET /communes/:insee/socio`

Démographie (séries + dernière valeur), taxes et évolution, délinquance.

**Requête**

```http
GET /api/communes/80021/socio
```

**Réponse** `200`

```json
{
  "demography": {
    "latest": {
      "dwellings_total": {
        "year": 2023,
        "value": 79419,
        "unit": "logements"
      },
      "mean_age_estimated": {
        "year": 2023,
        "value": 37.7,
        "unit": "ans"
      },
      "mean_length_of_stay": {
        "year": 2023,
        "value": 11.4,
        "unit": "ans"
      },
      "population": {
        "year": 2023,
        "value": 136449,
        "unit": "habitants"
      },
      "secondary_homes": {
        "year": 2023,
        "value": 2213,
        "unit": "logements"
      },
      "share_65_plus": {
        "year": 2023,
        "value": 16.2,
        "unit": "%"
      },
      "share_moved_in_last_2_years": {
        "year": 2023,
        "value": 19.14,
        "unit": "%"
      },
      "share_secondary_homes": {
        "year": 2023,
        "value": 2.79,
        "unit": "%"
      },
      "share_under_20": {
        "year": 2023,
        "value": 25.26,
        "unit": "%"
      },
      "share_vacant_dwellings": {
        "year": 2023,
        "value": 9.28,
        "unit": "%"
      },
      "vacant_dwellings": {
        "year": 2023,
        "value": 7373,
        "unit": "logements"
      }
    },
    "series": {
      "dwellings_total": [
        {
          "year": 2012,
          "value": 70076,
          "unit": "logements"
        },
        {
          "year": 2017,
          "value": 73541,
          "unit": "logements"
        },
        "… (3 éléments)"
      ],
      "mean_age_estimated": [
        {
          "year": 2012,
          "value": 36.7,
          "unit": "ans"
        },
        {
          "year": 2017,
          "value": 36.8,
          "unit": "ans"
        },
        "… (3 éléments)"
      ],
      "mean_length_of_stay": [
        {
          "year": 2012,
          "value": 11.6,
          "unit": "ans"
        },
        {
          "year": 2017,
          "value": 11.3,
          "unit": "ans"
        },
        "… (3 éléments)"
      ],
      "population": [
        {
          "year": 2012,
          "value": 132727,
          "unit": "habitants"
        },
        {
          "year": 2017,
          "value": 134057,
          "unit": "habitants"
        },
        "… (3 éléments)"
      ],
      "secondary_homes": [
        {
          "year": 2012,
          "value": 628,
          "unit": "logements"
        },
        {
          "year": 2017,
          "value": 1528,
          "unit": "logements"
        },
        "… (3 éléments)"
      ],
      "share_65_plus": [
        {
          "year": 2012,
          "value": 13.56,
          "unit": "%"
        },
        {
          "year": 2017,
          "value": 14.32,
          "unit": "%"
        },
        "… (3 éléments)"
      ],
      "share_moved_in_last_2_years": [
        {
          "year": 2012,
          "value": 20.91,
          "unit": "%"
        },
        {
          "year": 2017,
          "value": 21.17,
          "unit": "%"
        },
        "… (3 éléments)"
      ],
      "share_secondary_homes": [
        {
          "year": 2012,
          "value": 0.9,
          "unit": "%"
        },
        {
          "year": 2017,
          "value": 2.08,
          "unit": "%"
        },
        "… (3 éléments)"
      ],
      "share_under_20": [
        {
          "year": 2012,
          "value": 25.56,
          "unit": "%"
        },
        {
          "year": 2017,
          "value": 26.6,
          "unit": "%"
        },
        "… (3 éléments)"
      ],
      "share_vacant_dwellings": [
        {
          "year": 2012,
          "value": 8.87,
          "unit": "%"
        },
        {
          "year": 2017,
          "value": 9.19,
          "unit": "%"
        },
        "… (3 éléments)"
      ],
      "vacant_dwellings": [
        {
          "year": 2012,
          "value": 6219,
          "unit": "logements"
        },
        {
          "year": 2017,
          "value": 6762,
          "unit": "logements"
        },
        "… (3 éléments)"
      ]
    }
  },
  "taxes": {
    "history": [
      {
        "sourceCode": "fiscalite_locale",
        "fetchedAt": "2026-10-01T23:55:50.821Z",
        "expiresAt": "2027-03-30T23:55:50.821Z",
        "inseeCode": "80021",
        "year": 2021,
        "epciCode": "248000531",
        "propertyTaxRate": 55.87,
        "landTaxRate": 64.01,
        "wasteTaxRate": 8.53,
        "housingTaxRate": 32.78,
        "secondaryHomeSurcharge": false,
        "secondaryHomeSurchargeRate": null
      },
      {
        "sourceCode": "fiscalite_locale",
        "fetchedAt": "2026-10-01T23:55:50.821Z",
        "expiresAt": "2027-03-30T23:55:50.821Z",
        "inseeCode": "80021",
        "year": 2022,
        "epciCode": "248000531",
        "propertyTaxRate": 55.87,
        "landTaxRate": 62.98,
        "wasteTaxRate": 8.53,
        "housingTaxRate": 32.78,
        "secondaryHomeSurcharge": false,
        "secondaryHomeSurchargeRate": null
      },
      "… (5 éléments)"
    ],
    "propertyTaxRateChange": {
      "from": 2021,
      "to": 2025,
      "points": 0.13
    }
  },
  "crime": {
    "year": 2025,
    "highlights": [
      {
        "sourceCode": "ssmsi",
        "fetchedAt": "2026-10-01T23:55:50.823Z",
        "expiresAt": "2027-03-30T23:55:50.823Z",
        "id": 146,
        "inseeCode": "80021",
        "year": 2025,
        "indicator": "Destructions et dégradations volontaires",
        "countUnit": "Infraction",
        "count": 2042,
        "ratePerThousand": 14.9653,
        "isPublished": true
      },
      {
        "sourceCode": "ssmsi",
        "fetchedAt": "2026-10-01T23:55:50.823Z",
        "expiresAt": "2027-03-30T23:55:50.823Z",
        "id": 142,
        "inseeCode": "80021",
        "year": 2025,
        "indicator": "Cambriolages de logement",
        "countUnit": "Infraction",
        "count": 168,
        "ratePerThousand": 2.1381,
        "isPublished": true
      },
      "… (5 éléments)"
    ],
    "all": [
      {
        "sourceCode": "ssmsi",
        "fetchedAt": "2026-10-01T23:55:50.823Z",
        "expiresAt": "2027-03-30T23:55:50.823Z",
        "id": 1,
        "inseeCode": "80021",
        "year": 2016,
        "indicator": "Violences physiques intrafamiliales",
        "countUnit": "Victime",
        "count": 362,
        "ratePerThousand": 2.7064,
        "isPublished": true
      },
      {
        "sourceCode": "ssmsi",
        "fetchedAt": "2026-10-01T23:55:50.823Z",
        "expiresAt": "2027-03-30T23:55:50.823Z",
        "id": 15,
        "inseeCode": "80021",
        "year": 2016,
        "indicator": "Escroqueries et fraudes aux moyens de paiement",
        "countUnit": "Victime",
        "count": 559,
        "ratePerThousand": 4.1793,
        "isPublished": true
      },
      "… (150 éléments)"
    ]
  },
  "notCovered": [
    "Part de locations Airbnb (pas de donnée officielle)",
    "Vie associative (fichier RNA non interrogeable par API)"
  ]
}
```

## Mobilité

### `POST /addresses/:id/mobility/collect`

Collecte bornes IRVE, parkings, arrêts, aménagements cyclables, flux GTFS.

**Requête**

```http
POST /api/addresses/1/mobility/collect
```

**Réponse** `201`

```json
[
  {
    "source": "irve",
    "target": "commune:80021",
    "status": "cached",
    "items": 208,
    "fetchedAt": "2026-10-01T23:55:50.816Z",
    "expiresAt": "2026-10-08T23:55:50.816Z"
  },
  {
    "source": "bnls",
    "target": "commune:80021",
    "status": "cached",
    "items": 0,
    "fetchedAt": "2026-10-01T23:55:50.817Z",
    "expiresAt": "2026-10-31T23:55:50.817Z"
  },
  {
    "source": "overpass",
    "target": "address:1:mobility",
    "status": "cached",
    "items": 65,
    "fetchedAt": "2026-10-01T23:55:50.815Z",
    "expiresAt": "2026-10-31T23:55:50.815Z"
  },
  "… (4 éléments)"
]
```

### `GET /addresses/:id/mobility`

Arrêts à moins de 800 m, bornes, parkings, pistes cyclables, flux GTFS couvrant la commune.

**Requête**

```http
GET /api/addresses/1/mobility
```

**Réponse** `200`

```json
{
  "transit": {
    "stopsWithin800m": 65,
    "byMode": {
      "bus": [
        {
          "sourceCode": "overpass",
          "fetchedAt": "2026-10-01T23:55:50.815Z",
          "expiresAt": "2026-10-31T23:55:50.815Z",
          "externalId": "osm:node/2424967116",
          "name": "Hôtel de Ville",
          "mode": "bus",
          "network": null,
          "latitude": 49.892914,
          "longitude": 2.295433,
          "distanceM": 119
        },
        {
          "sourceCode": "overpass",
          "fetchedAt": "2026-10-01T23:55:50.815Z",
          "expiresAt": "2026-10-31T23:55:50.815Z",
          "externalId": "osm:node/2424971351",
          "name": "Jacobins",
          "mode": "bus",
          "network": null,
          "latitude": 49.892071,
          "longitude": 2.298393,
          "distanceM": 124
        },
        "… (3 éléments)"
      ]
    },
    "gtfsFeeds": [
      {
        "sourceCode": "transport_gouv",
        "fetchedAt": "2026-10-01T23:55:50.817Z",
        "expiresAt": "2026-10-08T23:55:50.817Z",
        "datasetId": "6033a87b4e276fd6499986bf",
        "inseeCode": "80021",
        "title": "Réseau urbain Ametis",
        "publisher": "Ametis",
        "gtfsUrl": "https://www.data.gouv.fr/api/1/datasets/r/5bc8b7dc-0d4e-48e7-b2ec-eccfe3702c19",
        "isAvailable": true,
        "coverageLevel": "epci",
        "updatedAt": "2026-09-14T12:18:46.000Z"
      },
      {
        "sourceCode": "transport_gouv",
        "fetchedAt": "2026-10-01T23:55:50.817Z",
        "expiresAt": "2026-10-08T23:55:50.817Z",
        "datasetId": "66970a3d58c639f7658e70c8",
        "inseeCode": "80021",
        "title": "Réseau interurbain - Somme (80)",
        "publisher": "Région Hauts-de-France",
        "gtfsUrl": "https://www.data.gouv.fr/api/1/datasets/r/429d30fb-ba6e-4e90-ad82-6d589a98cbfd",
        "isAvailable": true,
        "coverageLevel": "departement",
        "updatedAt": "2026-08-31T08:10:00.000Z"
      },
      "… (4 éléments)"
    ],
    "note": "Derniers départs du soir et service du dimanche : à calculer sur les GTFS (traitement batch, hors API)"
  },
  "charging": {
    "pointsWithin2km": 35,
    "fastChargers": 22,
    "nearest": [
      {
        "sourceCode": "irve",
        "fetchedAt": "2026-10-01T23:55:50.816Z",
        "expiresAt": "2026-10-08T23:55:50.816Z",
        "pdcId": "FRBMPE1336",
        "stationName": "Bump - OTERA - Amiens - OTERA AMIENS",
        "operatorName": "Bump",
        "inseeCode": "80021",
        "powerKw": 3.6,
        "connectors": [
          "2"
        ],
        "isFree": false,
        "accessCondition": "Accès libre",
        "openingHours": "24/7",
        "latitude": 49.894067,
        "longitude": 2.295753,
        "distanceM": 169
      },
      {
        "sourceCode": "irve",
        "fetchedAt": "2026-10-01T23:55:50.816Z",
        "expiresAt": "2026-10-08T23:55:50.816Z",
        "pdcId": "FRBMPE2561",
        "stationName": "Bump - OTERA - Amiens - OTERA AMIENS",
        "operatorName": "Bump",
        "inseeCode": "80021",
        "powerKw": 3.6,
        "connectors": [
          "2"
        ],
        "isFree": false,
        "accessCondition": "Accès libre",
        "openingHours": "24/7",
        "latitude": 49.894067,
        "longitude": 2.295753,
        "distanceM": 169
      },
      "… (5 éléments)"
    ]
  },
  "parking": [],
  "cycling": {
    "cycle_infrastructure_within_1km": {
      "value": 11328,
      "unit": "m"
    },
    "nearest_cycle_infrastructure": {
      "value": 170,
      "unit": "m"
    }
  },
  "notCovered": [
    "Tarifs et zones de stationnement résident sur voirie"
  ]
}
```

## Connectivité

### `POST /connectivity/fixed/import`

Import national ARCEP de l’éligibilité fixe par commune.

**Requête**

```http
POST /api/connectivity/fixed/import
```

**Réponse** `201`

```json
{
  "source": "arcep_fixe",
  "target": "france:commune_techno",
  "status": "cached",
  "items": 34877,
  "fetchedAt": "2026-10-01T23:55:50.812Z",
  "expiresAt": "2026-12-30T23:55:50.812Z"
}
```

### `POST /connectivity/mobile-sites/import`

Import national ARCEP des sites mobiles (2G à 5G) par opérateur.

**Requête**

```http
POST /api/connectivity/mobile-sites/import
```

**Réponse** `201`

```json
{
  "source": "arcep_mobile",
  "target": "france:sites",
  "status": "cached",
  "items": 129043,
  "fetchedAt": "2026-10-01T23:55:52.932Z",
  "expiresAt": "2026-12-30T23:55:52.932Z"
}
```

### `POST /addresses/:id/connectivity/collect`

S’assure que les deux référentiels ARCEP sont chargés et à jour.

**Requête**

```http
POST /api/addresses/1/connectivity/collect
```

**Réponse** `201`

```json
[
  {
    "source": "arcep_fixe",
    "target": "france:commune_techno",
    "status": "cached",
    "items": 34877,
    "fetchedAt": "2026-10-01T23:55:50.812Z",
    "expiresAt": "2026-12-30T23:55:50.812Z"
  },
  {
    "source": "arcep_mobile",
    "target": "france:sites",
    "status": "cached",
    "items": 129043,
    "fetchedAt": "2026-10-01T23:55:52.932Z",
    "expiresAt": "2026-12-30T23:55:52.932Z"
  }
]
```

### `GET /addresses/:id/connectivity`

Taux de fibre communal, proximité des sites 4G/5G par opérateur.

**Requête**

```http
GET /api/addresses/1/connectivity
```

**Réponse** `200`

```json
{
  "fixed": {
    "sourceCode": "arcep_fixe",
    "fetchedAt": "2026-10-01T23:55:50.812Z",
    "expiresAt": "2026-12-30T23:55:50.812Z",
    "inseeCode": "80021",
    "periodDate": "2026-06-30",
    "premises": 91983,
    "ftthEligible": 89735,
    "cableEligible": 0,
    "copperEligible": 91982,
    "thdRadioEligible": 0,
    "fixed4gEligible": 91788,
    "satelliteEligible": 91976,
    "ftthRate": 97.56,
    "scope": "commune",
    "note": "Taux communal d’éligibilité : l’éligibilité exacte du logement n’est pas publiée en API"
  },
  "mobile": [
    {
      "operator": "Bouygues Telecom",
      "sitesWithin1km": 8,
      "nearest4gM": 224,
      "nearest5gM": 342,
      "nearest5g3500M": 342
    },
    {
      "operator": "Free Mobile",
      "sitesWithin1km": 6,
      "nearest4gM": 350,
      "nearest5gM": 350,
      "nearest5g3500M": 350
    },
    "… (4 éléments)"
  ],
  "note": "Couverture intérieure non mesurée : indicateurs de proximité des sites ARCEP par opérateur",
  "notCovered": [
    "Réception TNT et satellite à l’adresse"
  ]
}
```

## Orchestration

### `POST /addresses/:id/collect`

Collecte tous les modules, ou une sélection (`modules=risk,water`). `force=true` ignore le cache.

**Requête**

```http
POST /api/addresses/1/collect?modules=risk,water
```

**Réponse** `201`

```json
{
  "addressId": 1,
  "durationMs": 2,
  "summary": {
    "success": 0,
    "cached": 8,
    "skipped": 0,
    "error": 0
  },
  "modules": [
    {
      "module": "risk",
      "durationMs": 2,
      "outcomes": [
        {
          "source": "georisques",
          "target": "address:1:report",
          "status": "cached",
          "items": 18,
          "fetchedAt": "2026-10-01T23:55:50.776Z",
          "expiresAt": "2026-10-31T23:55:50.776Z"
        },
        {
          "source": "georisques",
          "target": "commune:80021:profile",
          "status": "cached",
          "items": 1,
          "fetchedAt": "2026-10-01T23:55:50.774Z",
          "expiresAt": "2026-10-31T23:55:50.774Z"
        },
        "… (5 éléments)"
      ]
    },
    {
      "module": "water",
      "durationMs": 1,
      "outcomes": [
        {
          "source": "hubeau_eau_potable",
          "target": "commune:80021",
          "status": "cached",
          "items": 207,
          "fetchedAt": "2026-10-01T23:55:50.790Z",
          "expiresAt": "2026-10-08T23:55:50.790Z"
        },
        {
          "source": "hubeau_nappes",
          "target": "address:1",
          "status": "cached",
          "items": 33,
          "fetchedAt": "2026-10-01T23:55:50.788Z",
          "expiresAt": "2026-10-08T23:55:50.788Z"
        },
        "… (3 éléments)"
      ]
    }
  ]
}
```

### `POST /addresses/collect`

Géocode puis collecte (one-shot), avec sélection de modules.

**Requête**

```http
POST /api/addresses/collect?modules=geo,risk
Content-Type: application/json

{
  "q": "2 rue de la République, Amiens"
}
```

**Réponse** `201`

```json
{
  "addressId": 1,
  "durationMs": 7,
  "summary": {
    "success": 0,
    "cached": 11,
    "skipped": 0,
    "error": 0
  },
  "modules": [
    {
      "module": "geo",
      "durationMs": 5,
      "outcomes": [
        {
          "source": "apicarto_cadastre",
          "target": "address:1",
          "status": "cached",
          "items": 1,
          "fetchedAt": "2026-10-01T23:55:42.558Z",
          "expiresAt": "2026-12-30T23:55:42.558Z"
        },
        {
          "source": "geo_api",
          "target": "commune:80021",
          "status": "cached",
          "items": 1,
          "fetchedAt": "2026-10-01T23:55:42.450Z",
          "expiresAt": "2026-12-30T23:55:42.450Z"
        },
        "… (6 éléments)"
      ]
    },
    {
      "module": "risk",
      "durationMs": 1,
      "outcomes": [
        {
          "source": "georisques",
          "target": "address:1:report",
          "status": "cached",
          "items": 18,
          "fetchedAt": "2026-10-01T23:55:50.776Z",
          "expiresAt": "2026-10-31T23:55:50.776Z"
        },
        {
          "source": "georisques",
          "target": "commune:80021:profile",
          "status": "cached",
          "items": 1,
          "fetchedAt": "2026-10-01T23:55:50.774Z",
          "expiresAt": "2026-10-31T23:55:50.774Z"
        },
        "… (5 éléments)"
      ]
    }
  ]
}
```

### `GET /addresses/:id/report`

Rapport consolidé (tous modules), lecture seule.

**Requête**

```http
GET /api/addresses/1/report
```

**Réponse** `200`

```json
{
  "address": {
    "sourceCode": "ban",
    "fetchedAt": "2026-10-02T00:00:37.804Z",
    "expiresAt": "2026-11-01T00:00:37.804Z",
    "id": 1,
    "banId": "80021_6820_00002",
    "label": "2 Rue de la République 80000 Amiens",
    "housenumber": "2",
    "street": "Rue de la République",
    "postcode": "80000",
    "city": "Amiens",
    "inseeCode": "80021",
    "latitude": 49.892808,
    "longitude": 2.297087,
    "geocodeScore": 0.976,
    "geocodeType": "housenumber",
    "parcelIdu": "80021000VD0027",
    "rnbId": "QSQYSSG72D3F",
    "createdAt": "2026-10-01T23:55:42.554Z",
    "updatedAt": "2026-10-02T00:00:37.804Z",
    "commune": {
      "sourceCode": "geo_api",
      "fetchedAt": "2026-10-01T23:59:25.750Z",
      "expiresAt": "2026-12-30T23:59:25.750Z",
      "inseeCode": "80021",
      "name": "Amiens",
      "departmentCode": "80",
      "departmentName": "Somme",
      "regionCode": "32",
      "regionName": "Hauts-de-France",
      "epciCode": "248000531",
      "postalCodes": [
        "80000",
        "80080",
        "… (3 éléments)"
      ],
      "population": 136449,
      "surfaceHa": 5040.16,
      "latitude": 49.8987,
      "longitude": 2.2847
    },
    "parcel": {
      "sourceCode": "apicarto_cadastre",
      "fetchedAt": "2026-10-01T23:55:42.558Z",
      "expiresAt": "2026-12-30T23:55:42.558Z",
      "idu": "80021000VD0027",
      "inseeCode": "80021",
      "prefix": "000",
      "section": "VD",
      "numero": "0027",
      "sheet": 1,
      "areaM2": 870,
      "geometry": {
        "type": "MultiPolygon",
        "coordinates": [
          [
            [
              [
                2.29667773,
                49.89300052
              ],
              [
                2.29673243,
                49.89298691
              ],
              "… (13 éléments)"
            ]
          ]
        ]
      }
    }
  },
  "market": {
    "priceIndex": [
      {
        "inseeCode": "80021",
        "year": 2021,
        "propertyType": "Appartement",
        "salesCount": 943,
        "medianPriceM2": 2291.67,
        "meanPriceM2": 2434.77,
        "q1PriceM2": 1807.07,
        "q3PriceM2": 2813.39,
        "computedAt": "2026-10-02T00:00:37.621Z"
      },
      {
        "inseeCode": "80021",
        "year": 2021,
        "propertyType": "Ensemble",
        "salesCount": 1920,
        "medianPriceM2": 2250,
        "meanPriceM2": 2384.44,
        "q1PriceM2": 1817.34,
        "q3PriceM2": 2785.69,
        "computedAt": "2026-10-02T00:00:37.621Z"
      },
      "… (15 éléments)"
    ]
  },
  "urbanism": {
    "currentZone": {
      "sourceCode": "apicarto_gpu",
      "fetchedAt": "2026-10-01T23:55:42.683Z",
      "expiresAt": "2026-10-31T23:55:42.683Z",
      "id": 1,
      "gpuId": "zone_urba.3462417",
      "inseeCode": "80021",
      "documentId": "80021_PLU_20251211",
      "label": "UAa",
      "labelLong": "Quartier reconstruit sud ouest du centre-ville",
      "zoneType": "U",
      "approvedAt": "2025-12-11",
      "regulationFile": "80021_reglement_20251211.pdf",
      "containsAddress": true,
      "distanceM": 0
    },
    "neighbouringZones": [
      {
        "sourceCode": "apicarto_gpu",
        "fetchedAt": "2026-10-01T23:55:42.683Z",
        "expiresAt": "2026-10-31T23:55:42.683Z",
        "id": 2,
        "gpuId": "zone_urba.3462465",
        "inseeCode": "80021",
        "documentId": "80021_PLU_20251211",
        "label": "UAd",
        "labelLong": "Quartier ancien Est du centre-ville",
        "zoneType": "U",
        "approvedAt": "2025-12-11",
        "regulationFile": "80021_reglement_20251211.pdf",
        "containsAddress": false,
        "distanceM": 42
      },
      {
        "sourceCode": "apicarto_gpu",
        "fetchedAt": "2026-10-01T23:55:42.683Z",
        "expiresAt": "2026-10-31T23:55:42.683Z",
        "id": 3,
        "gpuId": "zone_urba.3462472",
        "inseeCode": "80021",
        "documentId": "80021_PLU_20251211",
        "label": "UFe",
        "labelLong": "Emprises d'équipements d'enseignement et administratifs",
        "zoneType": "U",
        "approvedAt": "2025-12-11",
        "regulationFile": "80021_reglement_20251211.pdf",
        "containsAddress": false,
        "distanceM": 201
      },
      "… (3 éléments)"
    ],
    "reservedLocations": [],
    "protectedLandscape": [
      {
        "sourceCode": "apicarto_gpu",
        "fetchedAt": "2026-10-01T23:55:42.933Z",
        "expiresAt": "2026-10-31T23:55:42.933Z",
        "id": 36,
        "gpuId": "prescription_surf.14412272",
        "inseeCode": "80021",
        "documentId": "80021_PLU_20251211",
        "geometryKind": "surface",
        "typeCode": "07",
        "subtypeCode": "01",
        "label": "Bati ou ensemble bati",
        "nature": "Bati_patrimo",
        "typeLabel": "Patrimoine bâti, paysager ou éléments de paysage à protéger",
        "distanceM": 6
      },
      {
        "sourceCode": "apicarto_gpu",
        "fetchedAt": "2026-10-01T23:55:42.933Z",
        "expiresAt": "2026-10-31T23:55:42.933Z",
        "id": 21,
        "gpuId": "prescription_surf.14412273",
        "inseeCode": "80021",
        "documentId": "80021_PLU_20251211",
        "geometryKind": "surface",
        "typeCode": "07",
        "subtypeCode": "01",
        "label": "Bati ou ensemble bati",
        "nature": "Bati_patrimo",
        "typeLabel": "Patrimoine bâti, paysager ou éléments de paysage à protéger",
        "distanceM": 10
      },
      "… (44 éléments)"
    ],
    "otherPrescriptions": [
      {
        "sourceCode": "apicarto_gpu",
        "fetchedAt": "2026-10-01T23:55:42.933Z",
        "expiresAt": "2026-10-31T23:55:42.933Z",
        "id": 1,
        "gpuId": "prescription_surf.14411362",
        "inseeCode": "80021",
        "documentId": "80021_PLU_20251211",
        "geometryKind": "surface",
        "typeCode": "44",
        "subtypeCode": "01",
        "label": "PERIMETRE CENTRE VILLE",
        "nature": "Perim_CV",
        "typeLabel": null,
        "distanceM": 0
      },
      {
        "sourceCode": "apicarto_gpu",
        "fetchedAt": "2026-10-01T23:55:42.933Z",
        "expiresAt": "2026-10-31T23:55:42.933Z",
        "id": 43,
        "gpuId": "prescription_surf.14412463",
        "inseeCode": "80021",
        "documentId": "80021_PLU_20251211",
        "geometryKind": "surface",
        "typeCode": "23",
        "subtypeCode": "00",
        "label": "Secteur avec taille minimale des logements en zone U et AU STL",
        "nature": null,
        "typeLabel": null,
        "distanceM": 0
      },
      "… (45 éléments)"
    ],
    "historicMonumentPerimeter": [
      {
        "sourceCode": "apicarto_gpu",
        "fetchedAt": "2026-10-01T23:55:43.679Z",
        "expiresAt": "2026-10-31T23:55:43.679Z",
        "id": 13,
        "gpuId": "assiette_sup_s.5793398",
        "supType": "ac1",
        "name": "Périmètre délimité de l'ancien hôtel Christophle",
        "assietteType": "Périmètre des abords",
        "generatorId": "AC1-172014607-1906270892-1"
      },
      {
        "sourceCode": "apicarto_gpu",
        "fetchedAt": "2026-10-01T23:55:43.679Z",
        "expiresAt": "2026-10-31T23:55:43.679Z",
        "id": 7,
        "gpuId": "assiette_sup_s.6030992",
        "supType": "ac1",
        "name": "Périmètre délimité églises Saint-Remi et des cordeliers",
        "assietteType": "Périmètre des abords",
        "generatorId": "AC1-172014607-1906270884-1"
      },
      "… (7 éléments)"
    ],
    "otherEasements": [],
    "monuments": [
      {
        "sourceCode": "monuments",
        "fetchedAt": "2026-10-01T23:55:44.540Z",
        "expiresAt": "2026-12-30T23:55:44.540Z",
        "reference": "PA00116059",
        "name": "Ancien hôtel Christophle",
        "inseeCode": "80021",
        "denomination": "hôtel",
        "protectionType": "inscrit MH partiellement",
        "protectionText": "Façade (cad. AK 123) : inscription par arrêté du 8 septembre 1988",
        "latitude": 49.892328,
        "longitude": 2.298031,
        "distanceM": 86
      },
      {
        "sourceCode": "monuments",
        "fetchedAt": "2026-10-01T23:55:44.540Z",
        "expiresAt": "2026-12-30T23:55:44.540Z",
        "reference": "PA80000025",
        "name": "Église Saint-Remi et couvent des Cordeliers",
        "inseeCode": "80021",
        "denomination": "couvent;église",
        "protectionType": "inscrit MH partiellement",
        "protectionText": "L'église, sa sacristie et l'ancienne nef du couvent (cad. VE 107) : inscription par arrêté du 17 août 2001",
        "latitude": 49.891987,
        "longitude": 2.296573,
        "distanceM": 98
      },
      "… (20 éléments)"
    ]
  },
  "building": {
    "building": {
      "sourceCode": "rnb",
      "fetchedAt": "2026-10-01T23:55:44.839Z",
      "expiresAt": "2026-10-31T23:55:44.839Z",
      "rnbId": "QSQYSSG72D3F",
      "bdnbGroupId": "bdnb-bg-66L6-LSZ5-2YK9",
      "status": "constructed",
      "inseeCode": "80021",
      "constructionYear": 1955,
      "heightM": 13,
      "levels": 6,
      "dwellings": 17,
      "wallMaterial": "BRIQUES",
      "roofMaterial": "ARDOISES",
      "mainUsage": "Résidentiel collectif",
      "dpeClassBdnb": "E",
      "condoRegistration": "AC6175483",
      "irisCode": "800211301",
      "footprintM2": 814,
      "groundAltitudeM": 33,
      "latitude": 49.892901,
      "longitude": 2.296932
    },
    "dpe": {
      "reference": {
        "sourceCode": "ademe_dpe",
        "fetchedAt": "2026-10-01T23:55:45.705Z",
        "expiresAt": "2026-10-31T23:55:45.705Z",
        "numeroDpe": "2680E0005882N",
        "rnbId": null,
        "banId": "80021_6820_00002",
        "addressLabel": "2 Rue de la République 80000 Amiens",
        "inseeCode": "80021",
        "issuedAt": "2026-01-03",
        "energyClass": "E",
        "ghgClass": "C",
        "energyKwhM2": 267,
        "ghgKgM2": 17,
        "constructionYear": null,
        "constructionPeriod": "1948-1974",
        "buildingType": "immeuble",
        "livingAreaM2": null,
        "ceilingHeightM": 2.7,
        "heatingEnergy": "Électricité",
        "annualCostEur": 39035.1,
        "latitude": 49.892808,
        "longitude": 2.297087,
        "sameAddress": true,
        "distanceM": 0
      },
      "all": [
        {
          "sourceCode": "ademe_dpe",
          "fetchedAt": "2026-10-01T23:55:45.705Z",
          "expiresAt": "2026-10-31T23:55:45.705Z",
          "numeroDpe": "2680E1531118L",
          "rnbId": null,
          "banId": "80021_2810_00002",
          "addressLabel": "2 Rue Duméril 80000 Amiens",
          "inseeCode": "80021",
          "issuedAt": "2026-06-08",
          "energyClass": "D",
          "ghgClass": "B",
          "energyKwhM2": 272,
          "ghgKgM2": 10,
          "constructionYear": null,
          "constructionPeriod": "avant 1948",
          "buildingType": "appartement",
          "livingAreaM2": 14.4,
          "ceilingHeightM": 2.5,
          "heatingEnergy": "Électricité",
          "annualCostEur": 549.3,
          "latitude": 49.892775,
          "longitude": 2.296794,
          "sameAddress": false,
          "distanceM": 21
        },
        {
          "sourceCode": "ademe_dpe",
          "fetchedAt": "2026-10-01T23:55:45.705Z",
          "expiresAt": "2026-10-31T23:55:45.705Z",
          "numeroDpe": "2680E0005882N",
          "rnbId": null,
          "banId": "80021_6820_00002",
          "addressLabel": "2 Rue de la République 80000 Amiens",
          "inseeCode": "80021",
          "issuedAt": "2026-01-03",
          "energyClass": "E",
          "ghgClass": "C",
          "energyKwhM2": 267,
          "ghgKgM2": 17,
          "constructionYear": null,
          "constructionPeriod": "1948-1974",
          "buildingType": "immeuble",
          "livingAreaM2": null,
          "ceilingHeightM": 2.7,
          "heatingEnergy": "Électricité",
          "annualCostEur": 39035.1,
          "latitude": 49.892808,
          "longitude": 2.297087,
          "sameAddress": true,
          "distanceM": 0
        },
        "… (26 éléments)"
      ]
    },
    "condominium": {
      "sourceCode": "rnic",
      "fetchedAt": "2026-10-01T23:55:45.845Z",
      "expiresAt": "2026-12-30T23:55:45.845Z",
      "registrationNumber": "AC6175483",
      "name": "2 REPUBLIQUE / 2 DUMERIL",
      "addressLabel": "2 r de la republique 80000 Amiens",
      "inseeCode": "80021",
      "totalLots": 65,
      "housingLots": 26,
      "parkingLots": 0,
      "syndicType": "professionnel",
      "syndicName": "MASSET FRERES",
      "mandateStatus": "Mandat en cours",
      "mandateEndDate": "2025-12-13",
      "constructionPeriod": "DE_1961_A_1974",
      "regulationDate": "1962-04-05",
      "isAided": false,
      "priorityDistrict": null,
      "cadastralRefs": [
        "80021000VD0027"
      ],
      "latitude": 49.892752,
      "longitude": 2.296769
    },
    "ceilingHeightM": 2.7,
    "presumptions": {
      "leadRisk": false,
      "asbestosRisk": true,
      "rentalBanDate": "2034-01-01",
      "rentalBanned": false,
      "notes": [
        "Plomb : constat (CREP) obligatoire pour les logements construits avant le 01/01/1949.",
        "Amiante : repérage obligatoire si le permis de construire est antérieur au 01/07/1997."
      ]
    }
  },
  "risks": {
    "atAddress": [
      {
        "sourceCode": "georisques",
        "fetchedAt": "2026-10-01T23:55:50.776Z",
        "expiresAt": "2026-10-31T23:55:50.776Z",
        "id": 2,
        "addressId": 1,
        "hazardCode": "inondation",
        "category": "natural",
        "label": "Inondation",
        "present": true,
        "communeStatus": "Risque Existant",
        "addressStatus": "Risque non Connu",
        "details": null
      },
      {
        "sourceCode": "georisques",
        "fetchedAt": "2026-10-01T23:55:50.776Z",
        "expiresAt": "2026-10-31T23:55:50.776Z",
        "id": 13,
        "addressId": 1,
        "hazardCode": "radon",
        "category": "natural",
        "label": "Radon",
        "present": true,
        "communeStatus": "Risque Existant - faible",
        "addressStatus": "Risque Existant - faible",
        "details": null
      },
      "… (8 éléments)"
    ],
    "notPresent": [
      "avalanche",
      "cyclone",
      "… (11 éléments)"
    ],
    "commune": {
      "sourceCode": "georisques",
      "fetchedAt": "2026-10-01T23:55:50.774Z",
      "expiresAt": "2026-10-31T23:55:50.774Z",
      "inseeCode": "80021",
      "radonClass": 1,
      "seismicZone": "1 - TRES FAIBLE",
      "knownRisks": [
        "Inondation",
        "Par ruissellement et coulée de boue",
        "… (8 éléments)"
      ],
      "floodAtlases": [
        {
          "code": "80DDTM20010005",
          "label": "Selle (département de la Somme)",
          "published": "2001-01-01"
        },
        {
          "code": "80DDTM20030002",
          "label": "Somme (département de la Somme)",
          "published": "2003-01-01"
        },
        "… (3 éléments)"
      ]
    },
    "catnat": {
      "total": 10,
      "byHazard": {
        "Mouvement de Terrain": 4,
        "Inondations et/ou Coulées de Boue": 5,
        "Inondations Remontée Nappe": 1
      },
      "latest": [
        {
          "sourceCode": "georisques",
          "fetchedAt": "2026-10-01T23:55:50.784Z",
          "expiresAt": "2026-10-31T23:55:50.784Z",
          "codeNational": "INTE2207961A",
          "inseeCode": "80021",
          "hazardLabel": "Mouvement de Terrain",
          "eventStart": "2021-02-09",
          "eventEnd": "2021-02-09",
          "decreeDate": "2022-03-14",
          "journalDate": "2022-03-30"
        },
        {
          "sourceCode": "georisques",
          "fetchedAt": "2026-10-01T23:55:50.784Z",
          "expiresAt": "2026-10-31T23:55:50.784Z",
          "codeNational": "INTE1731318A",
          "inseeCode": "80021",
          "hazardLabel": "Inondations et/ou Coulées de Boue",
          "eventStart": "2017-06-02",
          "eventEnd": "2017-06-02",
          "decreeDate": "2017-11-21",
          "journalDate": "2017-12-15"
        },
        "… (10 éléments)"
      ]
    },
    "sites": {
      "seveso": [],
      "icpe": [
        {
          "sourceCode": "georisques",
          "fetchedAt": "2026-10-01T23:55:50.784Z",
          "expiresAt": "2026-10-31T23:55:50.784Z",
          "id": 66,
          "siteType": "icpe",
          "externalId": "0003801169",
          "name": "PICARD",
          "inseeCode": "80021",
          "status": "Non ICPE",
          "sevesoStatus": null,
          "subtype": null,
          "details": {
            "regime": "Non ICPE",
            "naf": null,
            "siret": "78493968805071",
            "ied": false,
            "priority": false
          },
          "latitude": 49.894658,
          "longitude": 2.296637,
          "distanceM": 208
        },
        {
          "sourceCode": "georisques",
          "fetchedAt": "2026-10-01T23:55:50.784Z",
          "expiresAt": "2026-10-31T23:55:50.784Z",
          "id": 67,
          "siteType": "icpe",
          "externalId": "0003801279",
          "name": "SARL CENTRALE FRAIS",
          "inseeCode": "80021",
          "status": "Autres régimes",
          "sevesoStatus": null,
          "subtype": "10",
          "details": {
            "regime": "Autres régimes",
            "naf": "10",
            "siret": "50890512200034",
            "ied": false,
            "priority": false
          },
          "latitude": 49.894658,
          "longitude": 2.296637,
          "distanceM": 208
        },
        "… (50 éléments)"
      ],
      "pollutedSoils": [
        {
          "sourceCode": "georisques",
          "fetchedAt": "2026-10-01T23:55:50.784Z",
          "expiresAt": "2026-10-31T23:55:50.784Z",
          "id": 22,
          "siteType": "casias",
          "externalId": "SSP4022716",
          "name": "rue Duméril",
          "inseeCode": "80021",
          "status": "En arrêt",
          "sevesoStatus": null,
          "subtype": "casias",
          "details": {
            "address": "rue Duméril",
            "sheet": "https://fiches-risques.brgm.fr/georisques/casias/SSP4022716"
          },
          "latitude": 49.893169,
          "longitude": 2.296195,
          "distanceM": 75
        },
        {
          "sourceCode": "georisques",
          "fetchedAt": "2026-10-01T23:55:50.784Z",
          "expiresAt": "2026-10-31T23:55:50.784Z",
          "id": 46,
          "siteType": "casias",
          "externalId": "SSP4022818",
          "name": "Fabrique de chandelles",
          "inseeCode": "80021",
          "status": "En arrêt",
          "sevesoStatus": null,
          "subtype": "casias",
          "details": {
            "address": "11 rue Alphonse Paillat",
            "sheet": "https://fiches-risques.brgm.fr/georisques/casias/SSP4022818"
          },
          "latitude": 49.891549,
          "longitude": 2.297516,
          "distanceM": 143
        },
        "… (55 éléments)"
      ],
      "cavities": [
        {
          "sourceCode": "georisques",
          "fetchedAt": "2026-10-01T23:55:50.784Z",
          "expiresAt": "2026-10-31T23:55:50.784Z",
          "id": 3,
          "siteType": "cavity",
          "externalId": "PICAW0004163",
          "name": "Rue des sergents",
          "inseeCode": "80021",
          "status": null,
          "sevesoStatus": null,
          "subtype": "cave",
          "details": null,
          "latitude": 49.89449,
          "longitude": 2.298798,
          "distanceM": 224
        },
        {
          "sourceCode": "georisques",
          "fetchedAt": "2026-10-01T23:55:50.784Z",
          "expiresAt": "2026-10-31T23:55:50.784Z",
          "id": 4,
          "siteType": "cavity",
          "externalId": "PICAW0004164",
          "name": "Rue du Cloître de la Barge",
          "inseeCode": "80021",
          "status": null,
          "sevesoStatus": null,
          "subtype": "cave",
          "details": null,
          "latitude": 49.8935,
          "longitude": 2.300411,
          "distanceM": 250
        },
        "… (6 éléments)"
      ],
      "groundMovements": [
        {
          "sourceCode": "georisques",
          "fetchedAt": "2026-10-01T23:55:50.784Z",
          "expiresAt": "2026-10-31T23:55:50.784Z",
          "id": 7,
          "siteType": "ground_movement",
          "externalId": "11900607",
          "name": "58 rue Béranger - Point n°2",
          "inseeCode": "80021",
          "status": null,
          "sevesoStatus": null,
          "subtype": "Effondrement / Affaissement",
          "details": {
            "date": "2007-03-01",
            "reliability": "Fort",
            "comment": "limon"
          },
          "latitude": 49.890526,
          "longitude": 2.285918,
          "distanceM": 839
        },
        {
          "sourceCode": "georisques",
          "fetchedAt": "2026-10-01T23:55:50.784Z",
          "expiresAt": "2026-10-31T23:55:50.784Z",
          "id": 8,
          "siteType": "ground_movement",
          "externalId": "11900608",
          "name": "74/76 rue Béranger - Point n°3",
          "inseeCode": "80021",
          "status": null,
          "sevesoStatus": null,
          "subtype": "Effondrement / Affaissement",
          "details": {
            "date": "2004-02-01",
            "reliability": "Fort",
            "comment": "limon"
          },
          "latitude": 49.890354,
          "longitude": 2.285779,
          "distanceM": 855
        }
      ]
    },
    "biological": [
      {
        "sourceCode": "manual",
        "fetchedAt": "2026-10-02T00:00:37.665Z",
        "expiresAt": "2027-10-02T00:00:37.665Z",
        "id": 1,
        "scope": "department",
        "areaCode": "80",
        "species": "tiger_mosquito",
        "status": "implanté",
        "year": 2026,
        "referenceUrl": "https://sante.gouv.fr/sante-et-environnement/risques-microbiologiques-physiques-et-chimiques/especes-nuisibles-et-parasites/article/cartes-de-presence-du-mou…",
        "notes": null
      }
    ]
  },
  "water": {
    "drinkingWater": {
      "network": "AMIENS UDI",
      "distributor": "AMIENS METROPOLE",
      "lastConclusion": "Eau d’alimentation non conforme aux limites de qualité en vigueur pour les paramètres pesticides Desphényl-Chloridazone, et le total des pesticides analysés.…",
      "parameters": [
        {
          "key": "nitrates",
          "code": "1340",
          "label": "Nitrates (en NO3)",
          "value": 32.6,
          "rawValue": "32,6",
          "unit": "mg/L",
          "sampledAt": "2026-07-16T09:12:00.000Z",
          "exceedsLimit": false,
          "reference": "Limite de qualité : 50 mg/L"
        },
        {
          "key": "hardness",
          "code": "1345",
          "label": "Titre hydrotimétrique",
          "value": 31,
          "rawValue": "31,0",
          "unit": "°f",
          "sampledAt": "2025-12-18T09:53:00.000Z",
          "exceedsLimit": null,
          "reference": "Dureté : < 15 °f eau douce, > 30 °f eau très calcaire"
        },
        "… (5 éléments)"
      ]
    },
    "drought": [
      {
        "sourceCode": "vigieau",
        "fetchedAt": "2026-10-01T23:55:50.793Z",
        "expiresAt": "2026-10-02T23:55:50.793Z",
        "id": 1,
        "inseeCode": "80021",
        "zoneId": 6010234,
        "zoneCode": "22_80_7",
        "zoneName": "BASSIN DE LA  SELLE",
        "zoneType": "SUP",
        "severity": "alerte",
        "decreeStart": "2026-08-21",
        "decreeEnd": null,
        "decreeUrl": "https://regleau.s3.gra.perf.cloud.ovh.net/arrete-restriction/37849/bd3d6623-c4f4-45b5-aa4c-f4069b678da4/Arr%C3%83%C2%AAt%C3%83%C2%A9_sign%C3%83%C2%A9.pdf",
        "usages": [
          {
            "name": "Alimentation des fontaines publiques et privées d’ornement",
            "theme": "Alimenter des fontaines et autres usages de loisirs",
            "description": "L'alimentation des fontaines publiques et privées en circuit ouvert est interdite"
          },
          {
            "name": "Arrosage des golfs(Conformément à l'accord cadre golf et environnement 2019-2024",
            "theme": "Arroser",
            "description": "Interdiction d'arroser les terrains de golf de 8 heures à 20 heures de façon à diminuer la consommation d'eau sur le volume hebdomadaire de 15 à 30%. Tenue d…"
          },
          "… (13 éléments)"
        ]
      },
      {
        "sourceCode": "vigieau",
        "fetchedAt": "2026-10-01T23:55:50.793Z",
        "expiresAt": "2026-10-02T23:55:50.793Z",
        "id": 2,
        "inseeCode": "80021",
        "zoneId": 6010245,
        "zoneCode": "22_80_7",
        "zoneName": "BASSIN DE LA  SELLE",
        "zoneType": "SOU",
        "severity": "alerte",
        "decreeStart": "2026-08-21",
        "decreeEnd": null,
        "decreeUrl": "https://regleau.s3.gra.perf.cloud.ovh.net/arrete-restriction/37849/bd3d6623-c4f4-45b5-aa4c-f4069b678da4/Arr%C3%83%C2%AAt%C3%83%C2%A9_sign%C3%83%C2%A9.pdf",
        "usages": [
          {
            "name": "Alimentation des fontaines publiques et privées d’ornement",
            "theme": "Alimenter des fontaines et autres usages de loisirs",
            "description": "L'alimentation des fontaines publiques et privées en circuit ouvert est interdite"
          },
          {
            "name": "Arrosage des golfs(Conformément à l'accord cadre golf et environnement 2019-2024",
            "theme": "Arroser",
            "description": "Interdiction d'arroser les terrains de golf de 8 heures à 20 heures de façon à diminuer la consommation d'eau sur le volume hebdomadaire de 15 à 30%. Tenue d…"
          },
          "… (9 éléments)"
        ]
      },
      "… (3 éléments)"
    ],
    "groundwater": [
      {
        "sourceCode": "hubeau_nappes",
        "fetchedAt": "2026-10-01T23:55:50.788Z",
        "expiresAt": "2026-10-08T23:55:50.788Z",
        "codeBss": "00463X0036/H1",
        "bssId": "BSS000DXBD",
        "inseeCode": "80173",
        "communeName": "Cardonnette",
        "altitudeM": 87,
        "depthM": 48.75,
        "measuresCount": 7923,
        "firstMeasureDate": "1970-01-07",
        "lastMeasureDate": "2026-09-29",
        "lastWaterDepthM": 45.59,
        "lastLevelNgfM": 41.37,
        "latitude": 49.950686,
        "longitude": 2.35976,
        "distanceM": 7845,
        "active": true
      },
      {
        "sourceCode": "hubeau_nappes",
        "fetchedAt": "2026-10-01T23:55:50.788Z",
        "expiresAt": "2026-10-08T23:55:50.788Z",
        "codeBss": "00465X0007/F",
        "bssId": "BSS000DXKH",
        "inseeCode": "80305",
        "communeName": "Ferrières",
        "altitudeM": 107,
        "depthM": 112,
        "measuresCount": 7403,
        "firstMeasureDate": "1997-05-25",
        "lastMeasureDate": "2026-09-29",
        "lastWaterDepthM": 73.75,
        "lastLevelNgfM": 33.49,
        "latitude": 49.895282,
        "longitude": 2.177815,
        "distanceM": 8548,
        "active": true
      },
      "… (5 éléments)"
    ],
    "sanitation": {
      "covered": false,
      "note": "Raccordement à l’assainissement collectif : aucune source ouverte à l’adresse"
    }
  },
  "climate": {
    "observed": {
      "frost_days_per_year": {
        "value": 33.6,
        "unit": "jours/an"
      },
      "hot_days_per_year": {
        "value": 6.5,
        "unit": "jours/an"
      },
      "precipitation_per_year": {
        "value": 767.2,
        "unit": "mm/an"
      },
      "severe_frost_days_per_year": {
        "value": 2.4,
        "unit": "jours/an"
      },
      "snow_days_per_year": {
        "value": 2.4,
        "unit": "jours/an"
      },
      "snowfall_per_year": {
        "value": 9.5,
        "unit": "cm/an"
      },
      "strong_wind_days_per_year": {
        "value": 5,
        "unit": "jours/an"
      },
      "sunshine_hours_per_year": {
        "value": 2866.6,
        "unit": "h/an"
      },
      "tropical_nights_per_year": {
        "value": 1.5,
        "unit": "nuits/an"
      },
      "winter_sunshine_hours": {
        "value": 363.4,
        "unit": "h/hiver"
      }
    },
    "observedMeta": {
      "period": "2016-2025",
      "gridLat": 49.876976,
      "gridLon": 2.347826,
      "elevation": 37
    },
    "projections2050": {
      "models": [
        "MRI_AGCM3_2_S",
        "CMCC_CM2_VHR4",
        "… (3 éléments)"
      ],
      "ensemble": {
        "mean_tmax": {
          "2005-2014": 14.7,
          "2041-2050": 16.3,
          "change": 1.6
        },
        "hot_days_per_year": {
          "2005-2014": 7.3,
          "2041-2050": 15.1,
          "change": 7.8
        },
        "tropical_nights_per_year": {
          "2005-2014": 2.3,
          "2041-2050": 7.3,
          "change": 5
        },
        "frost_days_per_year": {
          "2005-2014": 33.7,
          "2041-2050": 18.8,
          "change": -14.9
        },
        "precipitation_per_year": {
          "2005-2014": 735.9,
          "2041-2050": 717.6,
          "change": -18.3
        }
      },
      "perModel": [
        {
          "sourceCode": "open_meteo_climate",
          "fetchedAt": "2026-10-01T23:55:50.797Z",
          "expiresAt": "2027-10-01T23:55:50.797Z",
          "id": 1,
          "addressId": 1,
          "model": "MRI_AGCM3_2_S",
          "period": "2005-2014",
          "indicator": "mean_tmax",
          "value": 14.4,
          "unit": "°C"
        },
        {
          "sourceCode": "open_meteo_climate",
          "fetchedAt": "2026-10-01T23:55:50.797Z",
          "expiresAt": "2027-10-01T23:55:50.797Z",
          "id": 2,
          "addressId": 1,
          "model": "MRI_AGCM3_2_S",
          "period": "2005-2014",
          "indicator": "hot_days_per_year",
          "value": 7.5,
          "unit": "jours/an"
        },
        "… (30 éléments)"
      ]
    },
    "solar": {
      "sourceCode": "pvgis",
      "fetchedAt": "2026-10-01T23:55:50.778Z",
      "expiresAt": "2027-10-01T23:55:50.778Z",
      "id": 1,
      "addressId": 1,
      "tiltDeg": 39,
      "azimuthDeg": -2,
      "yearlyKwhPerKwp": 1111.8,
      "yearlyIrradiationKwhM2": 1379.23,
      "winterKwhPerKwp": 143.18,
      "monthly": [
        {
          "month": 1,
          "kwh": 41.83,
          "irradiation": 48.68
        },
        {
          "month": 2,
          "kwh": 61.6,
          "irradiation": 72.02
        },
        "… (12 éléments)"
      ]
    },
    "airQuality": [],
    "pollens": [],
    "caveats": [
      "Réanalyse ERA5 (maille ~10 km) : l’îlot de chaleur urbain et les effets de relief local sont lissés.",
      "sunshine_duration ERA5 surestime nettement l’ensoleillement mesuré par héliographe : à utiliser en comparaison entre adresses, pas en valeur absolue."
    ],
    "notCovered": [
      "Brouillard (pas de climatologie ouverte à l’adresse)",
      "Masques solaires dus aux bâtiments voisins"
    ]
  },
  "nuisances": {
    "radiusM": 1000,
    "summary": {
      "nightlife": {
        "count": 78,
        "nearestM": 51,
        "nearest": {
          "name": "Le Piccadilly",
          "subcategory": "bar",
          "distanceM": 51
        }
      },
      "place_of_worship": {
        "count": 17,
        "nearestM": 105,
        "nearest": {
          "name": "Église Saint-Remi",
          "subcategory": "place_of_worship",
          "distanceM": 105
        }
      },
      "marketplace": {
        "count": 5,
        "nearestM": 287,
        "nearest": {
          "name": "Marché Hebdomadaire",
          "subcategory": "marketplace",
          "distanceM": 287
        }
      },
      "concert_venue": {
        "count": 10,
        "nearestM": 393,
        "nearest": {
          "name": "La Comédie de Picardie",
          "subcategory": "theatre",
          "distanceM": 393
        }
      },
      "railway": {
        "count": 71,
        "nearestM": 494,
        "nearest": {
          "name": "Ligne de Longueau à Boulogne-Ville",
          "subcategory": "25 kV",
          "distanceM": 494
        }
      },
      "power_line": {
        "count": 12,
        "nearestM": 2121,
        "nearest": {
          "name": null,
          "subcategory": "20 kV",
          "distanceM": 2121
        }
      }
    },
    "powerLines": [
      {
        "sourceCode": "overpass",
        "fetchedAt": "2026-10-01T23:55:50.781Z",
        "expiresAt": "2026-10-31T23:55:50.781Z",
        "id": 42,
        "externalId": "osm:way/621582981",
        "category": "power_line",
        "subcategory": "20 kV",
        "name": null,
        "tags": {
          "operator": "Enedis",
          "voltage": "20000"
        },
        "distanceM": 2121
      },
      {
        "sourceCode": "overpass",
        "fetchedAt": "2026-10-01T23:55:50.781Z",
        "expiresAt": "2026-10-31T23:55:50.781Z",
        "id": 45,
        "externalId": "osm:way/621582995",
        "category": "power_line",
        "subcategory": "225 kV",
        "name": null,
        "tags": {
          "operator": "RTE",
          "voltage": "225000"
        },
        "distanceM": 2127
      },
      "… (5 éléments)"
    ],
    "mobileAntennas": [
      {
        "sourceCode": "arcep_mobile",
        "fetchedAt": "2026-10-01T23:55:52.932Z",
        "expiresAt": "2026-12-30T23:55:52.932Z",
        "operatorCode": "20801",
        "siteNumber": "00029500A1",
        "operatorName": "Orange",
        "anfrStationId": "802290240",
        "inseeCode": "80021",
        "has2g": false,
        "has3g": false,
        "has4g": true,
        "has5g": false,
        "has5g3500": false,
        "latitude": 49.8925,
        "longitude": 2.29945,
        "distanceM": 173
      },
      {
        "sourceCode": "arcep_mobile",
        "fetchedAt": "2026-10-01T23:55:52.932Z",
        "expiresAt": "2026-12-30T23:55:52.932Z",
        "operatorCode": "20810",
        "siteNumber": "800662",
        "operatorName": "SFR",
        "anfrStationId": "802700150",
        "inseeCode": "80021",
        "has2g": true,
        "has3g": true,
        "has4g": true,
        "has5g": false,
        "has5g3500": false,
        "latitude": 49.89207,
        "longitude": 2.3,
        "distanceM": 224
      },
      "… (12 éléments)"
    ],
    "airportNoisePlans": [
      {
        "sourceCode": "geopf_wfs",
        "fetchedAt": "2026-10-01T23:55:59.075Z",
        "expiresAt": "2026-12-30T23:55:59.075Z",
        "id": 112,
        "externalId": "peb:LFAY",
        "category": "airport_noise_plan",
        "subcategory": "LFAY",
        "name": "LFAY - AMIENS",
        "tags": {
          "arrete": "http://piece-jointe-carto.developpement-durable.gouv.fr/NAT003/PEB/PEB_LFAY_01_12_1982.pdf"
        },
        "latitude": 49.873104,
        "longitude": 2.386986,
        "distanceM": 6804
      },
      {
        "sourceCode": "geopf_wfs",
        "fetchedAt": "2026-10-01T23:55:59.075Z",
        "expiresAt": "2026-12-30T23:55:59.075Z",
        "id": 113,
        "externalId": "peb:LFAQ",
        "category": "airport_noise_plan",
        "subcategory": "LFAQ",
        "name": "LFAQ - ALBERT",
        "tags": {
          "arrete": "http://piece-jointe-carto.developpement-durable.gouv.fr/NAT003/PEB/PEB_LFAQ_05_10_2005.pdf"
        },
        "latitude": 49.970062,
        "longitude": 2.692617,
        "distanceM": 29585
      }
    ],
    "flights": {
      "snapshotAt": null,
      "aircraftWithin15km": 0,
      "lowestAltitudeM": null,
      "closest": [],
      "note": "Instantané OpenSky : à échantillonner dans le temps pour estimer un couloir aérien"
    },
    "notCovered": [
      "Pollution lumineuse",
      "Livraisons et fret de nuit",
      "… (4 éléments)"
    ]
  },
  "energy": {
    "heatNetwork": {
      "sourceCode": "fcu",
      "fetchedAt": "2026-10-01T23:55:50.783Z",
      "expiresAt": "2026-10-31T23:55:50.783Z",
      "id": 1,
      "addressId": 1,
      "networkType": "heat",
      "available": true,
      "distanceM": 164,
      "operatorName": "Amiens Energies (ENGIE SOLUTIONS)",
      "networkName": "Réseau de la ville d'Amiens",
      "details": {
        "networkId": "8002C",
        "renewableRate": 53.4,
        "co2Rate": 0.124,
        "futureNetwork": false,
        "priorityZone": true
      }
    },
    "gasNetwork": {
      "sourceCode": "grdf",
      "fetchedAt": "2026-10-01T23:55:50.799Z",
      "expiresAt": "2026-12-30T23:55:50.799Z",
      "id": 2,
      "addressId": 1,
      "networkType": "gas",
      "available": true,
      "distanceM": null,
      "operatorName": "GRDF",
      "networkName": null,
      "details": {
        "scope": "commune",
        "propane": null,
        "note": "Commune desservie par GRDF ; le raccordement du logement n’est pas publié"
      }
    },
    "electricity": {
      "atAddress": [],
      "communeAverage": [
        {
          "sourceCode": "enedis",
          "fetchedAt": "2026-10-01T23:55:50.801Z",
          "expiresAt": "2026-12-30T23:55:50.801Z",
          "id": 1,
          "inseeCode": "80021",
          "addressKey": "__COMMUNE__",
          "year": 2024,
          "irisCode": null,
          "dwellings": null,
          "totalMwh": null,
          "avgPerSiteMwh": null,
          "communeAvgMwh": 2.619
        }
      ]
    },
    "notCovered": [
      "Historique des coupures électriques à l’adresse"
    ]
  },
  "services": {
    "byCategory": {
      "bakery": {
        "countWithin2km": 51,
        "nearest": [
          {
            "sourceCode": "overpass",
            "fetchedAt": "2026-10-01T23:55:50.804Z",
            "expiresAt": "2026-10-31T23:55:50.804Z",
            "id": 154,
            "externalId": "osm:node/11917606769",
            "category": "bakery",
            "name": "Mamatte Boulangerie Café",
            "addressLabel": "2 Place Gambetta Amiens",
            "inseeCode": null,
            "openingHours": "Mo-Sa 07:00-20:00; Su 07:30-19:00",
            "details": {
              "opensOnSunday": true,
              "operator": null
            },
            "latitude": 49.892939,
            "longitude": 2.297318,
            "distanceM": 22
          },
          {
            "sourceCode": "overpass",
            "fetchedAt": "2026-10-01T23:55:50.804Z",
            "expiresAt": "2026-10-31T23:55:50.804Z",
            "id": 145,
            "externalId": "osm:node/4857531131",
            "category": "bakery",
            "name": "La Mie Câline",
            "addressLabel": "1 bis Place Gambetta Amiens",
            "inseeCode": null,
            "openingHours": "Mo-Sa 07:30-19:45; Su off",
            "details": {
              "opensOnSunday": false,
              "operator": null
            },
            "latitude": 49.893017,
            "longitude": 2.297038,
            "distanceM": 23
          },
          "… (3 éléments)"
        ]
      },
      "childcare": {
        "countWithin2km": 18,
        "nearest": [
          {
            "sourceCode": "recherche_entreprises",
            "fetchedAt": "2026-10-01T23:55:50.803Z",
            "expiresAt": "2026-10-31T23:55:50.803Z",
            "id": 26,
            "externalId": "siret:83809878800030",
            "category": "childcare",
            "name": "HESTIA HZ",
            "addressLabel": "7 RUE DES CORDELIERS 80000 AMIENS",
            "inseeCode": "80021",
            "openingHours": null,
            "details": {
              "siret": "83809878800030",
              "naf": "88.91A",
              "createdAt": "2018-10-29"
            },
            "latitude": 49.892357,
            "longitude": 2.295597,
            "distanceM": 118
          },
          {
            "sourceCode": "recherche_entreprises",
            "fetchedAt": "2026-10-01T23:55:50.803Z",
            "expiresAt": "2026-10-31T23:55:50.803Z",
            "id": 4,
            "externalId": "siret:52337105200417",
            "category": "childcare",
            "name": "KINOUGARDE",
            "addressLabel": "18 PLACE DE L'HOTEL DE VILLE 80000 AMIENS",
            "inseeCode": "80021",
            "openingHours": null,
            "details": {
              "siret": "52337105200417",
              "naf": "88.91A",
              "createdAt": "2023-04-03"
            },
            "latitude": 49.892916,
            "longitude": 2.295185,
            "distanceM": 137
          },
          "… (3 éléments)"
        ]
      },
      "general_practitioner": {
        "countWithin2km": 51,
        "nearest": [
          {
            "sourceCode": "recherche_entreprises",
            "fetchedAt": "2026-10-01T23:55:50.803Z",
            "expiresAt": "2026-10-31T23:55:50.803Z",
            "id": 87,
            "externalId": "siret:51829092900026",
            "category": "general_practitioner",
            "name": "CRISTINA SMETANCA",
            "addressLabel": "12 RUE DUSEVEL 80000 AMIENS",
            "inseeCode": "80021",
            "openingHours": null,
            "details": {
              "siret": "51829092900026",
              "naf": "86.21Z",
              "createdAt": "2019-07-11"
            },
            "latitude": 49.894242,
            "longitude": 2.299496,
            "distanceM": 235
          },
          {
            "sourceCode": "recherche_entreprises",
            "fetchedAt": "2026-10-01T23:55:50.803Z",
            "expiresAt": "2026-10-31T23:55:50.803Z",
            "id": 51,
            "externalId": "siret:98207610100012",
            "category": "general_practitioner",
            "name": "THIBAUT DEHEDIN",
            "addressLabel": "APPARTEMENT 2 8 RUE ALBERT ROZE 80000 AMIENS",
            "inseeCode": "80021",
            "openingHours": null,
            "details": {
              "siret": "98207610100012",
              "naf": "86.21Z",
              "createdAt": "2023-12-01"
            },
            "latitude": 49.891956,
            "longitude": 2.293455,
            "distanceM": 277
          },
          "… (3 éléments)"
        ]
      },
      "hospital": {
        "countWithin2km": 3,
        "nearest": [
          {
            "sourceCode": "recherche_entreprises",
            "fetchedAt": "2026-10-01T23:55:50.803Z",
            "expiresAt": "2026-10-31T23:55:50.803Z",
            "id": 5,
            "externalId": "siret:26800029600114",
            "category": "hospital",
            "name": "CMP 80I01 PEDOPSYCHIATRIE",
            "addressLabel": "2 PLACE AU FEURRE 80000 AMIENS",
            "inseeCode": "80021",
            "openingHours": null,
            "details": {
              "siret": "26800029600114",
              "naf": "86.10Z",
              "createdAt": "1995-01-01"
            },
            "latitude": 49.896807,
            "longitude": 2.298176,
            "distanceM": 451
          },
          {
            "sourceCode": "recherche_entreprises",
            "fetchedAt": "2026-10-01T23:55:50.803Z",
            "expiresAt": "2026-10-31T23:55:50.803Z",
            "id": 6,
            "externalId": "siret:26800014800042",
            "category": "hospital",
            "name": "CENTRE GYNECOLOGIE OBSTETRIQUE",
            "addressLabel": "124 RUE CAMILLE DESMOULINS 80000 AMIENS",
            "inseeCode": "80021",
            "openingHours": null,
            "details": {
              "siret": "26800014800042",
              "naf": "86.10Z",
              "createdAt": "1983-12-01"
            },
            "latitude": 49.881719,
            "longitude": 2.300705,
            "distanceM": 1260
          },
          "… (3 éléments)"
        ]
      },
      "pharmacy": {
        "countWithin2km": 33,
        "nearest": [
          {
            "sourceCode": "overpass",
            "fetchedAt": "2026-10-01T23:55:50.804Z",
            "expiresAt": "2026-10-31T23:55:50.804Z",
            "id": 101,
            "externalId": "osm:node/1229685381",
            "category": "pharmacy",
            "name": "Pharmacie Lafayette",
            "addressLabel": "4 Place Gambetta Amiens",
            "inseeCode": null,
            "openingHours": "Mo-Sa 09:00-19:30",
            "details": {
              "opensOnSunday": false,
              "operator": null
            },
            "latitude": 49.893164,
            "longitude": 2.297816,
            "distanceM": 66
          },
          {
            "sourceCode": "overpass",
            "fetchedAt": "2026-10-01T23:55:50.804Z",
            "expiresAt": "2026-10-31T23:55:50.804Z",
            "id": 116,
            "externalId": "osm:node/3100404842",
            "category": "pharmacy",
            "name": "Pharmacie de l'Hotel de Ville",
            "addressLabel": "18 Rue de Beauvais",
            "inseeCode": null,
            "openingHours": "Mo-Fr 09:00-19:00; Sa 09:00-18:00; Su off",
            "details": {
              "opensOnSunday": false,
              "operator": null
            },
            "latitude": 49.893042,
            "longitude": 2.294107,
            "distanceM": 215
          },
          "… (3 éléments)"
        ]
      },
      "supermarket": {
        "countWithin2km": 6,
        "nearest": [
          {
            "sourceCode": "recherche_entreprises",
            "fetchedAt": "2026-10-01T23:55:50.803Z",
            "expiresAt": "2026-10-31T23:55:50.803Z",
            "id": 52,
            "externalId": "siret:91909694100035",
            "category": "supermarket",
            "name": "CARREFOUR CITY",
            "addressLabel": "13 RUE DES VERGEAUX 80000 AMIENS",
            "inseeCode": "80021",
            "openingHours": null,
            "details": {
              "siret": "91909694100035",
              "naf": "47.11D",
              "createdAt": "2024-06-07"
            },
            "latitude": 49.8949,
            "longitude": 2.297446,
            "distanceM": 234
          },
          {
            "sourceCode": "recherche_entreprises",
            "fetchedAt": "2026-10-01T23:55:50.803Z",
            "expiresAt": "2026-10-31T23:55:50.803Z",
            "id": 10,
            "externalId": "siret:48226545100054",
            "category": "supermarket",
            "name": "RIVERY EXPLOITATION",
            "addressLabel": "12-16 RUE GRESSET 80000 AMIENS",
            "inseeCode": "80021",
            "openingHours": null,
            "details": {
              "siret": "48226545100054",
              "naf": "47.11D",
              "createdAt": "2023-02-01"
            },
            "latitude": 49.894113,
            "longitude": 2.294086,
            "distanceM": 259
          },
          "… (3 éléments)"
        ]
      }
    },
    "emergency": [
      {
        "sourceCode": "overpass",
        "fetchedAt": "2026-10-01T23:55:50.804Z",
        "expiresAt": "2026-10-31T23:55:50.804Z",
        "id": 166,
        "externalId": "osm:relation/8271449",
        "category": "emergency",
        "name": "Clinique de l'Europe",
        "addressLabel": null,
        "inseeCode": null,
        "openingHours": "24/7",
        "details": {
          "opensOnSunday": true,
          "operator": null
        },
        "latitude": 49.87083,
        "longitude": 2.295548,
        "distanceM": 2446
      },
      {
        "sourceCode": "overpass",
        "fetchedAt": "2026-10-01T23:55:50.804Z",
        "expiresAt": "2026-10-31T23:55:50.804Z",
        "id": 163,
        "externalId": "osm:way/332382649",
        "category": "emergency",
        "name": "Hôpital Psychiatrique Philippe Pinel",
        "addressLabel": "74410 Route d'Amiens Amiens",
        "inseeCode": null,
        "openingHours": null,
        "details": {
          "opensOnSunday": null,
          "operator": null
        },
        "latitude": 49.870509,
        "longitude": 2.275593,
        "distanceM": 2919
      },
      "… (3 éléments)"
    ],
    "sundayBakeries": [
      {
        "sourceCode": "overpass",
        "fetchedAt": "2026-10-01T23:55:50.804Z",
        "expiresAt": "2026-10-31T23:55:50.804Z",
        "id": 154,
        "externalId": "osm:node/11917606769",
        "category": "bakery",
        "name": "Mamatte Boulangerie Café",
        "addressLabel": "2 Place Gambetta Amiens",
        "inseeCode": null,
        "openingHours": "Mo-Sa 07:00-20:00; Su 07:30-19:00",
        "details": {
          "opensOnSunday": true,
          "operator": null
        },
        "latitude": 49.892939,
        "longitude": 2.297318,
        "distanceM": 22
      },
      {
        "sourceCode": "overpass",
        "fetchedAt": "2026-10-01T23:55:50.804Z",
        "expiresAt": "2026-10-31T23:55:50.804Z",
        "id": 137,
        "externalId": "osm:node/3902535180",
        "category": "bakery",
        "name": "Les Saveurs du Pain",
        "addressLabel": "9 Rue du Maréchal de Lattre de Tassigny",
        "inseeCode": null,
        "openingHours": "Mo-Su 06:30-21:00",
        "details": {
          "opensOnSunday": true,
          "operator": null
        },
        "latitude": 49.892036,
        "longitude": 2.2924,
        "distanceM": 347
      },
      "… (5 éléments)"
    ],
    "travelTimes": [
      {
        "sourceCode": "ign_navigation",
        "fetchedAt": "2026-10-01T23:56:51.281Z",
        "expiresAt": "2026-10-31T23:56:51.281Z",
        "id": 5,
        "addressId": 1,
        "destinationKind": "nearest_emergency",
        "profile": "car",
        "destinationLabel": "Clinique de l'Europe",
        "destinationLat": 49.87083,
        "destinationLon": 2.295548,
        "durationS": 659,
        "distanceM": 2891
      },
      {
        "sourceCode": "ign_navigation",
        "fetchedAt": "2026-10-01T23:56:51.281Z",
        "expiresAt": "2026-10-31T23:56:51.281Z",
        "id": 1,
        "addressId": 1,
        "destinationKind": "nearest_general_practitioner",
        "profile": "car",
        "destinationLabel": "CRISTINA SMETANCA",
        "destinationLat": 49.894242,
        "destinationLon": 2.299496,
        "durationS": 228,
        "distanceM": 1115
      },
      "… (5 éléments)"
    ],
    "schools": [
      {
        "sourceCode": "education",
        "fetchedAt": "2026-10-01T23:55:50.805Z",
        "expiresAt": "2026-12-30T23:55:50.805Z",
        "uai": "0801479Y",
        "name": "Lycée Saint-Rémi",
        "schoolType": "Lycée",
        "natureLabel": "LYCEE ENSEIGNT GENERAL ET TECHNOLOGIQUE",
        "sector": "Privé",
        "inseeCode": "80021",
        "hasPreschool": null,
        "hasElementary": null,
        "hasCanteen": true,
        "priorityEducation": null,
        "ips": null,
        "ipsSchoolYear": null,
        "classesCount": null,
        "studentsCount": null,
        "avgClassSize": null,
        "headcountYear": null,
        "latitude": 49.893842,
        "longitude": 2.298264,
        "distanceM": 143
      },
      {
        "sourceCode": "education",
        "fetchedAt": "2026-10-01T23:55:50.805Z",
        "expiresAt": "2026-12-30T23:55:50.805Z",
        "uai": "0801950K",
        "name": "Lycée professionnel Saint-Rémi",
        "schoolType": "Lycée",
        "natureLabel": "LYCEE PROFESSIONNEL",
        "sector": "Privé",
        "inseeCode": "80021",
        "hasPreschool": null,
        "hasElementary": null,
        "hasCanteen": true,
        "priorityEducation": null,
        "ips": null,
        "ipsSchoolYear": null,
        "classesCount": null,
        "studentsCount": null,
        "avgClassSize": null,
        "headcountYear": null,
        "latitude": 49.893842,
        "longitude": 2.298264,
        "distanceM": 143
      },
      "… (56 éléments)"
    ],
    "indicators": [],
    "notCovered": [
      "Médecins acceptant de nouveaux patients",
      "Pharmacie de garde",
      "… (5 éléments)"
    ]
  },
  "socio": {
    "demography": {
      "latest": {
        "dwellings_total": {
          "year": 2023,
          "value": 79419,
          "unit": "logements"
        },
        "mean_age_estimated": {
          "year": 2023,
          "value": 37.7,
          "unit": "ans"
        },
        "mean_length_of_stay": {
          "year": 2023,
          "value": 11.4,
          "unit": "ans"
        },
        "population": {
          "year": 2023,
          "value": 136449,
          "unit": "habitants"
        },
        "secondary_homes": {
          "year": 2023,
          "value": 2213,
          "unit": "logements"
        },
        "share_65_plus": {
          "year": 2023,
          "value": 16.2,
          "unit": "%"
        },
        "share_moved_in_last_2_years": {
          "year": 2023,
          "value": 19.14,
          "unit": "%"
        },
        "share_secondary_homes": {
          "year": 2023,
          "value": 2.79,
          "unit": "%"
        },
        "share_under_20": {
          "year": 2023,
          "value": 25.26,
          "unit": "%"
        },
        "share_vacant_dwellings": {
          "year": 2023,
          "value": 9.28,
          "unit": "%"
        },
        "vacant_dwellings": {
          "year": 2023,
          "value": 7373,
          "unit": "logements"
        }
      },
      "series": {
        "dwellings_total": [
          {
            "year": 2012,
            "value": 70076,
            "unit": "logements"
          },
          {
            "year": 2017,
            "value": 73541,
            "unit": "logements"
          },
          "… (3 éléments)"
        ],
        "mean_age_estimated": [
          {
            "year": 2012,
            "value": 36.7,
            "unit": "ans"
          },
          {
            "year": 2017,
            "value": 36.8,
            "unit": "ans"
          },
          "… (3 éléments)"
        ],
        "mean_length_of_stay": [
          {
            "year": 2012,
            "value": 11.6,
            "unit": "ans"
          },
          {
            "year": 2017,
            "value": 11.3,
            "unit": "ans"
          },
          "… (3 éléments)"
        ],
        "population": [
          {
            "year": 2012,
            "value": 132727,
            "unit": "habitants"
          },
          {
            "year": 2017,
            "value": 134057,
            "unit": "habitants"
          },
          "… (3 éléments)"
        ],
        "secondary_homes": [
          {
            "year": 2012,
            "value": 628,
            "unit": "logements"
          },
          {
            "year": 2017,
            "value": 1528,
            "unit": "logements"
          },
          "… (3 éléments)"
        ],
        "share_65_plus": [
          {
            "year": 2012,
            "value": 13.56,
            "unit": "%"
          },
          {
            "year": 2017,
            "value": 14.32,
            "unit": "%"
          },
          "… (3 éléments)"
        ],
        "share_moved_in_last_2_years": [
          {
            "year": 2012,
            "value": 20.91,
            "unit": "%"
          },
          {
            "year": 2017,
            "value": 21.17,
            "unit": "%"
          },
          "… (3 éléments)"
        ],
        "share_secondary_homes": [
          {
            "year": 2012,
            "value": 0.9,
            "unit": "%"
          },
          {
            "year": 2017,
            "value": 2.08,
            "unit": "%"
          },
          "… (3 éléments)"
        ],
        "share_under_20": [
          {
            "year": 2012,
            "value": 25.56,
            "unit": "%"
          },
          {
            "year": 2017,
            "value": 26.6,
            "unit": "%"
          },
          "… (3 éléments)"
        ],
        "share_vacant_dwellings": [
          {
            "year": 2012,
            "value": 8.87,
            "unit": "%"
          },
          {
            "year": 2017,
            "value": 9.19,
            "unit": "%"
          },
          "… (3 éléments)"
        ],
        "vacant_dwellings": [
          {
            "year": 2012,
            "value": 6219,
            "unit": "logements"
          },
          {
            "year": 2017,
            "value": 6762,
            "unit": "logements"
          },
          "… (3 éléments)"
        ]
      }
    },
    "taxes": {
      "history": [
        {
          "sourceCode": "fiscalite_locale",
          "fetchedAt": "2026-10-01T23:55:50.821Z",
          "expiresAt": "2027-03-30T23:55:50.821Z",
          "inseeCode": "80021",
          "year": 2021,
          "epciCode": "248000531",
          "propertyTaxRate": 55.87,
          "landTaxRate": 64.01,
          "wasteTaxRate": 8.53,
          "housingTaxRate": 32.78,
          "secondaryHomeSurcharge": false,
          "secondaryHomeSurchargeRate": null
        },
        {
          "sourceCode": "fiscalite_locale",
          "fetchedAt": "2026-10-01T23:55:50.821Z",
          "expiresAt": "2027-03-30T23:55:50.821Z",
          "inseeCode": "80021",
          "year": 2022,
          "epciCode": "248000531",
          "propertyTaxRate": 55.87,
          "landTaxRate": 62.98,
          "wasteTaxRate": 8.53,
          "housingTaxRate": 32.78,
          "secondaryHomeSurcharge": false,
          "secondaryHomeSurchargeRate": null
        },
        "… (5 éléments)"
      ],
      "propertyTaxRateChange": {
        "from": 2021,
        "to": 2025,
        "points": 0.13
      }
    },
    "crime": {
      "year": 2025,
      "highlights": [
        {
          "sourceCode": "ssmsi",
          "fetchedAt": "2026-10-01T23:55:50.823Z",
          "expiresAt": "2027-03-30T23:55:50.823Z",
          "id": 146,
          "inseeCode": "80021",
          "year": 2025,
          "indicator": "Destructions et dégradations volontaires",
          "countUnit": "Infraction",
          "count": 2042,
          "ratePerThousand": 14.9653,
          "isPublished": true
        },
        {
          "sourceCode": "ssmsi",
          "fetchedAt": "2026-10-01T23:55:50.823Z",
          "expiresAt": "2027-03-30T23:55:50.823Z",
          "id": 142,
          "inseeCode": "80021",
          "year": 2025,
          "indicator": "Cambriolages de logement",
          "countUnit": "Infraction",
          "count": 168,
          "ratePerThousand": 2.1381,
          "isPublished": true
        },
        "… (5 éléments)"
      ],
      "all": [
        {
          "sourceCode": "ssmsi",
          "fetchedAt": "2026-10-01T23:55:50.823Z",
          "expiresAt": "2027-03-30T23:55:50.823Z",
          "id": 1,
          "inseeCode": "80021",
          "year": 2016,
          "indicator": "Violences physiques intrafamiliales",
          "countUnit": "Victime",
          "count": 362,
          "ratePerThousand": 2.7064,
          "isPublished": true
        },
        {
          "sourceCode": "ssmsi",
          "fetchedAt": "2026-10-01T23:55:50.823Z",
          "expiresAt": "2027-03-30T23:55:50.823Z",
          "id": 15,
          "inseeCode": "80021",
          "year": 2016,
          "indicator": "Escroqueries et fraudes aux moyens de paiement",
          "countUnit": "Victime",
          "count": 559,
          "ratePerThousand": 4.1793,
          "isPublished": true
        },
        "… (150 éléments)"
      ]
    },
    "notCovered": [
      "Part de locations Airbnb (pas de donnée officielle)",
      "Vie associative (fichier RNA non interrogeable par API)"
    ]
  },
  "mobility": {
    "transit": {
      "stopsWithin800m": 65,
      "byMode": {
        "bus": [
          {
            "sourceCode": "overpass",
            "fetchedAt": "2026-10-01T23:55:50.815Z",
            "expiresAt": "2026-10-31T23:55:50.815Z",
            "externalId": "osm:node/2424967116",
            "name": "Hôtel de Ville",
            "mode": "bus",
            "network": null,
            "latitude": 49.892914,
            "longitude": 2.295433,
            "distanceM": 119
          },
          {
            "sourceCode": "overpass",
            "fetchedAt": "2026-10-01T23:55:50.815Z",
            "expiresAt": "2026-10-31T23:55:50.815Z",
            "externalId": "osm:node/2424971351",
            "name": "Jacobins",
            "mode": "bus",
            "network": null,
            "latitude": 49.892071,
            "longitude": 2.298393,
            "distanceM": 124
          },
          "… (3 éléments)"
        ]
      },
      "gtfsFeeds": [
        {
          "sourceCode": "transport_gouv",
          "fetchedAt": "2026-10-01T23:55:50.817Z",
          "expiresAt": "2026-10-08T23:55:50.817Z",
          "datasetId": "6033a87b4e276fd6499986bf",
          "inseeCode": "80021",
          "title": "Réseau urbain Ametis",
          "publisher": "Ametis",
          "gtfsUrl": "https://www.data.gouv.fr/api/1/datasets/r/5bc8b7dc-0d4e-48e7-b2ec-eccfe3702c19",
          "isAvailable": true,
          "coverageLevel": "epci",
          "updatedAt": "2026-09-14T12:18:46.000Z"
        },
        {
          "sourceCode": "transport_gouv",
          "fetchedAt": "2026-10-01T23:55:50.817Z",
          "expiresAt": "2026-10-08T23:55:50.817Z",
          "datasetId": "66970a3d58c639f7658e70c8",
          "inseeCode": "80021",
          "title": "Réseau interurbain - Somme (80)",
          "publisher": "Région Hauts-de-France",
          "gtfsUrl": "https://www.data.gouv.fr/api/1/datasets/r/429d30fb-ba6e-4e90-ad82-6d589a98cbfd",
          "isAvailable": true,
          "coverageLevel": "departement",
          "updatedAt": "2026-08-31T08:10:00.000Z"
        },
        "… (4 éléments)"
      ],
      "note": "Derniers départs du soir et service du dimanche : à calculer sur les GTFS (traitement batch, hors API)"
    },
    "charging": {
      "pointsWithin2km": 35,
      "fastChargers": 22,
      "nearest": [
        {
          "sourceCode": "irve",
          "fetchedAt": "2026-10-01T23:55:50.816Z",
          "expiresAt": "2026-10-08T23:55:50.816Z",
          "pdcId": "FRBMPE1336",
          "stationName": "Bump - OTERA - Amiens - OTERA AMIENS",
          "operatorName": "Bump",
          "inseeCode": "80021",
          "powerKw": 3.6,
          "connectors": [
            "2"
          ],
          "isFree": false,
          "accessCondition": "Accès libre",
          "openingHours": "24/7",
          "latitude": 49.894067,
          "longitude": 2.295753,
          "distanceM": 169
        },
        {
          "sourceCode": "irve",
          "fetchedAt": "2026-10-01T23:55:50.816Z",
          "expiresAt": "2026-10-08T23:55:50.816Z",
          "pdcId": "FRBMPE2561",
          "stationName": "Bump - OTERA - Amiens - OTERA AMIENS",
          "operatorName": "Bump",
          "inseeCode": "80021",
          "powerKw": 3.6,
          "connectors": [
            "2"
          ],
          "isFree": false,
          "accessCondition": "Accès libre",
          "openingHours": "24/7",
          "latitude": 49.894067,
          "longitude": 2.295753,
          "distanceM": 169
        },
        "… (5 éléments)"
      ]
    },
    "parking": [],
    "cycling": {
      "cycle_infrastructure_within_1km": {
        "value": 11328,
        "unit": "m"
      },
      "nearest_cycle_infrastructure": {
        "value": 170,
        "unit": "m"
      }
    },
    "notCovered": [
      "Tarifs et zones de stationnement résident sur voirie"
    ]
  },
  "connectivity": {
    "fixed": {
      "sourceCode": "arcep_fixe",
      "fetchedAt": "2026-10-01T23:55:50.812Z",
      "expiresAt": "2026-12-30T23:55:50.812Z",
      "inseeCode": "80021",
      "periodDate": "2026-06-30",
      "premises": 91983,
      "ftthEligible": 89735,
      "cableEligible": 0,
      "copperEligible": 91982,
      "thdRadioEligible": 0,
      "fixed4gEligible": 91788,
      "satelliteEligible": 91976,
      "ftthRate": 97.56,
      "scope": "commune",
      "note": "Taux communal d’éligibilité : l’éligibilité exacte du logement n’est pas publiée en API"
    },
    "mobile": [
      {
        "operator": "Bouygues Telecom",
        "sitesWithin1km": 8,
        "nearest4gM": 224,
        "nearest5gM": 342,
        "nearest5g3500M": 342
      },
      {
        "operator": "Free Mobile",
        "sitesWithin1km": 6,
        "nearest4gM": 350,
        "nearest5gM": 350,
        "nearest5g3500M": 350
      },
      "… (4 éléments)"
    ],
    "note": "Couverture intérieure non mesurée : indicateurs de proximité des sites ARCEP par opérateur",
    "notCovered": [
      "Réception TNT et satellite à l’adresse"
    ]
  },
  "generatedAt": "2026-10-02T00:00:37.864Z"
}
```

## Sources et traçabilité

### `GET /sources`

Registre des sources : statut de vérification, TTL, clé requise.

**Requête**

```http
GET /api/sources
```

**Réponse** `200`

```json
[
  {
    "code": "ademe_dpe",
    "name": "DPE logements existants (ADEME)",
    "domain": "building",
    "baseUrl": "https://data.ademe.fr/data-fair/api/v1/datasets/dpe03existant",
    "ttlSeconds": 2592000,
    "requiresKey": false,
    "status": "verified",
    "notes": null
  },
  {
    "code": "bdnb",
    "name": "Base de Données Nationale des Bâtiments",
    "domain": "building",
    "baseUrl": "https://api.bdnb.io/v1/bdnb",
    "ttlSeconds": 7776000,
    "requiresKey": false,
    "status": "verified",
    "notes": null
  },
  {
    "code": "cerema_dvf_plus",
    "name": "Cerema DVF+ API",
    "domain": "building",
    "baseUrl": "https://apidf-preprod.cerema.fr",
    "ttlSeconds": 2592000,
    "requiresKey": false,
    "status": "obsolete",
    "notes": "HTTP 503 (preprod), domaine prod non résolu au 2026-10-02"
  },
  "… (43 éléments)"
]
```

### `GET /sources/fetch-logs`

Journal des collectes (filtres `source`, `status`, `target`, pagination).

**Requête**

```http
GET /api/sources/fetch-logs?status=skipped&limit=2
```

**Réponse** `200`

```json
{
  "total": 9,
  "page": 1,
  "limit": 2,
  "items": [
    {
      "id": 55,
      "sourceCode": "sirene",
      "targetKey": "commune:80021:bakeries",
      "status": "skipped",
      "itemsCount": 0,
      "httpStatus": null,
      "durationMs": 0,
      "errorMessage": "Clé API absente : renseigner INSEE_SIRENE_API_KEY dans .env",
      "fetchedAt": "2026-10-02T00:00:37.720Z",
      "expiresAt": null
    },
    {
      "id": 54,
      "sourceCode": "esante_fhir",
      "targetKey": "postcode:80000",
      "status": "skipped",
      "itemsCount": 0,
      "httpStatus": null,
      "durationMs": 0,
      "errorMessage": "Clé API absente : renseigner ESANTE_API_KEY dans .env",
      "fetchedAt": "2026-10-02T00:00:37.719Z",
      "expiresAt": null
    }
  ]
}
```

## Erreurs

### `GET /addresses/:id`

Adresse pivot + commune + parcelle (géométrie GeoJSON).

**Requête**

```http
GET /api/addresses/999999
```

**Réponse** `404`

```json
{
  "statusCode": 404,
  "message": "Adresse 999999 inconnue",
  "error": "Not Found"
}
```

### `POST /addresses`

Géocode une adresse (texte `q` ou `lat`/`lon`) et l’enregistre avec sa commune et sa parcelle. `?force=true` ignore le cache.

**Requête**

```http
POST /api/addresses
Content-Type: application/json

{
  "q": "zz"
}
```

**Réponse** `400`

```json
{
  "statusCode": 400,
  "message": [
    "q must be longer than or equal to 3 characters"
  ],
  "error": "Bad Request"
}
```

