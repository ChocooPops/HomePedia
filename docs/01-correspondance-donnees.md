# HomePedia : correspondance données métier → sources → tables

> Étape 1 du backend. Endpoints testés le 2026-10-02 (requêtes réelles sur Amiens, INSEE 80021).
> Les noms de tables sont **provisoires** : ils seront figés à l'étape 2 (schéma MariaDB).

Légende : ✅ couvert · 🟡 partiel / indicateur indirect / couverture géographique incomplète · ❌ non couvert par une source ouverte connue

---

## 1. Vérification des endpoints

| Source | Endpoint testé | Résultat | Action |
|---|---|---|---|
| Géocodage BAN (Géoplateforme) | `data.geopf.fr/geocodage/search`, `/reverse` | ✅ 200 | — |
| API Géo | `geo.api.gouv.fr/communes` | ✅ 200 | — |
| Cadastre API Carto | `apicarto.ign.fr/api/cadastre/parcelle` | ✅ 200 | — |
| GPU API Carto | `apicarto.ign.fr/api/gpu/zone-urba` | ✅ 200 | Utiliser aussi `/gpu/prescription-surf\|lin\|pct` et `/gpu/assiette-sup-s` |
| WMS / WFS Géoplateforme | `data.geopf.fr/wms-r/wms`, `/wfs/ows` | ✅ 200 | — |
| **Itinéraire / isochrone IGN** *(absent de la liste)* | `data.geopf.fr/navigation/itineraire`, `/isochrone` | ✅ 200 | **À ajouter** : seule source gratuite de temps de trajet |
| DPE ADEME | `data-fair/api/v1/datasets/dpe03existant/lines` | ✅ 200 | Jeu « virtuel » de 230 champs, dont `id_rnb`, `identifiant_ban`, `hauteur_sous_plafond` et `annee_construction` |
| RNB | `rnb-api.beta.gouv.fr/api/alpha/buildings/` | ✅ 200 | Toujours en `alpha` : le contrat d'API peut changer |
| BDNB | `api.bdnb.io/v1/bdnb/donnees/...` | ✅ 200 | Accès libre limité en débit (clé facultative) |
| **Cerema DVF+** | `apidf-preprod.cerema.fr` | ⚠️ **HS** : 302 vers `/swagger` puis **503**, et `/dvf_opendata/mutations/` en 503 | **Obsolète ou instable.** Le domaine prod `apidf.cerema.fr` **ne se résout pas**. Repli : DVF géolocalisé CSV |
| DVF géolocalisé | `files.data.gouv.fr/geo-dvf/latest/csv/` | ✅ 200 | Import fichier (par département et par année), pas d'API |
| Géorisques v1 | `georisques.gouv.fr/api/v1/...` | ✅ 200 sur `gaspar/catnat`, `gaspar/risques`, `gaspar/azi`, `gaspar/pprn`, `gaspar/tim`, `radon`, `zonage_sismique`, `cavites`, `mvt`, `ssp`, `ssp/casias`, `installations_classees`, `resultats_rapport_risque` | ⚠️ **`/rga` renvoie 200 avec un corps vide** : on passe par `resultats_rapport_risque`. **`/tri`, `/canalisations` et `/remontees_nappes` renvoient 404** |
| Hub'Eau qualité eau potable | `/qualite_eau_potable/resultats_dis` | ✅ 206 | 206 = réponse paginée, c'est normal |
| Hub'Eau nappes | `/niveaux_nappes/stations` | ✅ 206 | idem |
| VigiEau | `api.vigieau.gouv.fr/api/zones` | ✅ 200 | — |
| Open-Meteo prévisions et archive | `api.open-meteo.com`, `archive-api.open-meteo.com` | ✅ 200 | — |
| **Open-Meteo Climate** *(absent de la liste)* | `climate-api.open-meteo.com/v1/climate` | ✅ 200 | **À ajouter** pour les projections 2050 (CMIP6), gratuit et sans clé |
| Météo-France | `portail-api.meteofrance.fr` | ✅ portail joignable | Clé requise, pas testable sans compte |
| Atmo France | `admindata.atmo-france.org/api/doc` | ✅ 200 | Compte requis |
| PVGIS | `re.jrc.ec.europa.eu/api/v5_3/PVcalc` | ✅ 200 | v5_3 OK (v5_2 répond encore) |
| Overpass OSM | `overpass-api.de/api/interpreter` | ⚠️ **406 sans `User-Agent`**, 200 avec | Envoyer un `User-Agent` identifiable, limiter à 1 req/s environ |
| OpenSky | `opensky-network.org/api/states/all` | ✅ 200 (anonyme) | Instantané temps réel uniquement, quota anonyme faible. Pas un historique de couloirs aériens |
| ODRE | `odre.opendatasoft.com/api/explore/v2.1/` | ✅ 200 | Identifiants des jeux à préciser (`postes-electriques-rte`, lignes aériennes, parc éolien…) |
| **Enedis** | `data.enedis.fr/api/explore/v2.1/` | ❌ **404**, redirige vers `opendata.enedis.fr`, puis **410** (« couche de compatibilité ne supporte pas ») | **Obsolète.** Enedis a migré vers **data-fair** : `https://opendata.enedis.fr/data-fair/api/v1/datasets` (200) |
| GRDF | `opendata.grdf.fr/api/explore/v2.1/` | ✅ 200 | `cartographie-du-reseau-grdf-en-service` disponible |
| Recherche d'entreprises | `/near_point` | ✅ 200 | — |
| Sirene 3.11 | `api.insee.fr/api-sirene/3.11/` | 🔑 401 | Chemin valide (nouveau portail INSEE), clé requise |
| Annuaire Éducation | `data.education.gouv.fr/.../fr-en-annuaire-education` | ✅ 200 | — |
| Annuaire Santé FHIR | `gateway.api.esante.gouv.fr/fhir/` | 🔑 403 | Clé requise (`ESANTE-API-KEY`) |
| CAF | `data.caf.fr/api/explore/v2.1/` | ✅ 200 | ⚠️ **Statistiques agrégées seulement** (pas de liste géolocalisée de crèches) |
| INSEE Melodi | `api.insee.fr/melodi/catalog/all` | ✅ 200 | Catalogue accessible sans clé |
| REI / fiscalité locale | `data.economie.gouv.fr/api/explore/v2.1/` | ✅ 200 | Jeux « délibérations de fiscalité directe locale » disponibles. Id REI exact à fixer |
| Monuments historiques | `data.culture.gouv.fr/.../liste-des-immeubles-proteges...` | ✅ 200 | — |
| transport.data.gouv | `/api/datasets` | ✅ 200 | — |
| data.gouv.fr | `/api/1/datasets/?q=` | ✅ 200 | ⚠️ La recherche plein texte est peu fiable : on référencera les jeux **par identifiant**, pas par recherche |

