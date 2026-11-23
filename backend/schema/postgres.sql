-- Schéma PostgreSQL de HomePedia
-- Exécuté à chaque démarrage de l'API : utilisez IF NOT EXISTS, et ALTER TABLE pour modifier une table existante.

-- ---------------------------------------------------------------------------
-- GeoData (source : contours administratifs Etalab 2024)
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS regions (
    code  VARCHAR(3)   PRIMARY KEY,   -- code INSEE de la région
    name  VARCHAR(100) NOT NULL
);

CREATE TABLE IF NOT EXISTS departments (
    code         VARCHAR(3)   PRIMARY KEY,   -- code INSEE du département
    name         VARCHAR(100) NOT NULL,
    region_code  VARCHAR(3)   NOT NULL REFERENCES regions (code)
);

CREATE TABLE IF NOT EXISTS communes (
    code             VARCHAR(5)   PRIMARY KEY,   -- code INSEE de la commune
    name             VARCHAR(100) NOT NULL,
    department_code  VARCHAR(3)   NOT NULL REFERENCES departments (code)
);

CREATE INDEX IF NOT EXISTS idx_departments_region  ON departments (region_code);
CREATE INDEX IF NOT EXISTS idx_communes_department ON communes (department_code);

-- ---------------------------------------------------------------------------
-- Annonces immobilières (module annonces : scraping SeLoger, etc.)
-- ---------------------------------------------------------------------------

-- Résultats du géocodeur IGN (https://data.geopf.fr/geocodage), un par adresse.
-- address_key est l'adresse normalisée : une adresse déjà présente n'est jamais renvoyée au géocodeur.
-- Une adresse introuvable est enregistrée sans coordonnées, pour ne pas être redemandée.
CREATE TABLE IF NOT EXISTS geocodage (
    id           SERIAL        PRIMARY KEY,
    address_key  TEXT          NOT NULL UNIQUE,
    query        TEXT          NOT NULL,          -- texte envoyé au géocodeur
    label        TEXT,                            -- adresse trouvée
    score        DOUBLE PRECISION,                -- confiance, de 0 à 1
    result_type  VARCHAR(20),                     -- housenumber, street, municipality…
    housenumber  VARCHAR(20),
    street       TEXT,
    postcode     VARCHAR(5),
    city         TEXT,
    citycode     VARCHAR(5),                      -- code INSEE de la commune
    latitude     DOUBLE PRECISION,
    longitude    DOUBLE PRECISION,
    geocoded_at  TIMESTAMPTZ   NOT NULL DEFAULT now()
);

-- Une annonce est identifiée par son site d'origine et son identifiant sur ce site :
-- un nouveau scraping met à jour la ligne existante au lieu d'en créer une autre.
CREATE TABLE IF NOT EXISTS annonces (
    id                SERIAL        PRIMARY KEY,
    source            VARCHAR(30)   NOT NULL,     -- seloger…
    source_id         VARCHAR(64)   NOT NULL,     -- identifiant de l'annonce sur le site
    url               TEXT          NOT NULL,
    transaction_type  VARCHAR(10)   NOT NULL CHECK (transaction_type IN ('vente', 'location')),
    property_type     VARCHAR(20)   NOT NULL CHECK (property_type IN ('appartement', 'maison', 'autre')),
    price             NUMERIC(12, 2),             -- euros (loyer mensuel pour une location)
    rooms             SMALLINT,
    bedrooms          SMALLINT,
    surface_m2        NUMERIC(8, 2),
    floor             SMALLINT,                   -- 0 = rez-de-chaussée
    floor_label       VARCHAR(30),                -- libellé d'origine (« Étage 2/4 »)
    energy_class      CHAR(1)       CHECK (energy_class BETWEEN 'A' AND 'G'),
    street_number     VARCHAR(10),
    street            TEXT,
    postal_code       VARCHAR(5),
    city              TEXT,
    geocodage_id      INTEGER       REFERENCES geocodage (id) ON DELETE SET NULL,
    first_seen_at     TIMESTAMPTZ   NOT NULL DEFAULT now(),
    last_seen_at      TIMESTAMPTZ   NOT NULL DEFAULT now(),
    UNIQUE (source, source_id)
);

CREATE INDEX IF NOT EXISTS idx_annonces_geocodage   ON annonces (geocodage_id);
CREATE INDEX IF NOT EXISTS idx_annonces_postal_code ON annonces (postal_code);

CREATE INDEX IF NOT EXISTS idx_geocodage_position ON geocodage (latitude, longitude);
CREATE INDEX IF NOT EXISTS idx_geocodage_citycode ON geocodage (citycode);

-- Journal des scrapings : évite de repayer une recherche déjà faite récemment (zone sans annonce, erreur).
CREATE TABLE IF NOT EXISTS scrapes (
    id                SERIAL        PRIMARY KEY,
    source            VARCHAR(30)   NOT NULL,
    zone_level        VARCHAR(12)   NOT NULL,     -- france, region, departement, commune
    zone_code         VARCHAR(20)   NOT NULL,     -- code INSEE, ou identifiant de lieu du site
    transaction_type  VARCHAR(10)   NOT NULL,
    status            VARCHAR(10)   NOT NULL CHECK (status IN ('success', 'error')),
    found             INTEGER       NOT NULL DEFAULT 0,
    error             TEXT,
    scraped_at        TIMESTAMPTZ   NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_scrapes_zone ON scrapes (source, zone_level, zone_code, transaction_type, scraped_at);

-- Photo principale de l'annonce (première de la galerie sur la page de résultats).
ALTER TABLE annonces ADD COLUMN IF NOT EXISTS image_url TEXT;
