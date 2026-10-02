import { Column, Entity, Index, PrimaryColumn } from 'typeorm';
import { bool, decimal, json, SourcedEntity } from '../../common/entities/sourced.entity';

@Entity('charging_station')
export class ChargingStationEntity extends SourcedEntity {
  @PrimaryColumn({ name: 'pdc_id', type: 'varchar', length: 64 })
  pdcId: string;

  @Column({ name: 'station_name', type: 'varchar', length: 255, nullable: true })
  stationName: string | null;

  @Column({ name: 'operator_name', type: 'varchar', length: 160, nullable: true })
  operatorName: string | null;

  @Column({ name: 'insee_code', type: 'char', length: 5, nullable: true })
  inseeCode: string | null;

  @Column({ name: 'power_kw', type: 'decimal', precision: 7, scale: 2, nullable: true, transformer: decimal })
  powerKw: number | null;

  @Column({ type: 'longtext', nullable: true, transformer: json })
  connectors: string[] | null;

  @Column({ name: 'is_free', type: 'tinyint', width: 1, nullable: true, transformer: bool })
  isFree: boolean | null;

  @Column({ name: 'access_condition', type: 'varchar', length: 80, nullable: true })
  accessCondition: string | null;

  @Column({ name: 'opening_hours', type: 'varchar', length: 255, nullable: true })
  openingHours: string | null;

  @Column({ type: 'decimal', precision: 9, scale: 6, transformer: decimal })
  latitude: number;

  @Column({ type: 'decimal', precision: 9, scale: 6, transformer: decimal })
  longitude: number;

  @Index({ spatial: true })
  @Column({ type: 'point', srid: 4326, select: false })
  location: string;
}

@Entity('parking_facility')
export class ParkingFacilityEntity extends SourcedEntity {
  @PrimaryColumn({ name: 'external_id', type: 'varchar', length: 64 })
  externalId: string;

  @Column({ type: 'varchar', length: 255, nullable: true })
  name: string | null;

  @Column({ name: 'insee_code', type: 'char', length: 5, nullable: true })
  inseeCode: string | null;

  @Column({ type: 'int', unsigned: true, nullable: true })
  places: number | null;

  @Column({ name: 'pmr_places', type: 'int', unsigned: true, nullable: true })
  pmrPlaces: number | null;

  @Column({ name: 'ev_places', type: 'int', unsigned: true, nullable: true })
  evPlaces: number | null;

  @Column({ name: 'is_free', type: 'tinyint', width: 1, nullable: true, transformer: bool })
  isFree: boolean | null;

  @Column({ name: 'hourly_rate_eur', type: 'decimal', precision: 6, scale: 2, nullable: true, transformer: decimal })
  hourlyRateEur: number | null;

  @Column({ name: 'resident_subscription_eur', type: 'decimal', precision: 8, scale: 2, nullable: true, transformer: decimal })
  residentSubscriptionEur: number | null;

  @Column({ type: 'decimal', precision: 9, scale: 6, transformer: decimal })
  latitude: number;

  @Column({ type: 'decimal', precision: 9, scale: 6, transformer: decimal })
  longitude: number;

  @Index({ spatial: true })
  @Column({ type: 'point', srid: 4326, select: false })
  location: string;
}

@Entity('transit_stop')
export class TransitStopEntity extends SourcedEntity {
  @PrimaryColumn({ name: 'external_id', type: 'varchar', length: 64 })
  externalId: string;

  @Column({ type: 'varchar', length: 255, nullable: true })
  name: string | null;

  @Column({ type: 'varchar', length: 24 })
  mode: string;

  @Column({ type: 'varchar', length: 160, nullable: true })
  network: string | null;

  @Column({ type: 'decimal', precision: 9, scale: 6, transformer: decimal })
  latitude: number;

  @Column({ type: 'decimal', precision: 9, scale: 6, transformer: decimal })
  longitude: number;

  @Index({ spatial: true })
  @Column({ type: 'point', srid: 4326, select: false })
  location: string;
}

@Entity('transit_feed')
export class TransitFeedEntity extends SourcedEntity {
  @PrimaryColumn({ name: 'dataset_id', type: 'varchar', length: 64 })
  datasetId: string;

  @PrimaryColumn({ name: 'insee_code', type: 'char', length: 5 })
  inseeCode: string;

  @Column({ type: 'varchar', length: 255 })
  title: string;

  @Column({ type: 'varchar', length: 160, nullable: true })
  publisher: string | null;

  @Column({ name: 'gtfs_url', type: 'varchar', length: 500, nullable: true })
  gtfsUrl: string | null;

  @Column({ name: 'is_available', type: 'tinyint', width: 1, nullable: true, transformer: bool })
  isAvailable: boolean | null;

  @Column({ name: 'coverage_level', type: 'varchar', length: 16, nullable: true })
  coverageLevel: string | null;

  @Column({ name: 'updated_at', type: 'datetime', nullable: true })
  updatedAt: Date | null;
}
