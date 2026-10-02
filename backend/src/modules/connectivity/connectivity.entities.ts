import { Column, Entity, Index, PrimaryColumn } from 'typeorm';
import { bool, decimal, SourcedEntity } from '../../common/entities/sourced.entity';

@Entity('fixed_coverage')
export class FixedCoverageEntity extends SourcedEntity {
  @PrimaryColumn({ name: 'insee_code', type: 'char', length: 5 })
  inseeCode: string;

  @Column({ name: 'period_date', type: 'date' })
  periodDate: string;

  @Column({ type: 'int', unsigned: true })
  premises: number;

  @Column({ name: 'ftth_eligible', type: 'int', unsigned: true })
  ftthEligible: number;

  @Column({ name: 'cable_eligible', type: 'int', unsigned: true })
  cableEligible: number;

  @Column({ name: 'copper_eligible', type: 'int', unsigned: true })
  copperEligible: number;

  @Column({ name: 'thd_radio_eligible', type: 'int', unsigned: true })
  thdRadioEligible: number;

  @Column({ name: 'fixed_4g_eligible', type: 'int', unsigned: true })
  fixed4gEligible: number;

  @Column({ name: 'satellite_eligible', type: 'int', unsigned: true })
  satelliteEligible: number;

  @Column({ name: 'ftth_rate', type: 'decimal', precision: 5, scale: 2, nullable: true, transformer: decimal })
  ftthRate: number | null;
}

@Entity('mobile_site')
export class MobileSiteEntity extends SourcedEntity {
  @PrimaryColumn({ name: 'operator_code', type: 'varchar', length: 8 })
  operatorCode: string;

  @PrimaryColumn({ name: 'site_number', type: 'varchar', length: 64 })
  siteNumber: string;

  @Column({ name: 'operator_name', type: 'varchar', length: 48 })
  operatorName: string;

  @Column({ name: 'anfr_station_id', type: 'varchar', length: 24, nullable: true })
  anfrStationId: string | null;

  @Column({ name: 'insee_code', type: 'char', length: 5, nullable: true })
  inseeCode: string | null;

  @Column({ name: 'has_2g', type: 'tinyint', width: 1, transformer: bool })
  has2g: boolean;

  @Column({ name: 'has_3g', type: 'tinyint', width: 1, transformer: bool })
  has3g: boolean;

  @Column({ name: 'has_4g', type: 'tinyint', width: 1, transformer: bool })
  has4g: boolean;

  @Column({ name: 'has_5g', type: 'tinyint', width: 1, transformer: bool })
  has5g: boolean;

  @Column({ name: 'has_5g_3500', type: 'tinyint', width: 1, transformer: bool })
  has5g3500: boolean;

  @Column({ type: 'decimal', precision: 9, scale: 6, transformer: decimal })
  latitude: number;

  @Column({ type: 'decimal', precision: 9, scale: 6, transformer: decimal })
  longitude: number;

  @Index({ spatial: true })
  @Column({ type: 'point', srid: 4326, select: false })
  location: string;
}
