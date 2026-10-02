import { Column, Entity, Index, PrimaryColumn, PrimaryGeneratedColumn } from 'typeorm';
import { bool, decimal, json, SourcedEntity } from '../../common/entities/sourced.entity';

@Entity('building')
export class BuildingEntity extends SourcedEntity {
  @PrimaryColumn({ name: 'rnb_id', type: 'varchar', length: 12 })
  rnbId: string;

  @Column({ name: 'bdnb_group_id', type: 'varchar', length: 32, nullable: true })
  bdnbGroupId: string | null;

  @Column({ type: 'varchar', length: 24, nullable: true })
  status: string | null;

  @Column({ name: 'insee_code', type: 'char', length: 5, nullable: true })
  inseeCode: string | null;

  @Column({ name: 'construction_year', type: 'smallint', unsigned: true, nullable: true })
  constructionYear: number | null;

  @Column({ name: 'height_m', type: 'decimal', precision: 6, scale: 2, nullable: true, transformer: decimal })
  heightM: number | null;

  @Column({ type: 'smallint', unsigned: true, nullable: true })
  levels: number | null;

  @Column({ type: 'smallint', unsigned: true, nullable: true })
  dwellings: number | null;

  @Column({ name: 'wall_material', type: 'varchar', length: 80, nullable: true })
  wallMaterial: string | null;

  @Column({ name: 'roof_material', type: 'varchar', length: 80, nullable: true })
  roofMaterial: string | null;

  @Column({ name: 'main_usage', type: 'varchar', length: 80, nullable: true })
  mainUsage: string | null;

  @Column({ name: 'dpe_class_bdnb', type: 'char', length: 1, nullable: true })
  dpeClassBdnb: string | null;

  @Column({ name: 'condo_registration', type: 'varchar', length: 16, nullable: true })
  condoRegistration: string | null;

  @Column({ name: 'iris_code', type: 'char', length: 9, nullable: true })
  irisCode: string | null;

  @Column({ name: 'footprint_m2', type: 'int', unsigned: true, nullable: true })
  footprintM2: number | null;

  @Column({ name: 'ground_altitude_m', type: 'decimal', precision: 7, scale: 2, nullable: true, transformer: decimal })
  groundAltitudeM: number | null;

  @Column({ type: 'decimal', precision: 9, scale: 6, transformer: decimal })
  latitude: number;

  @Column({ type: 'decimal', precision: 9, scale: 6, transformer: decimal })
  longitude: number;

  @Index({ spatial: true })
  @Column({ type: 'point', srid: 4326, select: false })
  location: string;

  @Column({ type: 'geometry', srid: 4326, nullable: true, select: false })
  shape: string | null;
}

@Entity('dpe_certificate')
export class DpeCertificateEntity extends SourcedEntity {
  @PrimaryColumn({ name: 'numero_dpe', type: 'varchar', length: 16 })
  numeroDpe: string;

  @Column({ name: 'rnb_id', type: 'varchar', length: 12, nullable: true })
  rnbId: string | null;

  @Column({ name: 'ban_id', type: 'varchar', length: 64, nullable: true })
  banId: string | null;

  @Column({ name: 'address_label', type: 'varchar', length: 255, nullable: true })
  addressLabel: string | null;

  @Column({ name: 'insee_code', type: 'char', length: 5, nullable: true })
  inseeCode: string | null;

  @Column({ name: 'issued_at', type: 'date', nullable: true })
  issuedAt: string | null;

  @Column({ name: 'energy_class', type: 'char', length: 1, nullable: true })
  energyClass: string | null;

  @Column({ name: 'ghg_class', type: 'char', length: 1, nullable: true })
  ghgClass: string | null;

  @Column({ name: 'energy_kwh_m2', type: 'decimal', precision: 8, scale: 1, nullable: true, transformer: decimal })
  energyKwhM2: number | null;

  @Column({ name: 'ghg_kg_m2', type: 'decimal', precision: 8, scale: 1, nullable: true, transformer: decimal })
  ghgKgM2: number | null;

  @Column({ name: 'construction_year', type: 'smallint', unsigned: true, nullable: true })
  constructionYear: number | null;

  @Column({ name: 'construction_period', type: 'varchar', length: 24, nullable: true })
  constructionPeriod: string | null;

  @Column({ name: 'building_type', type: 'varchar', length: 24, nullable: true })
  buildingType: string | null;

  @Column({ name: 'living_area_m2', type: 'decimal', precision: 8, scale: 1, nullable: true, transformer: decimal })
  livingAreaM2: number | null;

  @Column({ name: 'ceiling_height_m', type: 'decimal', precision: 4, scale: 2, nullable: true, transformer: decimal })
  ceilingHeightM: number | null;

  @Column({ name: 'heating_energy', type: 'varchar', length: 80, nullable: true })
  heatingEnergy: string | null;

  @Column({ name: 'annual_cost_eur', type: 'decimal', precision: 10, scale: 2, nullable: true, transformer: decimal })
  annualCostEur: number | null;

  @Column({ type: 'decimal', precision: 9, scale: 6, nullable: true, transformer: decimal })
  latitude: number | null;

  @Column({ type: 'decimal', precision: 9, scale: 6, nullable: true, transformer: decimal })
  longitude: number | null;
}

