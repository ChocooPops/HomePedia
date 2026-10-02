import { Column, CreateDateColumn, Entity, Index, PrimaryColumn, PrimaryGeneratedColumn, UpdateDateColumn } from 'typeorm';
import { decimal, json, SourcedEntity } from '../../common/entities/sourced.entity';

@Entity('commune')
export class CommuneEntity extends SourcedEntity {
  @PrimaryColumn({ name: 'insee_code', type: 'char', length: 5 })
  inseeCode: string;

  @Column({ type: 'varchar', length: 120 })
  name: string;

  @Column({ name: 'department_code', type: 'varchar', length: 3 })
  departmentCode: string;

  @Column({ name: 'department_name', type: 'varchar', length: 80, nullable: true })
  departmentName: string | null;

  @Column({ name: 'region_code', type: 'varchar', length: 3, nullable: true })
  regionCode: string | null;

  @Column({ name: 'region_name', type: 'varchar', length: 80, nullable: true })
  regionName: string | null;

  @Column({ name: 'epci_code', type: 'varchar', length: 9, nullable: true })
  epciCode: string | null;

  @Column({ name: 'postal_codes', type: 'longtext', nullable: true, transformer: json })
  postalCodes: string[] | null;

  @Column({ type: 'int', unsigned: true, nullable: true })
  population: number | null;

  @Column({ name: 'surface_ha', type: 'decimal', precision: 12, scale: 2, nullable: true, transformer: decimal })
  surfaceHa: number | null;

  @Column({ type: 'decimal', precision: 9, scale: 6, transformer: decimal })
  latitude: number;

  @Column({ type: 'decimal', precision: 9, scale: 6, transformer: decimal })
  longitude: number;

  @Index({ spatial: true })
  @Column({ type: 'point', srid: 4326, select: false })
  center: string;
}

@Entity('parcel')
export class ParcelEntity extends SourcedEntity {
  @PrimaryColumn({ type: 'char', length: 14 })
  idu: string;

  @Column({ name: 'insee_code', type: 'char', length: 5 })
  inseeCode: string;

  @Column({ type: 'char', length: 3, default: '000' })
  prefix: string;

  @Column({ type: 'varchar', length: 2 })
  section: string;

  @Column({ type: 'char', length: 4 })
  numero: string;

  @Column({ type: 'smallint', unsigned: true, nullable: true })
  sheet: number | null;

  @Column({ name: 'area_m2', type: 'int', unsigned: true, nullable: true })
  areaM2: number | null;

  @Index({ spatial: true })
  @Column({ type: 'geometry', srid: 4326, select: false })
  geom: string;
}

/** Entité pivot : une adresse géolocalisée à laquelle se rattachent toutes les autres données. */
@Entity('address')
export class AddressEntity extends SourcedEntity {
  @PrimaryGeneratedColumn({ type: 'bigint', unsigned: true })
  id: number;

  @Column({ name: 'ban_id', type: 'varchar', length: 64, nullable: true, unique: true })
  banId: string | null;

  @Column({ type: 'varchar', length: 255 })
  label: string;

  @Column({ type: 'varchar', length: 16, nullable: true })
  housenumber: string | null;

  @Column({ type: 'varchar', length: 160, nullable: true })
  street: string | null;

  @Column({ type: 'char', length: 5, nullable: true })
  postcode: string | null;

  @Column({ type: 'varchar', length: 120, nullable: true })
  city: string | null;

  @Column({ name: 'insee_code', type: 'char', length: 5 })
  inseeCode: string;

  @Column({ type: 'decimal', precision: 9, scale: 6, transformer: decimal })
  latitude: number;

  @Column({ type: 'decimal', precision: 9, scale: 6, transformer: decimal })
  longitude: number;

  @Index({ spatial: true })
  @Column({ type: 'point', srid: 4326, select: false })
  location: string;

  @Column({ name: 'geocode_score', type: 'decimal', precision: 5, scale: 4, nullable: true, transformer: decimal })
  geocodeScore: number | null;

  @Column({ name: 'geocode_type', type: 'varchar', length: 16, nullable: true })
  geocodeType: string | null;

  @Column({ name: 'parcel_idu', type: 'char', length: 14, nullable: true })
  parcelIdu: string | null;

  @Column({ name: 'rnb_id', type: 'varchar', length: 12, nullable: true })
  rnbId: string | null;

  @CreateDateColumn({ name: 'created_at', type: 'datetime', precision: 3 })
  createdAt: Date;

  @UpdateDateColumn({ name: 'updated_at', type: 'datetime', precision: 3 })
  updatedAt: Date;
}

/** Indicateur calculé à l'adresse (table longue, une ligne par indicateur). */
@Entity('address_indicator')
export class AddressIndicatorEntity extends SourcedEntity {
  @PrimaryGeneratedColumn({ type: 'bigint', unsigned: true })
  id: number;

