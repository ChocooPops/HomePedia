import { MigrationInterface, QueryRunner } from 'typeorm';
import { readSqlFile } from '../sql-runner';

const TABLES_IN_DROP_ORDER = [
  'mobile_site', 'fixed_coverage', 'transit_feed', 'transit_stop', 'parking_facility', 'charging_station',
  'local_tax_rate', 'crime_stat', 'socio_indicator', 'travel_time', 'school', 'service_place',
  'electricity_consumption', 'energy_network_access', 'flight_observation', 'nuisance_line', 'nuisance_poi',
  'air_quality_index', 'solar_potential', 'climate_projection', 'drought_restriction', 'groundwater_station',
  'water_quality_result', 'bio_risk', 'risk_site', 'catnat_decree', 'commune_risk_profile', 'risk_assessment',
  'condominium', 'price_index', 'dvf_mutation', 'dpe_certificate', 'building', 'monument', 'public_easement',
  'plu_prescription', 'plu_zone', 'address_indicator', 'address', 'parcel', 'commune', 'raw_payload',
  'fetch_log', 'data_source',
];

/** Exécute src/database/sql/001_initial_schema.sql (fichier SQL de référence). */
export class InitialSchema1759363200000 implements MigrationInterface {
  name = 'InitialSchema1759363200000';

  public async up(queryRunner: QueryRunner): Promise<void> {
    for (const statement of readSqlFile('001_initial_schema.sql')) {
      await queryRunner.query(statement);
    }
  }

  public async down(queryRunner: QueryRunner): Promise<void> {
    for (const table of TABLES_IN_DROP_ORDER) {
      await queryRunner.query(`DROP TABLE IF EXISTS \`${table}\``);
    }
  }
}
