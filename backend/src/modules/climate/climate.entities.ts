import { Column, Entity, PrimaryGeneratedColumn } from 'typeorm';
import { decimal, json, SourcedEntity } from '../../common/entities/sourced.entity';

@Entity('climate_projection')
export class ClimateProjectionEntity extends SourcedEntity {
  @PrimaryGeneratedColumn({ type: 'bigint', unsigned: true })
  id: number;

  @Column({ name: 'address_id', type: 'bigint', unsigned: true })
  addressId: number;

  @Column({ type: 'varchar', length: 48 })
  model: string;

  @Column({ type: 'varchar', length: 16 })
  period: string;

  @Column({ type: 'varchar', length: 48 })
  indicator: string;

  @Column({ type: 'decimal', precision: 10, scale: 2, nullable: true, transformer: decimal })
  value: number | null;

  @Column({ type: 'varchar', length: 16, nullable: true })
  unit: string | null;
}

@Entity('solar_potential')
export class SolarPotentialEntity extends SourcedEntity {
  @PrimaryGeneratedColumn({ type: 'bigint', unsigned: true })
  id: number;

  @Column({ name: 'address_id', type: 'bigint', unsigned: true })
  addressId: number;

  @Column({ name: 'tilt_deg', type: 'tinyint', unsigned: true })
  tiltDeg: number;

  @Column({ name: 'azimuth_deg', type: 'smallint' })
  azimuthDeg: number;

  @Column({ name: 'yearly_kwh_per_kwp', type: 'decimal', precision: 8, scale: 2, nullable: true, transformer: decimal })
  yearlyKwhPerKwp: number | null;

  @Column({ name: 'yearly_irradiation_kwh_m2', type: 'decimal', precision: 8, scale: 2, nullable: true, transformer: decimal })
  yearlyIrradiationKwhM2: number | null;

  @Column({ name: 'winter_kwh_per_kwp', type: 'decimal', precision: 8, scale: 2, nullable: true, transformer: decimal })
  winterKwhPerKwp: number | null;

  @Column({ type: 'longtext', nullable: true, transformer: json })
  monthly: any;
}

@Entity('air_quality_index')
export class AirQualityIndexEntity extends SourcedEntity {
  @PrimaryGeneratedColumn({ type: 'bigint', unsigned: true })
  id: number;

  @Column({ name: 'insee_code', type: 'char', length: 5 })
  inseeCode: string;

  @Column({ name: 'index_type', type: 'enum', enum: ['atmo', 'pollen'] })
  indexType: 'atmo' | 'pollen';

  @Column({ name: 'index_date', type: 'date' })
  indexDate: string;

  @Column({ name: 'level_code', type: 'tinyint', unsigned: true, nullable: true })
  levelCode: number | null;

  @Column({ name: 'level_label', type: 'varchar', length: 48, nullable: true })
  levelLabel: string | null;

  @Column({ type: 'varchar', length: 120, nullable: true })
  responsible: string | null;

  @Column({ type: 'longtext', nullable: true, transformer: json })
  details: any;
}
