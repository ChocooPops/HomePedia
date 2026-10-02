-- =====================================================================
-- HomePedia : référentiel territorial (régions, départements),
-- consommation d'énergie à la commune (Agence ORE) et nouvelles sources.
-- Les contours GeoJSON et les avis sont stockés dans MongoDB.
-- =====================================================================

CREATE TABLE region (
  code            VARCHAR(3)   NOT NULL,
  name            VARCHAR(80)  NOT NULL,
  source_code     VARCHAR(48)  NOT NULL,
  fetched_at      DATETIME(3)  NOT NULL,
  expires_at      DATETIME(3)  NOT NULL,
  PRIMARY KEY (code),
  CONSTRAINT fk_region_source FOREIGN KEY (source_code) REFERENCES data_source (code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE department (
  code            VARCHAR(3)   NOT NULL,
  name            VARCHAR(80)  NOT NULL,
  region_code     VARCHAR(3)   NOT NULL,
  source_code     VARCHAR(48)  NOT NULL,
  fetched_at      DATETIME(3)  NOT NULL,
  expires_at      DATETIME(3)  NOT NULL,
  PRIMARY KEY (code),
  KEY idx_department_region (region_code),
  CONSTRAINT fk_department_source FOREIGN KEY (source_code) REFERENCES data_source (code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Une ligne par commune, année, énergie et grand secteur (les secteurs NAF détaillés sont agrégés).
CREATE TABLE commune_energy_consumption (
  id                  BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  insee_code          CHAR(5)      NOT NULL,
  year                SMALLINT UNSIGNED NOT NULL,
  energy              ENUM('electricity','gas') NOT NULL,
  sector              VARCHAR(32)  NOT NULL,
  sites               INT UNSIGNED NULL,
  consumption_mwh     DECIMAL(16,3) NULL,
  source_code         VARCHAR(48)  NOT NULL,
  fetched_at          DATETIME(3)  NOT NULL,
  expires_at          DATETIME(3)  NOT NULL,
  PRIMARY KEY (id),
  UNIQUE KEY uq_commune_energy (insee_code, year, energy, sector),
  CONSTRAINT fk_commune_energy_source FOREIGN KEY (source_code) REFERENCES data_source (code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

INSERT INTO data_source (code, name, domain, base_url, ttl_seconds, requires_key, status, notes) VALUES
('france_geojson',  'Contours des régions et départements (france-geojson)', 'geo',      'https://raw.githubusercontent.com/gregoiredavid/france-geojson/master', 15552000, 0, 'verified', 'Contours simplifiés ; ceux des communes viennent de l''API Géo'),
('agence_ore',      'Agence ORE - consommation d''électricité et de gaz par commune', 'energy', 'https://opendata.agenceore.fr/data-fair/api/v1',               15552000, 0, 'verified', 'Interrogé par commune via l''API data-fair, sans télécharger le CSV complet'),
('google_places',   'Google Maps - Places API (avis)',                       'reviews',  'https://places.googleapis.com/v1',                                       2592000, 1, 'untested', 'Clé payante ; 5 avis au plus par lieu'),
('meilleursagents', 'MeilleursAgents (fichiers exportés à la main)',         'reviews',  'import manuel',                                                          31536000, 0, 'verified', 'Pas d''API publique : import de fichiers');
