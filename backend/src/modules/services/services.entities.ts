import { Column, Entity, Index, PrimaryColumn, PrimaryGeneratedColumn } from 'typeorm';
import { bool, decimal, json, SourcedEntity } from '../../common/entities/sourced.entity';

@Entity('service_place')
export class ServicePlaceEntity extends SourcedEntity {
  @PrimaryGeneratedColumn({ type: 'bigint', unsigned: true })
  id: number;

  @Column({ name: 'external_id', type: 'varchar', length: 64 })
  externalId: string;

  @Column({ type: 'varchar', length: 48 })
  category: string;

  @Column({ type: 'varchar', length: 255, nullable: true })
  name: string | null;

  @Column({ name: 'address_label', type: 'varchar', length: 255, nullable: true })
  addressLabel: string | null;

  @Column({ name: 'insee_code', type: 'char', length: 5, nullable: true })
  inseeCode: string | null;

  @Column({ name: 'opening_hours', type: 'varchar', length: 255, nullable: true })
  openingHours: string | null;

  @Column({ type: 'longtext', nullable: true, transformer: json })
  details: any;

  @Column({ type: 'decimal', precision: 9, scale: 6, transformer: decimal })
  latitude: number;

  @Column({ type: 'decimal', precision: 9, scale: 6, transformer: decimal })
  longitude: number;

  @Index({ spatial: true })
  @Column({ type: 'point', srid: 4326, select: false })
  location: string;
}

@Entity('school')
export class SchoolEntity extends SourcedEntity {
  @PrimaryColumn({ type: 'char', length: 8 })
  uai: string;

  @Column({ type: 'varchar', length: 255 })
  name: string;

  @Column({ name: 'school_type', type: 'varchar', length: 48, nullable: true })
  schoolType: string | null;

  @Column({ name: 'nature_label', type: 'varchar', length: 120, nullable: true })
  natureLabel: string | null;

  @Column({ type: 'varchar', length: 16, nullable: true })
  sector: string | null;

  @Column({ name: 'insee_code', type: 'char', length: 5, nullable: true })
  inseeCode: string | null;

  @Column({ name: 'has_preschool', type: 'tinyint', width: 1, nullable: true, transformer: bool })
  hasPreschool: boolean | null;

  @Column({ name: 'has_elementary', type: 'tinyint', width: 1, nullable: true, transformer: bool })
  hasElementary: boolean | null;

  @Column({ name: 'has_canteen', type: 'tinyint', width: 1, nullable: true, transformer: bool })
  hasCanteen: boolean | null;

  @Column({ name: 'priority_education', type: 'varchar', length: 32, nullable: true })
  priorityEducation: string | null;

  @Column({ type: 'decimal', precision: 5, scale: 1, nullable: true, transformer: decimal })
  ips: number | null;

  @Column({ name: 'ips_school_year', type: 'varchar', length: 9, nullable: true })
  ipsSchoolYear: string | null;

  @Column({ name: 'classes_count', type: 'smallint', unsigned: true, nullable: true })
  classesCount: number | null;

  @Column({ name: 'students_count', type: 'smallint', unsigned: true, nullable: true })
  studentsCount: number | null;

  @Column({ name: 'avg_class_size', type: 'decimal', precision: 4, scale: 1, nullable: true, transformer: decimal })
  avgClassSize: number | null;

  @Column({ name: 'headcount_year', type: 'varchar', length: 9, nullable: true })
  headcountYear: string | null;

  @Column({ type: 'decimal', precision: 9, scale: 6, transformer: decimal })
  latitude: number;

  @Column({ type: 'decimal', precision: 9, scale: 6, transformer: decimal })
  longitude: number;

  @Index({ spatial: true })
  @Column({ type: 'point', srid: 4326, select: false })
  location: string;
}

@Entity('travel_time')
export class TravelTimeEntity extends SourcedEntity {
  @PrimaryGeneratedColumn({ type: 'bigint', unsigned: true })
  id: number;

  @Column({ name: 'address_id', type: 'bigint', unsigned: true })
  addressId: number;

  @Column({ name: 'destination_kind', type: 'varchar', length: 48 })
  destinationKind: string;

  @Column({ type: 'enum', enum: ['car', 'pedestrian'] })
  profile: 'car' | 'pedestrian';

  @Column({ name: 'destination_label', type: 'varchar', length: 255, nullable: true })
  destinationLabel: string | null;

  @Column({ name: 'destination_lat', type: 'decimal', precision: 9, scale: 6, transformer: decimal })
  destinationLat: number;

  @Column({ name: 'destination_lon', type: 'decimal', precision: 9, scale: 6, transformer: decimal })
  destinationLon: number;

  @Column({ name: 'duration_s', type: 'int', unsigned: true, nullable: true })
  durationS: number | null;

  @Column({ name: 'distance_m', type: 'int', unsigned: true, nullable: true })
  distanceM: number | null;
}
