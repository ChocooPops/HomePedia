import { Column, Entity, Index, PrimaryColumn, PrimaryGeneratedColumn } from 'typeorm';
import { decimal, json, SourcedEntity } from '../../common/entities/sourced.entity';

@Entity('water_quality_result')
export class WaterQualityResultEntity extends SourcedEntity {
  @PrimaryGeneratedColumn({ type: 'bigint', unsigned: true })
  id: number;

  @Column({ name: 'insee_code', type: 'char', length: 5 })
  inseeCode: string;

  @Column({ name: 'sample_code', type: 'varchar', length: 24 })
  sampleCode: string;

  @Column({ name: 'parameter_code', type: 'varchar', length: 8 })
  parameterCode: string;

  @Column({ name: 'parameter_label', type: 'varchar', length: 255 })
  parameterLabel: string;

  @Column({ name: 'result_numeric', type: 'decimal', precision: 16, scale: 6, nullable: true, transformer: decimal })
  resultNumeric: number | null;

  @Column({ name: 'result_text', type: 'varchar', length: 32, nullable: true })
  resultText: string | null;

  @Column({ type: 'varchar', length: 24, nullable: true })
  unit: string | null;

  @Column({ name: 'quality_limit', type: 'varchar', length: 64, nullable: true })
  qualityLimit: string | null;

  @Column({ name: 'sampled_at', type: 'datetime' })
  sampledAt: Date;

  @Column({ name: 'network_name', type: 'varchar', length: 160, nullable: true })
  networkName: string | null;

  @Column({ type: 'varchar', length: 160, nullable: true })
  distributor: string | null;

  @Column({ name: 'physchem_compliance', type: 'char', length: 1, nullable: true })
  physchemCompliance: string | null;

  @Column({ name: 'bacterio_compliance', type: 'char', length: 1, nullable: true })
  bacterioCompliance: string | null;

  @Column({ type: 'varchar', length: 1000, nullable: true })
  conclusion: string | null;
}

@Entity('groundwater_station')
export class GroundwaterStationEntity extends SourcedEntity {
  @PrimaryColumn({ name: 'code_bss', type: 'varchar', length: 32 })
  codeBss: string;

  @Column({ name: 'bss_id', type: 'varchar', length: 16, nullable: true })
  bssId: string | null;

  @Column({ name: 'insee_code', type: 'char', length: 5, nullable: true })
  inseeCode: string | null;

  @Column({ name: 'commune_name', type: 'varchar', length: 120, nullable: true })
  communeName: string | null;

  @Column({ name: 'altitude_m', type: 'decimal', precision: 7, scale: 2, nullable: true, transformer: decimal })
  altitudeM: number | null;

  @Column({ name: 'depth_m', type: 'decimal', precision: 7, scale: 2, nullable: true, transformer: decimal })
  depthM: number | null;

  @Column({ name: 'measures_count', type: 'int', unsigned: true, nullable: true })
  measuresCount: number | null;

  @Column({ name: 'first_measure_date', type: 'date', nullable: true })
  firstMeasureDate: string | null;

  @Column({ name: 'last_measure_date', type: 'date', nullable: true })
  lastMeasureDate: string | null;

  @Column({ name: 'last_water_depth_m', type: 'decimal', precision: 7, scale: 2, nullable: true, transformer: decimal })
  lastWaterDepthM: number | null;

  @Column({ name: 'last_level_ngf_m', type: 'decimal', precision: 7, scale: 2, nullable: true, transformer: decimal })
  lastLevelNgfM: number | null;

  @Column({ type: 'decimal', precision: 9, scale: 6, transformer: decimal })
  latitude: number;

  @Column({ type: 'decimal', precision: 9, scale: 6, transformer: decimal })
  longitude: number;

  @Index({ spatial: true })
  @Column({ type: 'point', srid: 4326, select: false })
  location: string;
}

@Entity('drought_restriction')
export class DroughtRestrictionEntity extends SourcedEntity {
  @PrimaryGeneratedColumn({ type: 'bigint', unsigned: true })
  id: number;

  @Column({ name: 'insee_code', type: 'char', length: 5 })
  inseeCode: string;

  @Column({ name: 'zone_id', type: 'int', unsigned: true })
  zoneId: number;

  @Column({ name: 'zone_code', type: 'varchar', length: 32, nullable: true })
  zoneCode: string | null;

  @Column({ name: 'zone_name', type: 'varchar', length: 160, nullable: true })
  zoneName: string | null;

  @Column({ name: 'zone_type', type: 'varchar', length: 8 })
  zoneType: string;

  @Column({ type: 'varchar', length: 32 })
  severity: string;

  @Column({ name: 'decree_start', type: 'date', nullable: true })
  decreeStart: string | null;

  @Column({ name: 'decree_end', type: 'date', nullable: true })
  decreeEnd: string | null;

  @Column({ name: 'decree_url', type: 'varchar', length: 500, nullable: true })
  decreeUrl: string | null;

  @Column({ type: 'longtext', nullable: true, transformer: json })
  usages: any;
}
