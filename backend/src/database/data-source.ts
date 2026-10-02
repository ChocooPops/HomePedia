import 'reflect-metadata';
import 'dotenv/config';
import { DataSource } from 'typeorm';
import { buildTypeOrmOptions } from './typeorm-options';

/** Point d'entrée de la CLI TypeORM (npm run migration:run). */
export default new DataSource(buildTypeOrmOptions());
