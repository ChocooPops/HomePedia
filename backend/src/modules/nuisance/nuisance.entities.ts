import { Column, Entity, Index, PrimaryGeneratedColumn } from 'typeorm';
import { bool, decimal, json, SourcedEntity } from '../../common/entities/sourced.entity';

@Entity('nuisance_poi')
export class NuisancePoiEntity extends SourcedEntity {
  @PrimaryGeneratedColumn({ type: 'bigint', unsigned: true })
  id: number;

  @Column({ name: 'external_id', type: 'varchar', length: 64 })
  externalId: string;

  @Column({ type: 'varchar', length: 48 })
  category: string;

  @Column({ type: 'varchar', length: 80, nullable: true })
  subcategory: string | null;

  @Column({ type: 'varchar', length: 255, nullable: true })
  name: string | null;

  @Column({ type: 'longtext', nullable: true, transformer: json })
  tags: any;

  @Column({ type: 'decimal', precision: 9, scale: 6, transformer: decimal })
  latitude: number;

  @Column({ type: 'decimal', precision: 9, scale: 6, transformer: decimal })
  longitude: number;

  @Index({ spatial: true })
  @Column({ type: 'point', srid: 4326, select: false })
  location: string;
}

@Entity('nuisance_line')
export class NuisanceLineEntity extends SourcedEntity {
  @PrimaryGeneratedColumn({ type: 'bigint', unsigned: true })
  id: number;

  @Column({ name: 'external_id', type: 'varchar', length: 64 })
  externalId: string;

  @Column({ type: 'varchar', length: 48 })
  category: string;

  @Column({ type: 'varchar', length: 80, nullable: true })
  subcategory: string | null;

  @Column({ type: 'varchar', length: 255, nullable: true })
  name: string | null;

  @Column({ type: 'longtext', nullable: true, transformer: json })
  tags: any;

  @Index({ spatial: true })
  @Column({ type: 'geometry', srid: 4326, select: false })
  geom: string;
}

@Entity('flight_observation')
export class FlightObservationEntity extends SourcedEntity {
  @PrimaryGeneratedColumn({ type: 'bigint', unsigned: true })
  id: number;

  @Column({ name: 'address_id', type: 'bigint', unsigned: true })
  addressId: number;

  @Column({ name: 'observed_at', type: 'datetime' })
  observedAt: Date;

  @Column({ type: 'varchar', length: 8 })
  icao24: string;

  @Column({ type: 'varchar', length: 12, nullable: true })
  callsign: string | null;

  @Column({ name: 'origin_country', type: 'varchar', length: 64, nullable: true })
  originCountry: string | null;

  @Column({ name: 'altitude_m', type: 'decimal', precision: 8, scale: 1, nullable: true, transformer: decimal })
  altitudeM: number | null;

  @Column({ name: 'on_ground', type: 'tinyint', width: 1, transformer: bool })
  onGround: boolean;

  @Column({ name: 'velocity_ms', type: 'decimal', precision: 7, scale: 2, nullable: true, transformer: decimal })
  velocityMs: number | null;

  @Column({ name: 'distance_m', type: 'int', unsigned: true, nullable: true })
  distanceM: number | null;

  @Column({ type: 'decimal', precision: 9, scale: 6, transformer: decimal })
  latitude: number;

  @Column({ type: 'decimal', precision: 9, scale: 6, transformer: decimal })
  longitude: number;
}
