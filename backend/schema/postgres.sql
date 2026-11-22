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
