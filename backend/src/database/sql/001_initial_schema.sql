-- =====================================================================
-- HomePedia : schéma MariaDB initial (>= 10.6, testé sur 11.4)
-- Convention géospatiale : WGS84 (SRID 4326), WKT en ordre « lon lat ».
-- Chaque table métier porte source_code / fetched_at / expires_at
-- (traçabilité de la source et fraîcheur de la donnée).
-- Ce fichier est immuable une fois publié : toute évolution passe par
-- un nouveau fichier 00X_*.sql + une nouvelle migration.
-- =====================================================================

-- ---------------------------------------------------------------------
-- 1. Socle : registre des sources, journal de collecte, réponses brutes
-- ---------------------------------------------------------------------

CREATE TABLE data_source (
  code            VARCHAR(48)  NOT NULL,
  name            VARCHAR(160) NOT NULL,
  domain          VARCHAR(32)  NOT NULL,
  base_url        VARCHAR(255) NOT NULL,
  ttl_seconds     INT UNSIGNED NOT NULL,
  requires_key    TINYINT(1)   NOT NULL DEFAULT 0,
  status          ENUM('verified','degraded','obsolete','untested') NOT NULL DEFAULT 'verified',
  notes           VARCHAR(500) NULL,
  PRIMARY KEY (code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE fetch_log (
  id              BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  source_code     VARCHAR(48)  NOT NULL,
  target_key      VARCHAR(191) NOT NULL,
  status          ENUM('success','error','skipped') NOT NULL,
  items_count     INT UNSIGNED NOT NULL DEFAULT 0,
  http_status     SMALLINT UNSIGNED NULL,
  duration_ms     INT UNSIGNED NOT NULL DEFAULT 0,
  error_message   VARCHAR(1000) NULL,
  fetched_at      DATETIME(3)  NOT NULL,
  expires_at      DATETIME(3)  NULL,
  PRIMARY KEY (id),
  KEY idx_fetch_log_freshness (source_code, target_key, status, fetched_at),
  KEY idx_fetch_log_fetched (fetched_at),
  CONSTRAINT fk_fetch_log_source FOREIGN KEY (source_code) REFERENCES data_source (code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE raw_payload (
  id              BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  fetch_log_id    BIGINT UNSIGNED NOT NULL,
  source_code     VARCHAR(48)  NOT NULL,
  target_key      VARCHAR(191) NOT NULL,
  payload         LONGTEXT     NOT NULL CHECK (JSON_VALID(payload)),
  created_at      DATETIME(3)  NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  PRIMARY KEY (id),
  KEY idx_raw_payload_target (source_code, target_key),
  CONSTRAINT fk_raw_payload_log FOREIGN KEY (fetch_log_id) REFERENCES fetch_log (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ---------------------------------------------------------------------
-- 2. Géo : commune, parcelle, adresse (entité pivot), urbanisme
-- ---------------------------------------------------------------------

CREATE TABLE commune (
  insee_code      CHAR(5)      NOT NULL,
  name            VARCHAR(120) NOT NULL,
  department_code VARCHAR(3)   NOT NULL,
  department_name VARCHAR(80)  NULL,
  region_code     VARCHAR(3)   NULL,
  region_name     VARCHAR(80)  NULL,
  epci_code       VARCHAR(9)   NULL,
  postal_codes    LONGTEXT     NULL CHECK (postal_codes IS NULL OR JSON_VALID(postal_codes)),
  population      INT UNSIGNED NULL,
  surface_ha      DECIMAL(12,2) NULL,
  latitude        DECIMAL(9,6) NOT NULL,
  longitude       DECIMAL(9,6) NOT NULL,
  center          POINT        NOT NULL,
  source_code     VARCHAR(48)  NOT NULL,
  fetched_at      DATETIME(3)  NOT NULL,
  expires_at      DATETIME(3)  NOT NULL,
  PRIMARY KEY (insee_code),
  KEY idx_commune_department (department_code),
  KEY idx_commune_region (region_code),
  KEY idx_commune_epci (epci_code),
  SPATIAL INDEX sidx_commune_center (center),
  CONSTRAINT fk_commune_source FOREIGN KEY (source_code) REFERENCES data_source (code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE parcel (
  idu             CHAR(14)     NOT NULL,
  insee_code      CHAR(5)      NOT NULL,
  prefix          CHAR(3)      NOT NULL DEFAULT '000',
  section         VARCHAR(2)   NOT NULL,
  numero          CHAR(4)      NOT NULL,
  sheet           SMALLINT UNSIGNED NULL,
  area_m2         INT UNSIGNED NULL,
  geom            GEOMETRY     NOT NULL,
  source_code     VARCHAR(48)  NOT NULL,
  fetched_at      DATETIME(3)  NOT NULL,
  expires_at      DATETIME(3)  NOT NULL,
  PRIMARY KEY (idu),
  KEY idx_parcel_insee (insee_code),
  SPATIAL INDEX sidx_parcel_geom (geom),
  CONSTRAINT fk_parcel_commune FOREIGN KEY (insee_code) REFERENCES commune (insee_code),
  CONSTRAINT fk_parcel_source FOREIGN KEY (source_code) REFERENCES data_source (code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Entité pivot : toutes les données « à l'adresse » s'y rattachent.
CREATE TABLE address (
  id              BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  ban_id          VARCHAR(64)  NULL,
  label           VARCHAR(255) NOT NULL,
  housenumber     VARCHAR(16)  NULL,
  street          VARCHAR(160) NULL,
  postcode        CHAR(5)      NULL,
  city            VARCHAR(120) NULL,
  insee_code      CHAR(5)      NOT NULL,
  latitude        DECIMAL(9,6) NOT NULL,
  longitude       DECIMAL(9,6) NOT NULL,
  location        POINT        NOT NULL,
  geocode_score   DECIMAL(5,4) NULL,
  geocode_type    VARCHAR(16)  NULL,
  parcel_idu      CHAR(14)     NULL,
  rnb_id          VARCHAR(12)  NULL,
  source_code     VARCHAR(48)  NOT NULL,
  fetched_at      DATETIME(3)  NOT NULL,
  expires_at      DATETIME(3)  NOT NULL,
  created_at      DATETIME(3)  NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  updated_at      DATETIME(3)  NOT NULL DEFAULT CURRENT_TIMESTAMP(3) ON UPDATE CURRENT_TIMESTAMP(3),
  PRIMARY KEY (id),
  UNIQUE KEY uq_address_ban (ban_id),
  KEY idx_address_insee (insee_code),
  KEY idx_address_parcel (parcel_idu),
  KEY idx_address_rnb (rnb_id),
  SPATIAL INDEX sidx_address_location (location),
  CONSTRAINT fk_address_commune FOREIGN KEY (insee_code) REFERENCES commune (insee_code),
  CONSTRAINT fk_address_parcel FOREIGN KEY (parcel_idu) REFERENCES parcel (idu) ON DELETE SET NULL,
  CONSTRAINT fk_address_source FOREIGN KEY (source_code) REFERENCES data_source (code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Indicateurs calculés à l'adresse (climat, mobilité, connectivité...) :
-- table « longue » pour éviter une colonne par indicateur.
CREATE TABLE address_indicator (
  id              BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  address_id      BIGINT UNSIGNED NOT NULL,
  domain          VARCHAR(32)  NOT NULL,
  indicator       VARCHAR(64)  NOT NULL,
  value_num       DECIMAL(18,4) NULL,
  value_text      VARCHAR(255) NULL,
  unit            VARCHAR(24)  NULL,
  details         LONGTEXT     NULL CHECK (details IS NULL OR JSON_VALID(details)),
  source_code     VARCHAR(48)  NOT NULL,
  fetched_at      DATETIME(3)  NOT NULL,
  expires_at      DATETIME(3)  NOT NULL,
  PRIMARY KEY (id),
  UNIQUE KEY uq_address_indicator (address_id, domain, indicator),
  KEY idx_address_indicator_domain (domain, indicator),
  CONSTRAINT fk_address_indicator_address FOREIGN KEY (address_id) REFERENCES address (id) ON DELETE CASCADE,
  CONSTRAINT fk_address_indicator_source FOREIGN KEY (source_code) REFERENCES data_source (code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE plu_zone (
  id              BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  gpu_id          VARCHAR(64)  NOT NULL,
  insee_code      CHAR(5)      NULL,
  document_id     VARCHAR(64)  NULL,
  label           VARCHAR(64)  NULL,
  label_long      VARCHAR(255) NULL,
  zone_type       VARCHAR(8)   NULL,
  approved_at     DATE         NULL,
  regulation_file VARCHAR(255) NULL,
  geom            GEOMETRY     NOT NULL,
  source_code     VARCHAR(48)  NOT NULL,
  fetched_at      DATETIME(3)  NOT NULL,
  expires_at      DATETIME(3)  NOT NULL,
  PRIMARY KEY (id),
  UNIQUE KEY uq_plu_zone_gpu (gpu_id),
  KEY idx_plu_zone_insee_type (insee_code, zone_type),
  SPATIAL INDEX sidx_plu_zone_geom (geom),
  CONSTRAINT fk_plu_zone_source FOREIGN KEY (source_code) REFERENCES data_source (code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Prescriptions PLU : emplacements réservés (type 05), EBC (01),
-- éléments de paysage / haies (07, 35), périmètres divers...
CREATE TABLE plu_prescription (
  id              BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  gpu_id          VARCHAR(64)  NOT NULL,
  insee_code      CHAR(5)      NULL,
  document_id     VARCHAR(64)  NULL,
  geometry_kind   ENUM('surface','line','point') NOT NULL,
  type_code       VARCHAR(4)   NULL,
  subtype_code    VARCHAR(4)   NULL,
  label           VARCHAR(255) NULL,
  nature          VARCHAR(255) NULL,
  geom            GEOMETRY     NOT NULL,
  source_code     VARCHAR(48)  NOT NULL,
  fetched_at      DATETIME(3)  NOT NULL,
  expires_at      DATETIME(3)  NOT NULL,
  PRIMARY KEY (id),
  UNIQUE KEY uq_plu_prescription_gpu (gpu_id),
  KEY idx_plu_prescription_type (insee_code, type_code),
  SPATIAL INDEX sidx_plu_prescription_geom (geom),
  CONSTRAINT fk_plu_prescription_source FOREIGN KEY (source_code) REFERENCES data_source (code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Servitudes d'utilité publique (AC1 = abords de Monuments historiques...)
CREATE TABLE public_easement (
  id              BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  gpu_id          VARCHAR(64)  NOT NULL,
  sup_type        VARCHAR(8)   NOT NULL,
  name            VARCHAR(255) NULL,
  assiette_type   VARCHAR(120) NULL,
  generator_id    VARCHAR(120) NULL,
  geom            GEOMETRY     NOT NULL,
  source_code     VARCHAR(48)  NOT NULL,
  fetched_at      DATETIME(3)  NOT NULL,
  expires_at      DATETIME(3)  NOT NULL,
  PRIMARY KEY (id),
  UNIQUE KEY uq_public_easement_gpu (gpu_id),
  KEY idx_public_easement_type (sup_type),
  SPATIAL INDEX sidx_public_easement_geom (geom),
  CONSTRAINT fk_public_easement_source FOREIGN KEY (source_code) REFERENCES data_source (code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE monument (
  reference       VARCHAR(16)  NOT NULL,
  name            VARCHAR(255) NULL,
  insee_code      CHAR(5)      NOT NULL,
  denomination    VARCHAR(255) NULL,
  protection_type VARCHAR(120) NULL,
  protection_text VARCHAR(1000) NULL,
  latitude        DECIMAL(9,6) NULL,
  longitude       DECIMAL(9,6) NULL,
  source_code     VARCHAR(48)  NOT NULL,
  fetched_at      DATETIME(3)  NOT NULL,
  expires_at      DATETIME(3)  NOT NULL,
  PRIMARY KEY (reference),
  KEY idx_monument_insee (insee_code),
  CONSTRAINT fk_monument_source FOREIGN KEY (source_code) REFERENCES data_source (code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ---------------------------------------------------------------------
-- 3. Bâtiment et marché
-- ---------------------------------------------------------------------

CREATE TABLE building (
  rnb_id              VARCHAR(12)  NOT NULL,
  bdnb_group_id       VARCHAR(32)  NULL,
  status              VARCHAR(24)  NULL,
  insee_code          CHAR(5)      NULL,
  construction_year   SMALLINT UNSIGNED NULL,
  height_m            DECIMAL(6,2) NULL,
  levels              SMALLINT UNSIGNED NULL,
  dwellings           SMALLINT UNSIGNED NULL,
  wall_material       VARCHAR(80)  NULL,
  roof_material       VARCHAR(80)  NULL,
  main_usage          VARCHAR(80)  NULL,
  dpe_class_bdnb      CHAR(1)      NULL,
  condo_registration  VARCHAR(16)  NULL,
  iris_code           CHAR(9)      NULL,
  footprint_m2        INT UNSIGNED NULL,
  ground_altitude_m   DECIMAL(7,2) NULL,
  latitude            DECIMAL(9,6) NOT NULL,
  longitude           DECIMAL(9,6) NOT NULL,
  location            POINT        NOT NULL,
  shape               GEOMETRY     NULL,
  source_code         VARCHAR(48)  NOT NULL,
  fetched_at          DATETIME(3)  NOT NULL,
  expires_at          DATETIME(3)  NOT NULL,
  PRIMARY KEY (rnb_id),
  KEY idx_building_bdnb (bdnb_group_id),
  KEY idx_building_insee_year (insee_code, construction_year),
  KEY idx_building_condo (condo_registration),
  SPATIAL INDEX sidx_building_location (location),
  CONSTRAINT fk_building_source FOREIGN KEY (source_code) REFERENCES data_source (code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE dpe_certificate (
  numero_dpe          VARCHAR(16)  NOT NULL,
  rnb_id              VARCHAR(12)  NULL,
  ban_id              VARCHAR(64)  NULL,
  address_label       VARCHAR(255) NULL,
  insee_code          CHAR(5)      NULL,
  issued_at           DATE         NULL,
  energy_class        CHAR(1)      NULL,
  ghg_class           CHAR(1)      NULL,
  energy_kwh_m2       DECIMAL(8,1) NULL,
  ghg_kg_m2           DECIMAL(8,1) NULL,
  construction_year   SMALLINT UNSIGNED NULL,
  construction_period VARCHAR(24)  NULL,
  building_type       VARCHAR(24)  NULL,
  living_area_m2      DECIMAL(8,1) NULL,
  ceiling_height_m    DECIMAL(4,2) NULL,
  heating_energy      VARCHAR(80)  NULL,
  annual_cost_eur     DECIMAL(10,2) NULL,
  latitude            DECIMAL(9,6) NULL,
  longitude           DECIMAL(9,6) NULL,
  source_code         VARCHAR(48)  NOT NULL,
  fetched_at          DATETIME(3)  NOT NULL,
  expires_at          DATETIME(3)  NOT NULL,
  PRIMARY KEY (numero_dpe),
  KEY idx_dpe_rnb (rnb_id),
  KEY idx_dpe_ban (ban_id),
  KEY idx_dpe_insee_class (insee_code, energy_class),
  KEY idx_dpe_latlon (latitude, longitude),
  CONSTRAINT fk_dpe_source FOREIGN KEY (source_code) REFERENCES data_source (code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Une ligne DVF = un local (ou une parcelle) d'une mutation.
CREATE TABLE dvf_mutation (
  id                  BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  row_hash            CHAR(40)     NOT NULL,
  mutation_id         VARCHAR(24)  NOT NULL,
  mutation_date       DATE         NOT NULL,
  nature              VARCHAR(48)  NOT NULL,
  price_eur           DECIMAL(15,2) NULL,
  insee_code          CHAR(5)      NOT NULL,
  parcel_idu          CHAR(14)     NULL,
  address_label       VARCHAR(255) NULL,
  property_type       VARCHAR(48)  NULL,
  built_area_m2       INT UNSIGNED NULL,
  rooms               SMALLINT UNSIGNED NULL,
  land_area_m2        INT UNSIGNED NULL,
  lots_count          SMALLINT UNSIGNED NULL,
  latitude            DECIMAL(9,6) NULL,
  longitude           DECIMAL(9,6) NULL,
  source_code         VARCHAR(48)  NOT NULL,
  fetched_at          DATETIME(3)  NOT NULL,
  expires_at          DATETIME(3)  NOT NULL,
  PRIMARY KEY (id),
  UNIQUE KEY uq_dvf_row (row_hash),
  KEY idx_dvf_insee_date (insee_code, mutation_date),
  KEY idx_dvf_mutation (mutation_id),
  KEY idx_dvf_parcel (parcel_idu),
  KEY idx_dvf_latlon (latitude, longitude),
  CONSTRAINT fk_dvf_source FOREIGN KEY (source_code) REFERENCES data_source (code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Agrégat calculé à partir de dvf_mutation (prix au m² par commune/année/type).
CREATE TABLE price_index (
  insee_code          CHAR(5)      NOT NULL,
  year                SMALLINT UNSIGNED NOT NULL,
  property_type       VARCHAR(48)  NOT NULL,
  sales_count         INT UNSIGNED NOT NULL,
  median_price_m2     DECIMAL(10,2) NULL,
  mean_price_m2       DECIMAL(10,2) NULL,
  q1_price_m2         DECIMAL(10,2) NULL,
  q3_price_m2         DECIMAL(10,2) NULL,
  computed_at         DATETIME(3)  NOT NULL,
  PRIMARY KEY (insee_code, year, property_type)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE condominium (
  registration_number VARCHAR(16)  NOT NULL,
  name                VARCHAR(255) NULL,
  address_label       VARCHAR(255) NULL,
  insee_code          CHAR(5)      NULL,
  total_lots          INT UNSIGNED NULL,
  housing_lots        INT UNSIGNED NULL,
  parking_lots        INT UNSIGNED NULL,
  syndic_type         VARCHAR(32)  NULL,
  syndic_name         VARCHAR(255) NULL,
  mandate_status      VARCHAR(64)  NULL,
  mandate_end_date    DATE         NULL,
  construction_period VARCHAR(32)  NULL,
  regulation_date     DATE         NULL,
  is_aided            TINYINT(1)   NULL,
  priority_district   VARCHAR(120) NULL,
  cadastral_refs      LONGTEXT     NULL CHECK (cadastral_refs IS NULL OR JSON_VALID(cadastral_refs)),
  latitude            DECIMAL(9,6) NULL,
  longitude           DECIMAL(9,6) NULL,
  source_code         VARCHAR(48)  NOT NULL,
  fetched_at          DATETIME(3)  NOT NULL,
  expires_at          DATETIME(3)  NOT NULL,
  PRIMARY KEY (registration_number),
  KEY idx_condominium_insee (insee_code),
  CONSTRAINT fk_condominium_source FOREIGN KEY (source_code) REFERENCES data_source (code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ---------------------------------------------------------------------
-- 4. Risques
-- ---------------------------------------------------------------------

-- Une ligne par aléa et par adresse (rapport Géorisques + OLD).
CREATE TABLE risk_assessment (
  id                  BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  address_id          BIGINT UNSIGNED NOT NULL,
  hazard_code         VARCHAR(48)  NOT NULL,
  category            ENUM('natural','technological','regulatory') NOT NULL,
  label               VARCHAR(160) NOT NULL,
  present             TINYINT(1)   NOT NULL,
  commune_status      VARCHAR(80)  NULL,
  address_status      VARCHAR(80)  NULL,
  details             LONGTEXT     NULL CHECK (details IS NULL OR JSON_VALID(details)),
  source_code         VARCHAR(48)  NOT NULL,
  fetched_at          DATETIME(3)  NOT NULL,
  expires_at          DATETIME(3)  NOT NULL,
  PRIMARY KEY (id),
  UNIQUE KEY uq_risk_assessment (address_id, hazard_code),
  KEY idx_risk_assessment_hazard (hazard_code, present),
  CONSTRAINT fk_risk_assessment_address FOREIGN KEY (address_id) REFERENCES address (id) ON DELETE CASCADE,
  CONSTRAINT fk_risk_assessment_source FOREIGN KEY (source_code) REFERENCES data_source (code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE commune_risk_profile (
  insee_code          CHAR(5)      NOT NULL,
  radon_class         TINYINT UNSIGNED NULL,
  seismic_zone        VARCHAR(32)  NULL,
  known_risks         LONGTEXT     NULL CHECK (known_risks IS NULL OR JSON_VALID(known_risks)),
  flood_atlases       LONGTEXT     NULL CHECK (flood_atlases IS NULL OR JSON_VALID(flood_atlases)),
  source_code         VARCHAR(48)  NOT NULL,
  fetched_at          DATETIME(3)  NOT NULL,
  expires_at          DATETIME(3)  NOT NULL,
  PRIMARY KEY (insee_code),
  CONSTRAINT fk_commune_risk_profile_source FOREIGN KEY (source_code) REFERENCES data_source (code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE catnat_decree (
  code_national       VARCHAR(24)  NOT NULL,
  insee_code          CHAR(5)      NOT NULL,
  hazard_label        VARCHAR(160) NOT NULL,
  event_start         DATE         NULL,
  event_end           DATE         NULL,
  decree_date         DATE         NULL,
  journal_date        DATE         NULL,
  source_code         VARCHAR(48)  NOT NULL,
  fetched_at          DATETIME(3)  NOT NULL,
  expires_at          DATETIME(3)  NOT NULL,
  PRIMARY KEY (code_national, insee_code),
  KEY idx_catnat_insee_date (insee_code, event_start),
  CONSTRAINT fk_catnat_source FOREIGN KEY (source_code) REFERENCES data_source (code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Sites ponctuels : ICPE / Seveso, sols pollués (SSP, CASIAS), cavités, mouvements de terrain.
CREATE TABLE risk_site (
  id                  BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  site_type           ENUM('icpe','casias','ssp','cavity','ground_movement') NOT NULL,
  external_id         VARCHAR(64)  NOT NULL,
  name                VARCHAR(255) NULL,
  insee_code          CHAR(5)      NULL,
  status              VARCHAR(80)  NULL,
  seveso_status       VARCHAR(48)  NULL,
  subtype             VARCHAR(120) NULL,
  details             LONGTEXT     NULL CHECK (details IS NULL OR JSON_VALID(details)),
  latitude            DECIMAL(9,6) NOT NULL,
  longitude           DECIMAL(9,6) NOT NULL,
  location            POINT        NOT NULL,
  source_code         VARCHAR(48)  NOT NULL,
  fetched_at          DATETIME(3)  NOT NULL,
  expires_at          DATETIME(3)  NOT NULL,
  PRIMARY KEY (id),
  UNIQUE KEY uq_risk_site (site_type, external_id),
  KEY idx_risk_site_insee (insee_code, site_type),
  SPATIAL INDEX sidx_risk_site_location (location),
  CONSTRAINT fk_risk_site_source FOREIGN KEY (source_code) REFERENCES data_source (code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Faune / risques biologiques : pas d'API nationale, alimentation manuelle ou par import.
CREATE TABLE bio_risk (
  id                  BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  scope               ENUM('commune','department') NOT NULL,
  area_code           VARCHAR(5)   NOT NULL,
  species             VARCHAR(48)  NOT NULL,
  status              VARCHAR(80)  NOT NULL,
  year                SMALLINT UNSIGNED NOT NULL,
  reference_url       VARCHAR(500) NULL,
  notes               VARCHAR(500) NULL,
  source_code         VARCHAR(48)  NOT NULL,
  fetched_at          DATETIME(3)  NOT NULL,
  expires_at          DATETIME(3)  NOT NULL,
  PRIMARY KEY (id),
  UNIQUE KEY uq_bio_risk (scope, area_code, species, year),
  CONSTRAINT fk_bio_risk_source FOREIGN KEY (source_code) REFERENCES data_source (code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ---------------------------------------------------------------------
-- 5. Eau
-- ---------------------------------------------------------------------

CREATE TABLE water_quality_result (
  id                  BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  insee_code          CHAR(5)      NOT NULL,
  sample_code         VARCHAR(24)  NOT NULL,
  parameter_code      VARCHAR(8)   NOT NULL,
  parameter_label     VARCHAR(255) NOT NULL,
  result_numeric      DECIMAL(16,6) NULL,
  result_text         VARCHAR(32)  NULL,
  unit                VARCHAR(24)  NULL,
  quality_limit       VARCHAR(64)  NULL,
  sampled_at          DATETIME     NOT NULL,
  network_name        VARCHAR(160) NULL,
  distributor         VARCHAR(160) NULL,
  physchem_compliance CHAR(1)      NULL,
  bacterio_compliance CHAR(1)      NULL,
  conclusion          VARCHAR(1000) NULL,
  source_code         VARCHAR(48)  NOT NULL,
  fetched_at          DATETIME(3)  NOT NULL,
  expires_at          DATETIME(3)  NOT NULL,
  PRIMARY KEY (id),
  UNIQUE KEY uq_water_quality (sample_code, parameter_code, insee_code),
  KEY idx_water_quality_param (insee_code, parameter_code, sampled_at),
  CONSTRAINT fk_water_quality_source FOREIGN KEY (source_code) REFERENCES data_source (code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE groundwater_station (
  code_bss            VARCHAR(32)  NOT NULL,
  bss_id              VARCHAR(16)  NULL,
  insee_code          CHAR(5)      NULL,
  commune_name        VARCHAR(120) NULL,
  altitude_m          DECIMAL(7,2) NULL,
  depth_m             DECIMAL(7,2) NULL,
  measures_count      INT UNSIGNED NULL,
  first_measure_date  DATE         NULL,
  last_measure_date   DATE         NULL,
  last_water_depth_m  DECIMAL(7,2) NULL,
  last_level_ngf_m    DECIMAL(7,2) NULL,
  latitude            DECIMAL(9,6) NOT NULL,
  longitude           DECIMAL(9,6) NOT NULL,
  location            POINT        NOT NULL,
  source_code         VARCHAR(48)  NOT NULL,
  fetched_at          DATETIME(3)  NOT NULL,
  expires_at          DATETIME(3)  NOT NULL,
  PRIMARY KEY (code_bss),
  KEY idx_groundwater_insee (insee_code),
  SPATIAL INDEX sidx_groundwater_location (location),
  CONSTRAINT fk_groundwater_source FOREIGN KEY (source_code) REFERENCES data_source (code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE drought_restriction (
  id                  BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  insee_code          CHAR(5)      NOT NULL,
  zone_id             INT UNSIGNED NOT NULL,
  zone_code           VARCHAR(32)  NULL,
  zone_name           VARCHAR(160) NULL,
  zone_type           VARCHAR(8)   NOT NULL,
  severity            VARCHAR(32)  NOT NULL,
  decree_start        DATE         NULL,
  decree_end          DATE         NULL,
  decree_url          VARCHAR(500) NULL,
  usages              LONGTEXT     NULL CHECK (usages IS NULL OR JSON_VALID(usages)),
  source_code         VARCHAR(48)  NOT NULL,
  fetched_at          DATETIME(3)  NOT NULL,
  expires_at          DATETIME(3)  NOT NULL,
  PRIMARY KEY (id),
  UNIQUE KEY uq_drought_zone (insee_code, zone_id, zone_type),
  KEY idx_drought_severity (insee_code, severity),
  CONSTRAINT fk_drought_source FOREIGN KEY (source_code) REFERENCES data_source (code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ---------------------------------------------------------------------
-- 6. Climat, air, soleil
-- ---------------------------------------------------------------------

CREATE TABLE climate_projection (
  id                  BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  address_id          BIGINT UNSIGNED NOT NULL,
  model               VARCHAR(48)  NOT NULL,
  period              VARCHAR(16)  NOT NULL,
  indicator           VARCHAR(48)  NOT NULL,
  value               DECIMAL(10,2) NULL,
  unit                VARCHAR(16)  NULL,
  source_code         VARCHAR(48)  NOT NULL,
  fetched_at          DATETIME(3)  NOT NULL,
  expires_at          DATETIME(3)  NOT NULL,
  PRIMARY KEY (id),
  UNIQUE KEY uq_climate_projection (address_id, model, period, indicator),
  CONSTRAINT fk_climate_projection_address FOREIGN KEY (address_id) REFERENCES address (id) ON DELETE CASCADE,
  CONSTRAINT fk_climate_projection_source FOREIGN KEY (source_code) REFERENCES data_source (code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE solar_potential (
  id                     BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  address_id             BIGINT UNSIGNED NOT NULL,
  tilt_deg               TINYINT UNSIGNED NOT NULL,
  azimuth_deg            SMALLINT     NOT NULL,
  yearly_kwh_per_kwp     DECIMAL(8,2) NULL,
  yearly_irradiation_kwh_m2 DECIMAL(8,2) NULL,
  winter_kwh_per_kwp     DECIMAL(8,2) NULL,
  monthly                LONGTEXT     NULL CHECK (monthly IS NULL OR JSON_VALID(monthly)),
  source_code            VARCHAR(48)  NOT NULL,
  fetched_at             DATETIME(3)  NOT NULL,
  expires_at             DATETIME(3)  NOT NULL,
  PRIMARY KEY (id),
  UNIQUE KEY uq_solar_potential (address_id, tilt_deg, azimuth_deg),
  CONSTRAINT fk_solar_address FOREIGN KEY (address_id) REFERENCES address (id) ON DELETE CASCADE,
  CONSTRAINT fk_solar_source FOREIGN KEY (source_code) REFERENCES data_source (code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE air_quality_index (
  id                  BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  insee_code          CHAR(5)      NOT NULL,
  index_type          ENUM('atmo','pollen') NOT NULL,
  index_date          DATE         NOT NULL,
  level_code          TINYINT UNSIGNED NULL,
  level_label         VARCHAR(48)  NULL,
  responsible         VARCHAR(120) NULL,
  details             LONGTEXT     NULL CHECK (details IS NULL OR JSON_VALID(details)),
  source_code         VARCHAR(48)  NOT NULL,
  fetched_at          DATETIME(3)  NOT NULL,
  expires_at          DATETIME(3)  NOT NULL,
  PRIMARY KEY (id),
  UNIQUE KEY uq_air_quality (insee_code, index_type, index_date),
  CONSTRAINT fk_air_quality_source FOREIGN KEY (source_code) REFERENCES data_source (code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ---------------------------------------------------------------------
-- 7. Nuisances
-- ---------------------------------------------------------------------

CREATE TABLE nuisance_poi (
  id                  BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  external_id         VARCHAR(64)  NOT NULL,
  category            VARCHAR(48)  NOT NULL,
  subcategory         VARCHAR(80)  NULL,
  name                VARCHAR(255) NULL,
  tags                LONGTEXT     NULL CHECK (tags IS NULL OR JSON_VALID(tags)),
  latitude            DECIMAL(9,6) NOT NULL,
  longitude           DECIMAL(9,6) NOT NULL,
  location            POINT        NOT NULL,
  source_code         VARCHAR(48)  NOT NULL,
  fetched_at          DATETIME(3)  NOT NULL,
  expires_at          DATETIME(3)  NOT NULL,
  PRIMARY KEY (id),
  UNIQUE KEY uq_nuisance_poi (source_code, external_id),
  KEY idx_nuisance_poi_category (category),
  SPATIAL INDEX sidx_nuisance_poi_location (location),
  CONSTRAINT fk_nuisance_poi_source FOREIGN KEY (source_code) REFERENCES data_source (code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Éléments linéaires : lignes haute tension, voies ferrées, autoroutes.
CREATE TABLE nuisance_line (
  id                  BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  external_id         VARCHAR(64)  NOT NULL,
  category            VARCHAR(48)  NOT NULL,
  subcategory         VARCHAR(80)  NULL,
  name                VARCHAR(255) NULL,
  tags                LONGTEXT     NULL CHECK (tags IS NULL OR JSON_VALID(tags)),
  geom                GEOMETRY     NOT NULL,
  source_code         VARCHAR(48)  NOT NULL,
  fetched_at          DATETIME(3)  NOT NULL,
  expires_at          DATETIME(3)  NOT NULL,
  PRIMARY KEY (id),
  UNIQUE KEY uq_nuisance_line (source_code, external_id),
  KEY idx_nuisance_line_category (category),
  SPATIAL INDEX sidx_nuisance_line_geom (geom),
  CONSTRAINT fk_nuisance_line_source FOREIGN KEY (source_code) REFERENCES data_source (code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE flight_observation (
  id                  BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  address_id          BIGINT UNSIGNED NOT NULL,
  observed_at         DATETIME     NOT NULL,
  icao24              VARCHAR(8)   NOT NULL,
  callsign            VARCHAR(12)  NULL,
  origin_country      VARCHAR(64)  NULL,
  altitude_m          DECIMAL(8,1) NULL,
  on_ground           TINYINT(1)   NOT NULL DEFAULT 0,
  velocity_ms         DECIMAL(7,2) NULL,
  distance_m          INT UNSIGNED NULL,
  latitude            DECIMAL(9,6) NOT NULL,
  longitude           DECIMAL(9,6) NOT NULL,
  source_code         VARCHAR(48)  NOT NULL,
  fetched_at          DATETIME(3)  NOT NULL,
  expires_at          DATETIME(3)  NOT NULL,
  PRIMARY KEY (id),
  UNIQUE KEY uq_flight_observation (address_id, icao24, observed_at),
  KEY idx_flight_address_time (address_id, observed_at),
  CONSTRAINT fk_flight_address FOREIGN KEY (address_id) REFERENCES address (id) ON DELETE CASCADE,
  CONSTRAINT fk_flight_source FOREIGN KEY (source_code) REFERENCES data_source (code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ---------------------------------------------------------------------
-- 8. Énergie
-- ---------------------------------------------------------------------

CREATE TABLE energy_network_access (
  id                  BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  address_id          BIGINT UNSIGNED NOT NULL,
  network_type        ENUM('heat','gas') NOT NULL,
  available           TINYINT(1)   NOT NULL,
  distance_m          INT UNSIGNED NULL,
  operator_name       VARCHAR(160) NULL,
  network_name        VARCHAR(160) NULL,
  details             LONGTEXT     NULL CHECK (details IS NULL OR JSON_VALID(details)),
  source_code         VARCHAR(48)  NOT NULL,
  fetched_at          DATETIME(3)  NOT NULL,
  expires_at          DATETIME(3)  NOT NULL,
  PRIMARY KEY (id),
  UNIQUE KEY uq_energy_network (address_id, network_type),
  CONSTRAINT fk_energy_network_address FOREIGN KEY (address_id) REFERENCES address (id) ON DELETE CASCADE,
  CONSTRAINT fk_energy_network_source FOREIGN KEY (source_code) REFERENCES data_source (code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE electricity_consumption (
  id                  BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  insee_code          CHAR(5)      NOT NULL,
  address_key         VARCHAR(191) NOT NULL,
  year                SMALLINT UNSIGNED NOT NULL,
  iris_code           CHAR(9)      NULL,
  dwellings           INT UNSIGNED NULL,
  total_mwh           DECIMAL(12,3) NULL,
  avg_per_site_mwh    DECIMAL(10,3) NULL,
  commune_avg_mwh     DECIMAL(10,3) NULL,
  source_code         VARCHAR(48)  NOT NULL,
  fetched_at          DATETIME(3)  NOT NULL,
  expires_at          DATETIME(3)  NOT NULL,
  PRIMARY KEY (id),
  UNIQUE KEY uq_electricity (insee_code, address_key, year),
  CONSTRAINT fk_electricity_source FOREIGN KEY (source_code) REFERENCES data_source (code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ---------------------------------------------------------------------
-- 9. Services, santé, éducation
-- ---------------------------------------------------------------------

CREATE TABLE service_place (
  id                  BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  external_id         VARCHAR(64)  NOT NULL,
  category            VARCHAR(48)  NOT NULL,
  name                VARCHAR(255) NULL,
  address_label       VARCHAR(255) NULL,
  insee_code          CHAR(5)      NULL,
  opening_hours       VARCHAR(255) NULL,
  details             LONGTEXT     NULL CHECK (details IS NULL OR JSON_VALID(details)),
  latitude            DECIMAL(9,6) NOT NULL,
  longitude           DECIMAL(9,6) NOT NULL,
  location            POINT        NOT NULL,
  source_code         VARCHAR(48)  NOT NULL,
  fetched_at          DATETIME(3)  NOT NULL,
  expires_at          DATETIME(3)  NOT NULL,
  PRIMARY KEY (id),
  UNIQUE KEY uq_service_place (source_code, external_id, category),
  KEY idx_service_place_category (category, insee_code),
  SPATIAL INDEX sidx_service_place_location (location),
  CONSTRAINT fk_service_place_source FOREIGN KEY (source_code) REFERENCES data_source (code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE school (
  uai                 CHAR(8)      NOT NULL,
  name                VARCHAR(255) NOT NULL,
  school_type         VARCHAR(48)  NULL,
  nature_label        VARCHAR(120) NULL,
  sector              VARCHAR(16)  NULL,
  insee_code          CHAR(5)      NULL,
  has_preschool       TINYINT(1)   NULL,
  has_elementary      TINYINT(1)   NULL,
  has_canteen         TINYINT(1)   NULL,
  priority_education  VARCHAR(32)  NULL,
  ips                 DECIMAL(5,1) NULL,
  ips_school_year     VARCHAR(9)   NULL,
  classes_count       SMALLINT UNSIGNED NULL,
  students_count      SMALLINT UNSIGNED NULL,
  avg_class_size      DECIMAL(4,1) NULL,
  headcount_year      VARCHAR(9)   NULL,
  latitude            DECIMAL(9,6) NOT NULL,
  longitude           DECIMAL(9,6) NOT NULL,
  location            POINT        NOT NULL,
  source_code         VARCHAR(48)  NOT NULL,
  fetched_at          DATETIME(3)  NOT NULL,
  expires_at          DATETIME(3)  NOT NULL,
  PRIMARY KEY (uai),
  KEY idx_school_insee_type (insee_code, school_type),
  SPATIAL INDEX sidx_school_location (location),
  CONSTRAINT fk_school_source FOREIGN KEY (source_code) REFERENCES data_source (code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE travel_time (
  id                  BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  address_id          BIGINT UNSIGNED NOT NULL,
  destination_kind    VARCHAR(48)  NOT NULL,
  profile             ENUM('car','pedestrian') NOT NULL,
  destination_label   VARCHAR(255) NULL,
  destination_lat     DECIMAL(9,6) NOT NULL,
  destination_lon     DECIMAL(9,6) NOT NULL,
  duration_s          INT UNSIGNED NULL,
  distance_m          INT UNSIGNED NULL,
  source_code         VARCHAR(48)  NOT NULL,
  fetched_at          DATETIME(3)  NOT NULL,
  expires_at          DATETIME(3)  NOT NULL,
  PRIMARY KEY (id),
  UNIQUE KEY uq_travel_time (address_id, destination_kind, profile),
  CONSTRAINT fk_travel_time_address FOREIGN KEY (address_id) REFERENCES address (id) ON DELETE CASCADE,
  CONSTRAINT fk_travel_time_source FOREIGN KEY (source_code) REFERENCES data_source (code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ---------------------------------------------------------------------
-- 10. Socio-démographie, sécurité, fiscalité
-- ---------------------------------------------------------------------

CREATE TABLE socio_indicator (
  id                  BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  insee_code          CHAR(5)      NOT NULL,
  indicator           VARCHAR(64)  NOT NULL,
  year                SMALLINT UNSIGNED NOT NULL,
  value               DECIMAL(18,4) NULL,
  unit                VARCHAR(24)  NULL,
  source_code         VARCHAR(48)  NOT NULL,
  fetched_at          DATETIME(3)  NOT NULL,
  expires_at          DATETIME(3)  NOT NULL,
  PRIMARY KEY (id),
  UNIQUE KEY uq_socio_indicator (insee_code, indicator, year),
  KEY idx_socio_indicator (indicator, year),
  CONSTRAINT fk_socio_indicator_source FOREIGN KEY (source_code) REFERENCES data_source (code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE crime_stat (
  id                  BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  insee_code          CHAR(5)      NOT NULL,
  year                SMALLINT UNSIGNED NOT NULL,
  indicator           VARCHAR(128) NOT NULL,
  count_unit          VARCHAR(32)  NULL,
  count               INT UNSIGNED NULL,
  rate_per_thousand   DECIMAL(10,4) NULL,
  is_published        TINYINT(1)   NOT NULL,
  source_code         VARCHAR(48)  NOT NULL,
  fetched_at          DATETIME(3)  NOT NULL,
  expires_at          DATETIME(3)  NOT NULL,
  PRIMARY KEY (id),
  UNIQUE KEY uq_crime_stat (insee_code, year, indicator),
  CONSTRAINT fk_crime_stat_source FOREIGN KEY (source_code) REFERENCES data_source (code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE local_tax_rate (
  insee_code              CHAR(5)      NOT NULL,
  year                    SMALLINT UNSIGNED NOT NULL,
  epci_code               VARCHAR(9)   NULL,
  property_tax_rate       DECIMAL(6,3) NULL,
  land_tax_rate           DECIMAL(6,3) NULL,
  waste_tax_rate          DECIMAL(6,3) NULL,
  housing_tax_rate        DECIMAL(6,3) NULL,
  secondary_home_surcharge TINYINT(1)  NULL,
  secondary_home_surcharge_rate DECIMAL(6,3) NULL,
  source_code             VARCHAR(48)  NOT NULL,
  fetched_at              DATETIME(3)  NOT NULL,
  expires_at              DATETIME(3)  NOT NULL,
  PRIMARY KEY (insee_code, year),
  CONSTRAINT fk_local_tax_source FOREIGN KEY (source_code) REFERENCES data_source (code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ---------------------------------------------------------------------
-- 11. Mobilité
-- ---------------------------------------------------------------------

CREATE TABLE charging_station (
  pdc_id              VARCHAR(64)  NOT NULL,
  station_name        VARCHAR(255) NULL,
  operator_name       VARCHAR(160) NULL,
  insee_code          CHAR(5)      NULL,
  power_kw            DECIMAL(7,2) NULL,
  connectors          LONGTEXT     NULL CHECK (connectors IS NULL OR JSON_VALID(connectors)),
  is_free             TINYINT(1)   NULL,
  access_condition    VARCHAR(80)  NULL,
  opening_hours       VARCHAR(255) NULL,
  latitude            DECIMAL(9,6) NOT NULL,
  longitude           DECIMAL(9,6) NOT NULL,
  location            POINT        NOT NULL,
  source_code         VARCHAR(48)  NOT NULL,
  fetched_at          DATETIME(3)  NOT NULL,
  expires_at          DATETIME(3)  NOT NULL,
  PRIMARY KEY (pdc_id),
  KEY idx_charging_insee (insee_code),
  SPATIAL INDEX sidx_charging_location (location),
  CONSTRAINT fk_charging_source FOREIGN KEY (source_code) REFERENCES data_source (code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE parking_facility (
  external_id         VARCHAR(64)  NOT NULL,
  name                VARCHAR(255) NULL,
  insee_code          CHAR(5)      NULL,
  places              INT UNSIGNED NULL,
  pmr_places          INT UNSIGNED NULL,
  ev_places           INT UNSIGNED NULL,
  is_free             TINYINT(1)   NULL,
  hourly_rate_eur     DECIMAL(6,2) NULL,
  resident_subscription_eur DECIMAL(8,2) NULL,
  latitude            DECIMAL(9,6) NOT NULL,
  longitude           DECIMAL(9,6) NOT NULL,
  location            POINT        NOT NULL,
  source_code         VARCHAR(48)  NOT NULL,
  fetched_at          DATETIME(3)  NOT NULL,
  expires_at          DATETIME(3)  NOT NULL,
  PRIMARY KEY (external_id),
  KEY idx_parking_insee (insee_code),
  SPATIAL INDEX sidx_parking_location (location),
  CONSTRAINT fk_parking_source FOREIGN KEY (source_code) REFERENCES data_source (code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE transit_stop (
  external_id         VARCHAR(64)  NOT NULL,
  name                VARCHAR(255) NULL,
  mode                VARCHAR(24)  NOT NULL,
  network             VARCHAR(160) NULL,
  latitude            DECIMAL(9,6) NOT NULL,
  longitude           DECIMAL(9,6) NOT NULL,
  location            POINT        NOT NULL,
  source_code         VARCHAR(48)  NOT NULL,
  fetched_at          DATETIME(3)  NOT NULL,
  expires_at          DATETIME(3)  NOT NULL,
  PRIMARY KEY (external_id),
  KEY idx_transit_stop_mode (mode),
  SPATIAL INDEX sidx_transit_stop_location (location),
  CONSTRAINT fk_transit_stop_source FOREIGN KEY (source_code) REFERENCES data_source (code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Flux GTFS couvrant une commune (l'analyse des horaires est faite hors API, sur Spark).
CREATE TABLE transit_feed (
  dataset_id          VARCHAR(64)  NOT NULL,
  insee_code          CHAR(5)      NOT NULL,
  title               VARCHAR(255) NOT NULL,
  publisher           VARCHAR(160) NULL,
  gtfs_url            VARCHAR(500) NULL,
  is_available        TINYINT(1)   NULL,
  coverage_level      VARCHAR(16)  NULL,
  updated_at          DATETIME     NULL,
  source_code         VARCHAR(48)  NOT NULL,
  fetched_at          DATETIME(3)  NOT NULL,
  expires_at          DATETIME(3)  NOT NULL,
  PRIMARY KEY (dataset_id, insee_code),
  KEY idx_transit_feed_insee (insee_code),
  CONSTRAINT fk_transit_feed_source FOREIGN KEY (source_code) REFERENCES data_source (code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ---------------------------------------------------------------------
-- 12. Connectivité
-- ---------------------------------------------------------------------

CREATE TABLE fixed_coverage (
  insee_code          CHAR(5)      NOT NULL,
  period_date         DATE         NOT NULL,
  premises            INT UNSIGNED NOT NULL,
  ftth_eligible       INT UNSIGNED NOT NULL,
  cable_eligible      INT UNSIGNED NOT NULL,
  copper_eligible     INT UNSIGNED NOT NULL,
  thd_radio_eligible  INT UNSIGNED NOT NULL,
  fixed_4g_eligible   INT UNSIGNED NOT NULL,
  satellite_eligible  INT UNSIGNED NOT NULL,
  ftth_rate           DECIMAL(5,2) NULL,
  source_code         VARCHAR(48)  NOT NULL,
  fetched_at          DATETIME(3)  NOT NULL,
  expires_at          DATETIME(3)  NOT NULL,
  PRIMARY KEY (insee_code),
  CONSTRAINT fk_fixed_coverage_source FOREIGN KEY (source_code) REFERENCES data_source (code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE mobile_site (
  operator_code       VARCHAR(8)   NOT NULL,
  site_number         VARCHAR(64)  NOT NULL,
  operator_name       VARCHAR(48)  NOT NULL,
  anfr_station_id     VARCHAR(24)  NULL,
  insee_code          CHAR(5)      NULL,
  has_2g              TINYINT(1)   NOT NULL DEFAULT 0,
  has_3g              TINYINT(1)   NOT NULL DEFAULT 0,
  has_4g              TINYINT(1)   NOT NULL DEFAULT 0,
  has_5g              TINYINT(1)   NOT NULL DEFAULT 0,
  has_5g_3500         TINYINT(1)   NOT NULL DEFAULT 0,
  latitude            DECIMAL(9,6) NOT NULL,
  longitude           DECIMAL(9,6) NOT NULL,
  location            POINT        NOT NULL,
  source_code         VARCHAR(48)  NOT NULL,
  fetched_at          DATETIME(3)  NOT NULL,
  expires_at          DATETIME(3)  NOT NULL,
  PRIMARY KEY (operator_code, site_number),
  KEY idx_mobile_site_insee (insee_code),
  SPATIAL INDEX sidx_mobile_site_location (location),
  CONSTRAINT fk_mobile_site_source FOREIGN KEY (source_code) REFERENCES data_source (code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ---------------------------------------------------------------------
-- 13. Registre des sources (TTL en secondes)
-- ---------------------------------------------------------------------

INSERT INTO data_source (code, name, domain, base_url, ttl_seconds, requires_key, status, notes) VALUES
('ban',               'Géocodage BAN (Géoplateforme)',          'geo',          'https://data.geopf.fr/geocodage',                         2592000, 0, 'verified', NULL),
('geo_api',           'API Géo (communes)',                     'geo',          'https://geo.api.gouv.fr',                                 7776000, 0, 'verified', NULL),
('apicarto_cadastre', 'API Carto - Cadastre',                   'geo',          'https://apicarto.ign.fr/api/cadastre',                    7776000, 0, 'verified', 'Recherche par point inopérante : on interroge avec un petit polygone'),
('apicarto_gpu',      'API Carto - Géoportail de l''urbanisme', 'geo',          'https://apicarto.ign.fr/api/gpu',                         2592000, 0, 'verified', NULL),
('monuments',         'Immeubles protégés MH (data.gouv tabular)', 'geo',       'https://tabular-api.data.gouv.fr',                        7776000, 0, 'verified', 'data.culture.gouv.fr a migré : API ODS d''origine obsolète'),
('rnb',               'Référentiel National des Bâtiments',     'building',     'https://rnb-api.beta.gouv.fr/api/alpha',                  2592000, 0, 'verified', 'API alpha'),
('bdnb',              'Base de Données Nationale des Bâtiments','building',     'https://api.bdnb.io/v1/bdnb',                             7776000, 0, 'verified', NULL),
('ademe_dpe',         'DPE logements existants (ADEME)',        'building',     'https://data.ademe.fr/data-fair/api/v1/datasets/dpe03existant', 2592000, 0, 'verified', NULL),
('dvf',               'DVF géolocalisé (fichiers CSV)',         'building',     'https://files.data.gouv.fr/geo-dvf/latest/csv',           15552000, 0, 'verified', NULL),
('cerema_dvf_plus',   'Cerema DVF+ API',                        'building',     'https://apidf-preprod.cerema.fr',                         2592000, 0, 'obsolete', 'HTTP 503 (preprod), domaine prod non résolu au 2026-10-02'),
('rnic',              'Registre des copropriétés (data.gouv tabular)', 'building', 'https://tabular-api.data.gouv.fr',                    7776000, 0, 'verified', NULL),
('georisques',        'Géorisques API v1',                      'risk',         'https://georisques.gouv.fr/api/v1',                       2592000, 0, 'degraded', '/rga vide, /tri /canalisations /remontees_nappes en 404 ; /gaspar/pprn ignore code_insee'),
('geopf_wfs',         'WFS Géoplateforme',                      'risk',         'https://data.geopf.fr/wfs/ows',                           7776000, 0, 'verified', NULL),
('manual',            'Saisie manuelle / import ponctuel',      'risk',         'local',                                                  31536000, 0, 'verified', NULL),
('hubeau_eau_potable','Hub''Eau qualité eau potable',           'water',        'https://hubeau.eaufrance.fr/api/v1/qualite_eau_potable',  604800, 0, 'verified', NULL),
('hubeau_nappes',     'Hub''Eau niveaux de nappes',             'water',        'https://hubeau.eaufrance.fr/api/v1/niveaux_nappes',       604800, 0, 'verified', NULL),
('vigieau',           'VigiEau restrictions sécheresse',        'water',        'https://api.vigieau.gouv.fr',                             86400, 0, 'verified', NULL),
('open_meteo_archive','Open-Meteo historique',                  'climate',      'https://archive-api.open-meteo.com/v1',                   31536000, 0, 'verified', NULL),
('open_meteo_climate','Open-Meteo projections CMIP6',           'climate',      'https://climate-api.open-meteo.com/v1',                   31536000, 0, 'verified', NULL),
('pvgis',             'PVGIS (JRC)',                            'climate',      'https://re.jrc.ec.europa.eu/api/v5_3',                    31536000, 0, 'verified', NULL),
('atmo',              'Atmo France (air, pollens)',             'climate',      'https://admindata.atmo-france.org/api',                   43200, 1, 'untested', 'Compte requis'),
('meteo_france',      'Météo-France portail API',               'climate',      'https://portail-api.meteofrance.fr',                      86400, 1, 'untested', 'Clé requise - non intégré (API climatologique asynchrone)'),
('overpass',          'OpenStreetMap Overpass',                 'nuisance',     'https://overpass-api.de/api/interpreter',                 2592000, 0, 'verified', 'User-Agent obligatoire (406 sinon)'),
('opensky',           'OpenSky Network',                        'nuisance',     'https://opensky-network.org/api',                         900, 0, 'verified', 'Instantané temps réel uniquement'),
('odre',              'ODRE (RTE)',                             'nuisance',     'https://odre.opendatasoft.com/api/explore/v2.1',          7776000, 0, 'degraded', 'Jeux de lignes RTE sans géométrie : lignes HT via OSM'),
('grdf',              'GRDF open data',                         'energy',       'https://opendata.grdf.fr/api/explore/v2.1',               7776000, 0, 'verified', NULL),
('enedis',            'Enedis open data (data-fair)',           'energy',       'https://opendata.enedis.fr/data-fair/api/v1',             7776000, 0, 'verified', 'Ancienne API ODS v2.1 en 410'),
('fcu',               'France Chaleur Urbaine',                 'energy',       'https://france-chaleur-urbaine.beta.gouv.fr/api/v1',      2592000, 0, 'verified', NULL),
('recherche_entreprises','API Recherche d''entreprises',        'services',     'https://recherche-entreprises.api.gouv.fr',               2592000, 0, 'verified', NULL),
('sirene',            'INSEE Sirene 3.11',                      'services',     'https://api.insee.fr/api-sirene/3.11',                    2592000, 1, 'untested', 'Clé requise'),
('education',         'Annuaire et indicateurs Éducation',      'services',     'https://data.education.gouv.fr/api/explore/v2.1',         7776000, 0, 'verified', NULL),
('esante_fhir',       'Annuaire Santé FHIR',                    'services',     'https://gateway.api.esante.gouv.fr/fhir/v2',              2592000, 1, 'untested', 'Clé requise'),
('ign_navigation',    'IGN itinéraire / isochrone',             'services',     'https://data.geopf.fr/navigation',                        2592000, 0, 'verified', NULL),
('caf',               'CAF open data',                          'services',     'https://data.caf.fr/api/explore/v2.1',                    7776000, 0, 'verified', 'Statistiques agrégées uniquement'),
('insee_melodi',      'INSEE Melodi',                           'socio',        'https://api.insee.fr/melodi',                             15552000, 0, 'verified', NULL),
('fiscalite_locale',  'Fiscalité locale des particuliers (DGFiP)','socio',      'https://data.economie.gouv.fr/api/explore/v2.1',          15552000, 0, 'verified', NULL),
('ssmsi',             'SSMSI délinquance communale (data.gouv tabular)', 'socio', 'https://tabular-api.data.gouv.fr',                      15552000, 0, 'verified', NULL),
('transport_gouv',    'transport.data.gouv.fr',                 'mobility',     'https://transport.data.gouv.fr/api',                      604800, 0, 'verified', NULL),
('irve',              'Base nationale IRVE (data.gouv tabular)','mobility',     'https://tabular-api.data.gouv.fr',                        604800, 0, 'verified', NULL),
('bnls',              'Base nationale lieux de stationnement',  'mobility',     'https://tabular-api.data.gouv.fr',                        2592000, 0, 'verified', 'Non exhaustive'),
('arcep_fixe',        'ARCEP Ma connexion internet',            'connectivity', 'https://data.arcep.fr/fixe/maconnexioninternet',          7776000, 0, 'verified', NULL),
('arcep_mobile',      'ARCEP sites mobiles',                    'connectivity', 'https://data.arcep.fr/mobile/sites',                      7776000, 0, 'verified', NULL),
('computed',          'Calcul interne HomePedia',               'core',         'local',                                                  2592000, 0, 'verified', NULL);
