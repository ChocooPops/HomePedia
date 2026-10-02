import { join } from 'path';
import { DataSourceOptions } from 'typeorm';
import configuration from '../config/configuration';

/** Options partagées par l'application Nest et la CLI TypeORM (migrations). */
export function buildTypeOrmOptions(): DataSourceOptions {
  const { db } = configuration();
  return {
    type: 'mariadb',
    host: db.host,
    port: db.port,
    username: db.user,
    password: db.password,
    database: db.name,
    charset: 'utf8mb4_unicode_ci',
    timezone: 'Z',
    // MariaDB : fonctions ST_* (et non GeomFromText) pour lire/écrire les géométries.
    legacySpatialSupport: false,
    entities: [join(__dirname, '..', '**', '*.entities.{ts,js}')],
    migrations: [join(__dirname, 'migrations', '*.{ts,js}')],
    synchronize: false,
    logging: db.logging,
    supportBigNumbers: true,
    bigNumberStrings: false,
    extra: { connectionLimit: 10 },
  };
}