---

## 2. Correspondance données métier → sources → tables

Tables transverses (toutes les tables métier en dépendent) : `commune`, `address` (pivot), `parcel`, `data_source` (source, TTL par défaut), `fetch_log` (traçabilité des collectes), `raw_payload` (réponse brute en JSON).
Chaque ligne métier porte `source_id`, `fetched_at` et `expires_at`.

### 2.1 Nuisances invisibles à la visite (module `nuisance`)

| Donnée | Source(s) | Table(s) | Couv. | Remarque |
|---|---|---|---|---|
| Bruit nocturne (bars, livraisons, fret de nuit) | Overpass (`amenity=bar\|pub\|nightclub`, `landuse=industrial`, entrepôts) ; WFS Géoplateforme, cartes de bruit stratégiques (type C, nuit, indicateur Ln) ; GTFS fret (non) | `nuisance_poi`, `noise_exposure` | 🟡 | Cartes de bruit limitées aux grands axes et agglomérations. Les livraisons de nuit ne sont pas couvertes |
| Couloirs aériens, altitude de survol | WFS/WMS **PEB** (plans d'exposition au bruit) ; OpenSky (instantané) | `noise_exposure`, `flight_observation` | 🟡 | OpenSky ne donne qu'un instantané. Un échantillonnage périodique (cron) permettrait d'estimer des fréquences et altitudes moyennes, mais l'historique est réservé aux comptes chercheurs |
| Cloches, coqs, chiens, séchoirs à grain | Overpass (`amenity=place_of_worship` + `building=church`, `landuse=farmyard`, `man_made=silo`, `craft=agricultural_engines`) | `nuisance_poi` | 🟡 | Simple proximité. Aucune donnée sur l'animal ou la sonnerie |
| Odeurs (STEP, élevages, épandage, agroalimentaire) | Géorisques `installations_classees` (élevages ICPE, IAA) ; Overpass (`man_made=wastewater_plant`) ; Sirene / recherche-entreprises (NAF 10.xx, 01.4x) | `nuisance_poi`, `risk_site` | 🟡 | Plans d'épandage non publics : ❌ |
| Pollution lumineuse | data.gouv « Pollution lumineuse – radiance » (raster, couverture régionale) | `nuisance_indicator` | 🟡 | Pas d'API nationale. Import raster ponctuel |
| Lignes haute tension | ODRE (lignes aériennes RTE) ; Overpass (`power=line`) | `nuisance_poi` (géométrie linéaire) | ✅ | — |
| Antennes relais | ANFR, données des installations radioélectriques de plus de 5 W (fichier data.gouv) | `nuisance_poi` | ✅ | Fichier national mensuel. Cartoradio n'a pas d'API |
| Éoliennes | ODRE (parc éolien) ; Overpass (`generator:source=wind`) | `nuisance_poi` | ✅ | Projets en instruction : voir §2.9 |
| Stade, salle de concert, marché | Overpass (`leisure=stadium`, `amenity=music_venue\|theatre\|marketplace`) | `nuisance_poi` | ✅ | Jours de marché présents seulement si `opening_hours` est renseigné |

### 2.2 Faune et nature (rattaché au module `risk`, sous-domaine biologique, et au module `geo` pour la protection)

| Donnée | Source(s) | Table(s) | Couv. | Remarque |
|---|---|---|---|---|
| Moustique tigre | Ministère de la Santé, liste annuelle des départements colonisés | `bio_risk` (par département) | 🟡 | Pas d'API, saisie annuelle manuelle |
| Frelons asiatiques | — | — | ❌ | Uniquement des jeux locaux (Lorient, Amiens Métropole…) |
| Termites | Arrêtés préfectoraux (jeux DDT ponctuels sur data.gouv) | `bio_risk` | 🟡 | Couverture nationale absente |
| Mérule | — | — | ❌ | Arrêtés très rares, aucune base |
| Rats, pigeons, punaises de lit | — | — | ❌ | **Candidat pour la source textuelle** (voir §4) |
| Sangliers | — | — | ❌ | Statistiques de chasse départementales seulement |
| Loups | OFB / réseau loup-lynx, « Aire de présence détectée du loup » (data.gouv) | `bio_risk` | ✅ | Maille communale ou 10 km |
| Tiques, Lyme | Santé publique France (incidence régionale, publications) | — | ❌ | Pas de jeu exploitable |
| Pollens dominants | Atmo France (indices pollens) | `pollen_index` | ✅ | Compte requis |
| Arbres classés, haies protégées | GPU `prescription-surf\|lin\|pct` (EBC, éléments de paysage L151-19/23) ; IGN « Haies » (WFS) | `plu_prescription`, `nature_feature` | 🟡 | Les « arbres remarquables » ne sont publiés que localement |

### 2.3 Climat et microclimat (module `climate`)

| Donnée | Source(s) | Table(s) | Couv. | Remarque |
|---|---|---|---|---|
| Ensoleillement réel (orientation, masques, soleil d'hiver) | PVGIS (`PVcalc`, `seriescalc`, masque d'horizon topographique) | `solar_potential` | 🟡 | PVGIS intègre le relief mais **pas les bâtiments voisins**. Orientation du logement inconnue |
| Îlot de chaleur, nuits tropicales | Open-Meteo archive (nb de nuits avec Tmin ≥ 20 °C) ; Cerema LCZ « zones climatiques locales » (data.gouv, environ 90 agglos) | `climate_stat`, `climate_zone` | 🟡 | Maille Open-Meteo d'environ 10 km, trop grossière pour l'îlot de chaleur. Les LCZ compensent en ville |
| Brouillard | Open-Meteo (`visibility`, prévisions seulement) ; Météo-France (stations) | `climate_stat` | 🟡 | Climatologie du brouillard via Météo-France (clé) |
| Gel, vent, enneigement | Open-Meteo archive (`temperature_2m_min`, `wind_speed_10m_max`, `snowfall_sum`, `snow_depth`) | `climate_stat` | ✅ | Agrégats calculés sur 10 ans |
| Projections climatiques 2050 | **Open-Meteo Climate API** (CMIP6) ; DRIAS (Météo-France, fichiers) | `climate_projection` | ✅ | Source à ajouter à la liste |
| Qualité de l'air | Atmo France (indice ATMO) | `air_quality_index` | ✅ | — |

### 2.4 Risques peu connus (module `risk`)

| Donnée | Source(s) | Table(s) | Couv. | Remarque |
|---|---|---|---|---|
| Retrait-gonflement des argiles | Géorisques `resultats_rapport_risque` (`/rga` ne renvoie rien) | `risk_assessment` | ✅ | — |
| Radon | Géorisques `radon` | `risk_assessment` | ✅ | Classe 1 à 3 par commune |
| Cavités, anciennes mines et carrières | Géorisques `cavites`, `mvt` ; rapport de risque (volet minier) | `risk_site` | ✅ | — |
| Sols pollués | Géorisques `ssp`, `ssp/casias`, `ssp/instructions` | `risk_site` | ✅ | — |
| Remontée de nappe | Géorisques `resultats_rapport_risque` ; Hub'Eau nappes (niveaux) | `risk_assessment`, `groundwater_level` | ✅ | `/remontees_nappes` renvoie 404 |
| Feux de forêt, débroussaillement | Géorisques `gaspar/risques`, `gaspar/pprn` ; OLD (jeux départementaux data.gouv) | `risk_assessment`, `risk_zone` | 🟡 | Zonage OLD national incomplet |
| Recul du trait de côte | Cerema, indicateur national de l'érosion côtière (WFS Géolittoral / data.gouv) | `risk_zone` | 🟡 | Hors liste, à valider |
| Sites Seveso | Géorisques `installations_classees` (champ statut Seveso) | `risk_site` | ✅ | — |
| Canalisations de gaz / matières dangereuses | Géorisques rapport de risque ; GRDF cartographie réseau ; jeux DREAL | `risk_site` | 🟡 | `/canalisations` renvoie 404. Couverture à vérifier via le rapport |
| Inondation (PPRI, AZI) | Géorisques `gaspar/azi`, `gaspar/pprn` | `risk_zone` | ✅ | — |
| Sismicité | Géorisques `zonage_sismique` | `risk_assessment` | ✅ | — |

### 2.5 Eau et énergie (modules `water` et `energy`)

| Donnée | Source(s) | Table(s) | Couv. | Remarque |
|---|---|---|---|---|
| Qualité de l'eau (nitrates, pesticides, PFAS, dureté) | Hub'Eau `qualite_eau_potable/resultats_dis` (par commune / UDI) | `water_quality_result` | ✅ | PFAS mesurés seulement depuis 2023 et pas partout |
| Arrêtés sécheresse | VigiEau `/api/zones` | `drought_restriction` | ✅ | TTL court (1 jour) |
| Assainissement collectif ou fosse septique | SISPEA (services d'assainissement non collectif, data.gouv) | `sanitation_info` | 🟡 | On sait si la commune a un SPANC, **pas si l'adresse est raccordée** |
| Raccordement gaz | GRDF `cartographie-du-reseau-grdf-en-service` | `energy_network_access` | 🟡 | Proximité du réseau ≠ raccordement effectif |
| Réseau de chaleur | France Chaleur Urbaine (tracés, data.gouv) | `energy_network_access` | ✅ | — |
| Potentiel solaire du toit | PVGIS ; BDNB (surface et type de toiture) | `solar_potential` | 🟡 | Pente et orientation réelles du toit inconnues |
| Coupures électriques | — | — | ❌ | Enedis ne publie pas d'historique de coupures par adresse. Consommations par commune disponibles via data-fair |

### 2.6 Connectivité (nouveau module proposé : `connectivity`)

| Donnée | Source(s) | Table(s) | Couv. | Remarque |
|---|---|---|---|---|
| Fibre réellement raccordable | ARCEP, IPE / « Ma connexion internet » (fichier national par immeuble) | `connectivity_fixed` | ✅ | Import fichier (plusieurs Go), jointure par adresse BAN |
| Couverture 4G/5G intérieure par opérateur | ARCEP « Mon réseau mobile » (cartes de couverture par opérateur) | `connectivity_mobile` | 🟡 | La couverture **intérieure** est une estimation de l'ARCEP, pas une mesure |
| Réception TNT et satellite | — | — | ❌ | Pas de données ouvertes exploitables |

### 2.7 Vie quotidienne (modules `services` et `mobility`)

| Donnée | Source(s) | Table(s) | Couv. | Remarque |
|---|---|---|---|---|
| Temps d'accès au premier médecin | Annuaire Santé FHIR (localisation des généralistes) + **IGN itinéraire** | `service_place`, `travel_time` | 🟡 | « Accepte de nouveaux patients » : ❌, aucune donnée ouverte |
| Urgences, maternité | FINESS (fichier data.gouv, catégories d'établissements) | `service_place` | ✅ | — |
| Pharmacie de garde | — | — | ❌ | Seulement des jeux locaux. Localisation des pharmacies via FINESS : ✅ |
| Boulangerie ouverte le dimanche | Recherche-entreprises / Sirene (NAF 10.71C) ; Overpass (`opening_hours`) | `service_place` | 🟡 | Horaires du dimanche renseignés de façon partielle dans OSM |
| Derniers transports du soir, service du dimanche | transport.data.gouv (GTFS) | `transit_stop`, `transit_service_stat` | ✅ | Calcul lourd (parsing GTFS) : bon candidat pour Spark |
| Trajet domicile-travail aux heures de pointe | IGN itinéraire (sans trafic) | `travel_time` | 🟡 | Aucune source gratuite avec trafic temps réel |
| Carte scolaire (école de secteur) | — | — | ❌ | Secteurs publiés seulement par quelques départements (collèges) |
| École, IPS, taille des classes | Annuaire Éducation ; data.education (IPS écoles/collèges, effectifs et nombre de classes) | `school` | ✅ | — |
| Cantine | Registre national des cantines (ma-cantine, data.gouv) | `school` | 🟡 | Présence et qualité déclarées, couverture partielle |
| Crèches | Overpass (`amenity=childcare\|kindergarten`) ; Sirene (NAF 88.91A) ; CAF (taux de couverture par commune) | `service_place`, `socio_indicator` | 🟡 | monenfant.fr n'a pas d'API |
| Pistes cyclables | transport.data.gouv (aménagements cyclables) ; Overpass | `cycle_path` | ✅ | — |
| Bornes de recharge | transport.data.gouv (IRVE consolidé) | `charging_station` | ✅ | — |
| Stationnement résident | transport.data.gouv (base nationale des lieux de stationnement) | `parking_facility` | 🟡 | Les tarifs et zones résidents ne sont pas centralisés |

### 2.8 Voisinage et social (module `socio`)

| Donnée | Source(s) | Table(s) | Couv. | Remarque |
|---|---|---|---|---|
| Âge moyen | INSEE Melodi (recensement) | `socio_indicator` | ✅ | — |
| Turnover | INSEE Melodi (ancienneté d'emménagement) ; DVF (taux de rotation des ventes) | `socio_indicator` | ✅ | — |
| Résidences secondaires | INSEE Melodi | `socio_indicator` | ✅ | — |
| Part d'Airbnb | data.gouv « Meublés de tourisme par commune » | `socio_indicator` | 🟡 | Pas de données Airbnb officielles. Inside Airbnb couvre quelques villes |
| Logements vacants | Melodi ; jeu MTE « Logements vacants du parc privé » (LOVAC) | `socio_indicator` | ✅ | — |
| Évolution des prix sur 5 à 10 ans | DVF géolocalisé (calcul) | `dvf_mutation`, `price_index` | ✅ | Agrégation par commune/IRIS, en batch Spark |
| Criminalité, cambriolages | SSMSI, base statistique communale de la délinquance (data.gouv) | `crime_stat` | ✅ | Valeurs masquées en dessous d'un seuil pour les petites communes |
| Vie associative | RNA (data.gouv, fichier national) | `socio_indicator` | ✅ | Nombre d'associations actives par commune |

### 2.9 Projets futurs (module `geo`)

| Donnée | Source(s) | Table(s) | Couv. | Remarque |
|---|---|---|---|---|
| Projets urbains (tram, rocade, ZAC, entrepôt, méthaniseur, éoliennes) | Géorisques `installations_classees` (ICPE en projet) ; GPU (OAP, secteurs de projet) | `plu_prescription`, `risk_site` | ❌/🟡 | **Pas de base nationale des projets.** Seuls des indices partiels existent |
| Zonage PLU des terrains voisins | GPU `zone-urba` (requête avec buffer) | `plu_zone` | ✅ | — |
| Emplacements réservés | GPU `prescription-surf` (type 05) | `plu_prescription` | ✅ | — |
| Périmètre Monuments historiques | GPU `assiette-sup-s` (SUP AC1) ; data.culture (liste des MH) | `public_easement`, `monument` | ✅ | — |

### 2.10 Fiscalité et coûts cachés (module `socio`, sous-domaine fiscalité)

| Donnée | Source(s) | Table(s) | Couv. | Remarque |
|---|---|---|---|---|
| Taxe foncière et évolution du taux | REI (data.economie) | `local_tax_rate` | ✅ | Historique annuel par commune |
| Majoration résidence secondaire | data.economie « Délibérations de fiscalité directe locale » | `local_tax_rate` | ✅ | — |
| Charges et procédures de copropriété | RNIC (registre des copropriétés, data.gouv) | `condominium` | 🟡 | Le RNIC donne lots, syndic et procédures (mandat ad hoc, administration provisoire). Le **montant des charges** n'y figure pas |
| Coût d'assurance selon les risques | — | — | ❌ | Aucune donnée. Possibilité : calculer un *score de risque* à partir de `risk_*` (indicateur maison, à documenter comme tel) |
| Encadrement des loyers | data.gouv (jeux par ville : Paris, Lille, Lyon, Montpellier, Bordeaux…) | `rent_control_zone` | 🟡 | Hétérogène, une ville à la fois |
| Interdiction de louer les passoires (DPE G puis F) | DPE ADEME + calendrier légal (G 2025, F 2028, E 2034) | `dpe_certificate` (+ règle calculée) | ✅ | — |

### 2.11 Le bâtiment (module `building`)

| Donnée | Source(s) | Table(s) | Couv. | Remarque |
|---|---|---|---|---|
| Amiante, plomb | Année de construction (BDNB, DPE, RNB) → règle (plomb : avant 1949 ; amiante : permis avant le 01/07/1997) | `building` (+ règle calculée) | 🟡 | Présomption réglementaire, pas un diagnostic |
| Isolation phonique | — | — | ❌ | Seule une approximation (année, matériaux BDNB) est possible |
| Ascenseur, accessibilité PMR | — | — | ❌ | Non publiés pour le logement privé |
| Inondation de cave et parking | Géorisques (remontée de nappe, AZI, PPRI) | `risk_assessment` | 🟡 | Exposition de la zone, pas de l'immeuble |
| Hauteur sous plafond | DPE ADEME (`hauteur_sous_plafond`) | `dpe_certificate` | ✅ | Si un DPE existe pour le logement |
| Luminosité | PVGIS + hauteur des bâtiments voisins (BDNB/RNB) | `solar_potential`, `building` | 🟡 | Indicateur calculé approximatif |
| Historique CatNat de la commune | Géorisques `gaspar/catnat` | `catnat_decree` | ✅ | — |
| Identité du bâtiment (RNB, année, hauteur, matériaux, DPE) | RNB, BDNB, DPE (liés via `id_rnb`) | `building`, `dpe_certificate` | ✅ | `id_rnb` sert de clé de rapprochement |

---

## 3. Données non couvertes (récapitulatif)

Aucune source ouverte connue : **frelons asiatiques** (hors jeux locaux), **mérule**, **rats / pigeons / punaises de lit**, **sangliers**, **tiques / Lyme**, **coupures électriques**, **réception TNT/satellite**, **médecin acceptant de nouveaux patients**, **pharmacie de garde** (hors jeux locaux), **carte scolaire nationale**, **trafic aux heures de pointe**, **base nationale des projets urbains**, **coût d'assurance**, **isolation phonique**, **ascenseur / PMR**, **plans d'épandage**, **livraisons de nuit**.

---

## 4. Points à valider avant l'étape 2

1. **Sources ajoutées à la liste** : Open-Meteo Climate, IGN itinéraire/isochrone, ARCEP (fibre et mobile), ANFR (antennes), FINESS, SSMSI, RNIC, RNA, LOVAC, Cerema LCZ, France Chaleur Urbaine, OFB loup. Au total environ 45 sources, dans la fourchette 12–50 du sujet.
2. **Cerema DVF+ abandonné** au profit de DVF géolocalisé (CSV) tant que l'API reste en 503.
3. **Enedis** : on passe par l'API data-fair (`opendata.enedis.fr/data-fair/api/v1`).
4. **Module `connectivity`** ajouté aux 10 modules demandés (ou rattachement à `services`).
5. **Exigences du sujet Epitech absentes de la demande** :
   - *Base non relationnelle obligatoire* : MariaDB seule ne suffit pas. Proposition : **MongoDB** pour les réponses brutes (`raw_payload`) et les données textuelles, avec MariaDB pour le modèle normalisé.
   - *Source textuelle obligatoire* traitée par IA (analyse de sentiment, extraction) : aucune source listée n'en fournit. Proposition : avis d'habitants sur les communes (ville-ideale.fr, toléré par le sujet) avec extraction de mentions (rats, punaises, bruit, insécurité…). Cela comble aussi une partie des ❌ du §3.
   - *Cluster Spark* : les traitements lourds (DVF → `price_index`, GTFS → `transit_service_stat`, fichiers ARCEP/ANFR) seront isolés pour être exécutés sur Spark ou Databricks, pas dans l'API.
6. **Accès aux données** : SQL écrit à la main et SQLAlchemy Core (détail dans le document 02), pour garder la main sur les types spatiaux MariaDB (`POINT`, `POLYGON`) et les `SPATIAL INDEX`.

---

## 5. Mise à jour après implémentation (2026-10-02)

L'implémentation a révélé d'autres écarts avec la liste de départ :

| Source | Constat | Solution retenue |
|---|---|---|
| Monuments historiques (`data.culture.gouv.fr`) | ⚠️ **Obsolète** : redirection vers `culture.data.gouv.fr`, page HTML sans API Opendatasoft | Même jeu (Ministère de la Culture) interrogé sur data.gouv.fr via l'**API tabulaire** (`tabular-api.data.gouv.fr`) |
| Cadastre API Carto | Une géométrie `Point` renvoie toujours 0 parcelle | Requête avec un carré de 12 m, puis choix de la parcelle contenant le point |
| Overpass | 406 si le User-Agent contient un contact factice (`example.com`), 504 fréquents en charge | User-Agent réaliste + bascule vers un miroir |
| Open-Meteo Climate | Facturation au volume : 6 modèles × 20 ans dépassent le quota par minute (429) | 3 modèles × 2 périodes de 10 ans, attente de la fenêtre suivante sur 429 |
| ODRE lignes RTE | Jeux `lignes-aeriennes-rte-nv` **sans géométrie** | Lignes haute tension via OSM (`power=line`) |
| Géorisques `/gaspar/pprn` | Ignore le filtre `code_insee` (renvoie toute la France) | Non utilisé ; PPR couverts par le rapport de risque et les AZI |
| BDNB | Pas de lien direct RNB dans `batiment_groupe_complet` | Passage par `batiment_construction?rnb_id=eq.…` |
| INSEE Melodi | Fonctionne **sans clé** (quota réduit) | Clé facultative (`INSEE_API_KEY`) |
| Fichiers nationaux (MH, RNIC, SSMSI, IRVE, stationnement) | Pas d'API dédiée | **API tabulaire data.gouv** : filtre par colonne sans télécharger le fichier |
| ANFR (antennes) | Archive ZIP mensuelle | Remplacé par les **sites mobiles ARCEP** (CSV, contient l'identifiant ANFR) |

**Noms de tables définitifs** (différences avec le §2) : `climate_stat` → `address_indicator` (domaine `climate`) ; `connectivity_fixed` → `fixed_coverage` ; `connectivity_mobile` → `mobile_site` ; `noise_exposure` → `nuisance_poi` (catégorie `airport_noise_plan`) ; `cycle_path` → indicateurs `address_indicator` (domaine `mobility`) ; `transit_service_stat` → `transit_feed` ; `nature_feature` → `plu_prescription` (EBC, éléments de paysage) ; ajout de `commune_risk_profile` et `nuisance_line`.

**Prévu au §2 mais pas encore implémenté** : LCZ Cerema (îlot de chaleur), pollution lumineuse (raster), encadrement des loyers, présence du loup (OFB), meublés de tourisme, RNA (vie associative), FINESS (maternités), assainissement (SISPEA), CAF petite enfance, Météo-France (brouillard). Les réponses de lecture de l'API signalent leurs principales lacunes dans un champ `notCovered`.

**Implémenté sans test réel faute de clé** : Atmo France, Annuaire Santé FHIR, Sirene 3.11 (code conforme à la documentation officielle, renvoie `skipped` tant que la clé est absente).

## Analyse de territoire : sources ajoutées

| Donnée métier | Source | Accès | Stockage |
|---|---|---|---|
| Régions, départements | API Géo | REST, sans clé | `region`, `department` |
| Contours des communes | API Géo (`geometry=contour`) | REST, sans clé | MongoDB `contours` |
| Contours des régions et départements | france-geojson (GitHub) | fichiers GeoJSON | MongoDB `contours` |
| Population depuis 1968 | INSEE Melodi `DS_POPULATIONS_HISTORIQUES` | REST, sans clé | `socio_indicator` (`municipal_population`) |
| Tranches d'âge | INSEE Melodi `DS_RP_POPULATION_PRINC` | REST, sans clé | `socio_indicator` (`age_*`, `share_age_*`) |
| Actifs, emploi, chômage (15-64 ans) | INSEE Melodi `DS_RP_EMPLOI_LR_PRINC` | REST, sans clé | `socio_indicator` (`unemployment_rate`, `activity_rate`…) |
| Logements vacants, résidences secondaires | INSEE Melodi `DS_RP_LOGEMENT_PRINC` | REST, sans clé | `socio_indicator` |
| Niveau de vie, pauvreté, Gini | INSEE Melodi `DS_FILOSOFI_CC` | REST, sans clé | `socio_indicator` (`median_living_standard`, `poverty_rate`, `gini_index`…) |
| Transactions d'un département | DVF géolocalisé, `…/{année}/departements/{dep}.csv.gz` | fichier | `dvf_mutation`, `price_index` |
| Consommation d'électricité et de gaz | Agence ORE (API data-fair, interrogée par commune) | REST, sans clé | `commune_energy_consumption` |
| Avis sur des lieux | Google Maps Places API (New) | clé payante, 5 avis par lieu | MongoDB `reviews` |
| Avis de quartiers et d'agences | MeilleursAgents | fichiers exportés à la main | MongoDB `reviews` |

Remarques : le chômage est celui du recensement (déclaratif), supérieur au taux au sens du BIT ; les mesures Filosofi
absentes pour une commune sont couvertes par le secret statistique ; les populations de 1968 à 1999 sont des populations
sans doubles comptes, celles d'après 2006 des populations municipales.