@Entity('dvf_mutation')
export class DvfMutationEntity extends SourcedEntity {
  @PrimaryGeneratedColumn({ type: 'bigint', unsigned: true })
  id: number;

  @Column({ name: 'row_hash', type: 'char', length: 40, unique: true })
  rowHash: string;

  @Column({ name: 'mutation_id', type: 'varchar', length: 24 })
  mutationId: string;

  @Column({ name: 'mutation_date', type: 'date' })
  mutationDate: string;

  @Column({ type: 'varchar', length: 48 })
  nature: string;

  @Column({ name: 'price_eur', type: 'decimal', precision: 15, scale: 2, nullable: true, transformer: decimal })
  priceEur: number | null;

  @Column({ name: 'insee_code', type: 'char', length: 5 })
  inseeCode: string;

  @Column({ name: 'parcel_idu', type: 'char', length: 14, nullable: true })
  parcelIdu: string | null;

  @Column({ name: 'address_label', type: 'varchar', length: 255, nullable: true })
  addressLabel: string | null;

  @Column({ name: 'property_type', type: 'varchar', length: 48, nullable: true })
  propertyType: string | null;

  @Column({ name: 'built_area_m2', type: 'int', unsigned: true, nullable: true })
  builtAreaM2: number | null;

  @Column({ type: 'smallint', unsigned: true, nullable: true })
  rooms: number | null;

  @Column({ name: 'land_area_m2', type: 'int', unsigned: true, nullable: true })
  landAreaM2: number | null;

  @Column({ name: 'lots_count', type: 'smallint', unsigned: true, nullable: true })
  lotsCount: number | null;

  @Column({ type: 'decimal', precision: 9, scale: 6, nullable: true, transformer: decimal })
  latitude: number | null;

  @Column({ type: 'decimal', precision: 9, scale: 6, nullable: true, transformer: decimal })
  longitude: number | null;
}

@Entity('price_index')
export class PriceIndexEntity {
  @PrimaryColumn({ name: 'insee_code', type: 'char', length: 5 })
  inseeCode: string;

  @PrimaryColumn({ type: 'smallint', unsigned: true })
  year: number;

  @PrimaryColumn({ name: 'property_type', type: 'varchar', length: 48 })
  propertyType: string;

  @Column({ name: 'sales_count', type: 'int', unsigned: true })
  salesCount: number;

  @Column({ name: 'median_price_m2', type: 'decimal', precision: 10, scale: 2, nullable: true, transformer: decimal })
  medianPriceM2: number | null;

  @Column({ name: 'mean_price_m2', type: 'decimal', precision: 10, scale: 2, nullable: true, transformer: decimal })
  meanPriceM2: number | null;

  @Column({ name: 'q1_price_m2', type: 'decimal', precision: 10, scale: 2, nullable: true, transformer: decimal })
  q1PriceM2: number | null;

  @Column({ name: 'q3_price_m2', type: 'decimal', precision: 10, scale: 2, nullable: true, transformer: decimal })
  q3PriceM2: number | null;

  @Column({ name: 'computed_at', type: 'datetime', precision: 3 })
  computedAt: Date;
}

@Entity('condominium')
export class CondominiumEntity extends SourcedEntity {
  @PrimaryColumn({ name: 'registration_number', type: 'varchar', length: 16 })
  registrationNumber: string;

  @Column({ type: 'varchar', length: 255, nullable: true })
  name: string | null;

  @Column({ name: 'address_label', type: 'varchar', length: 255, nullable: true })
  addressLabel: string | null;

  @Column({ name: 'insee_code', type: 'char', length: 5, nullable: true })
  inseeCode: string | null;

  @Column({ name: 'total_lots', type: 'int', unsigned: true, nullable: true })
  totalLots: number | null;

  @Column({ name: 'housing_lots', type: 'int', unsigned: true, nullable: true })
  housingLots: number | null;

  @Column({ name: 'parking_lots', type: 'int', unsigned: true, nullable: true })
  parkingLots: number | null;

  @Column({ name: 'syndic_type', type: 'varchar', length: 32, nullable: true })
  syndicType: string | null;

  @Column({ name: 'syndic_name', type: 'varchar', length: 255, nullable: true })
  syndicName: string | null;

  @Column({ name: 'mandate_status', type: 'varchar', length: 64, nullable: true })
  mandateStatus: string | null;

  @Column({ name: 'mandate_end_date', type: 'date', nullable: true })
  mandateEndDate: string | null;

  @Column({ name: 'construction_period', type: 'varchar', length: 32, nullable: true })
  constructionPeriod: string | null;

  @Column({ name: 'regulation_date', type: 'date', nullable: true })
  regulationDate: string | null;

  @Column({ name: 'is_aided', type: 'tinyint', width: 1, nullable: true, transformer: bool })
  isAided: boolean | null;

  @Column({ name: 'priority_district', type: 'varchar', length: 120, nullable: true })
  priorityDistrict: string | null;

  @Column({ name: 'cadastral_refs', type: 'longtext', nullable: true, transformer: json })
  cadastralRefs: string[] | null;

  @Column({ type: 'decimal', precision: 9, scale: 6, nullable: true, transformer: decimal })
  latitude: number | null;

  @Column({ type: 'decimal', precision: 9, scale: 6, nullable: true, transformer: decimal })
  longitude: number | null;
}