  @Column({ name: 'address_id', type: 'bigint', unsigned: true })
  addressId: number;

  @Column({ type: 'varchar', length: 32 })
  domain: string;

  @Column({ type: 'varchar', length: 64 })
  indicator: string;

  @Column({ name: 'value_num', type: 'decimal', precision: 18, scale: 4, nullable: true, transformer: decimal })
  valueNum: number | null;

  @Column({ name: 'value_text', type: 'varchar', length: 255, nullable: true })
  valueText: string | null;

  @Column({ type: 'varchar', length: 24, nullable: true })
  unit: string | null;

  @Column({ type: 'longtext', nullable: true, transformer: json })
  details: any;
}

@Entity('plu_zone')
export class PluZoneEntity extends SourcedEntity {
  @PrimaryGeneratedColumn({ type: 'bigint', unsigned: true })
  id: number;

  @Column({ name: 'gpu_id', type: 'varchar', length: 64, unique: true })
  gpuId: string;

  @Column({ name: 'insee_code', type: 'char', length: 5, nullable: true })
  inseeCode: string | null;

  @Column({ name: 'document_id', type: 'varchar', length: 64, nullable: true })
  documentId: string | null;

  @Column({ type: 'varchar', length: 64, nullable: true })
  label: string | null;

  @Column({ name: 'label_long', type: 'varchar', length: 255, nullable: true })
  labelLong: string | null;

  @Column({ name: 'zone_type', type: 'varchar', length: 8, nullable: true })
  zoneType: string | null;

  @Column({ name: 'approved_at', type: 'date', nullable: true })
  approvedAt: string | null;

  @Column({ name: 'regulation_file', type: 'varchar', length: 255, nullable: true })
  regulationFile: string | null;

  @Index({ spatial: true })
  @Column({ type: 'geometry', srid: 4326, select: false })
  geom: string;
}

@Entity('plu_prescription')
export class PluPrescriptionEntity extends SourcedEntity {
  @PrimaryGeneratedColumn({ type: 'bigint', unsigned: true })
  id: number;

  @Column({ name: 'gpu_id', type: 'varchar', length: 64, unique: true })
  gpuId: string;

  @Column({ name: 'insee_code', type: 'char', length: 5, nullable: true })
  inseeCode: string | null;

  @Column({ name: 'document_id', type: 'varchar', length: 64, nullable: true })
  documentId: string | null;

  @Column({ name: 'geometry_kind', type: 'enum', enum: ['surface', 'line', 'point'] })
  geometryKind: 'surface' | 'line' | 'point';

  @Column({ name: 'type_code', type: 'varchar', length: 4, nullable: true })
  typeCode: string | null;

  @Column({ name: 'subtype_code', type: 'varchar', length: 4, nullable: true })
  subtypeCode: string | null;

  @Column({ type: 'varchar', length: 255, nullable: true })
  label: string | null;

  @Column({ type: 'varchar', length: 255, nullable: true })
  nature: string | null;

  @Index({ spatial: true })
  @Column({ type: 'geometry', srid: 4326, select: false })
  geom: string;
}

@Entity('public_easement')
export class PublicEasementEntity extends SourcedEntity {
  @PrimaryGeneratedColumn({ type: 'bigint', unsigned: true })
  id: number;

  @Column({ name: 'gpu_id', type: 'varchar', length: 64, unique: true })
  gpuId: string;

  @Column({ name: 'sup_type', type: 'varchar', length: 8 })
  supType: string;

  @Column({ type: 'varchar', length: 255, nullable: true })
  name: string | null;

  @Column({ name: 'assiette_type', type: 'varchar', length: 120, nullable: true })
  assietteType: string | null;

  @Column({ name: 'generator_id', type: 'varchar', length: 120, nullable: true })
  generatorId: string | null;

  @Index({ spatial: true })
  @Column({ type: 'geometry', srid: 4326, select: false })
  geom: string;
}

@Entity('monument')
export class MonumentEntity extends SourcedEntity {
  @PrimaryColumn({ type: 'varchar', length: 16 })
  reference: string;

  @Column({ type: 'varchar', length: 255, nullable: true })
  name: string | null;

  @Column({ name: 'insee_code', type: 'char', length: 5 })
  inseeCode: string;

  @Column({ type: 'varchar', length: 255, nullable: true })
  denomination: string | null;

  @Column({ name: 'protection_type', type: 'varchar', length: 120, nullable: true })
  protectionType: string | null;

  @Column({ name: 'protection_text', type: 'varchar', length: 1000, nullable: true })
  protectionText: string | null;

  @Column({ type: 'decimal', precision: 9, scale: 6, nullable: true, transformer: decimal })
  latitude: number | null;

  @Column({ type: 'decimal', precision: 9, scale: 6, nullable: true, transformer: decimal })
  longitude: number | null;
}
