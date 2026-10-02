import { Column, Entity, Index, PrimaryColumn, PrimaryGeneratedColumn } from 'typeorm';
import { bool, decimal, json, SourcedEntity } from '../../common/entities/sourced.entity';

export type RiskCategory = 'natural' | 'technological' | 'regulatory';

@Entity('risk_assessment')
export class RiskAssessmentEntity extends SourcedEntity {
  @PrimaryGeneratedColumn({ type: 'bigint', unsigned: true })
  id: number;

  @Column({ name: 'address_id', type: 'bigint', unsigned: true })
  addressId: number;

  @Column({ name: 'hazard_code', type: 'varchar', length: 48 })
  hazardCode: string;

  @Column({ type: 'enum', enum: ['natural', 'technological', 'regulatory'] })
  category: RiskCategory;

  @Column({ type: 'varchar', length: 160 })
  label: string;

  @Column({ type: 'tinyint', width: 1, transformer: bool })
  present: boolean;

  @Column({ name: 'commune_status', type: 'varchar', length: 80, nullable: true })
  communeStatus: string | null;

  @Column({ name: 'address_status', type: 'varchar', length: 80, nullable: true })
  addressStatus: string | null;

  @Column({ type: 'longtext', nullable: true, transformer: json })
  details: any;
}

@Entity('commune_risk_profile')
export class CommuneRiskProfileEntity extends SourcedEntity {
  @PrimaryColumn({ name: 'insee_code', type: 'char', length: 5 })
  inseeCode: string;

  @Column({ name: 'radon_class', type: 'tinyint', unsigned: true, nullable: true })
  radonClass: number | null;

  @Column({ name: 'seismic_zone', type: 'varchar', length: 32, nullable: true })
  seismicZone: string | null;

  @Column({ name: 'known_risks', type: 'longtext', nullable: true, transformer: json })
  knownRisks: string[] | null;

  @Column({ name: 'flood_atlases', type: 'longtext', nullable: true, transformer: json })
  floodAtlases: any;
}

@Entity('catnat_decree')
export class CatnatDecreeEntity extends SourcedEntity {
  @PrimaryColumn({ name: 'code_national', type: 'varchar', length: 24 })
  codeNational: string;

  @PrimaryColumn({ name: 'insee_code', type: 'char', length: 5 })
  inseeCode: string;

  @Column({ name: 'hazard_label', type: 'varchar', length: 160 })
  hazardLabel: string;

  @Column({ name: 'event_start', type: 'date', nullable: true })
  eventStart: string | null;

  @Column({ name: 'event_end', type: 'date', nullable: true })
  eventEnd: string | null;

  @Column({ name: 'decree_date', type: 'date', nullable: true })
  decreeDate: string | null;

  @Column({ name: 'journal_date', type: 'date', nullable: true })
  journalDate: string | null;
}

export type RiskSiteType = 'icpe' | 'casias' | 'ssp' | 'cavity' | 'ground_movement';

@Entity('risk_site')
export class RiskSiteEntity extends SourcedEntity {
  @PrimaryGeneratedColumn({ type: 'bigint', unsigned: true })
  id: number;

  @Column({ name: 'site_type', type: 'enum', enum: ['icpe', 'casias', 'ssp', 'cavity', 'ground_movement'] })
  siteType: RiskSiteType;

  @Column({ name: 'external_id', type: 'varchar', length: 64 })
  externalId: string;

  @Column({ type: 'varchar', length: 255, nullable: true })
  name: string | null;

  @Column({ name: 'insee_code', type: 'char', length: 5, nullable: true })
  inseeCode: string | null;

  @Column({ type: 'varchar', length: 80, nullable: true })
  status: string | null;

  @Column({ name: 'seveso_status', type: 'varchar', length: 48, nullable: true })
  sevesoStatus: string | null;

  @Column({ type: 'varchar', length: 120, nullable: true })
  subtype: string | null;

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

@Entity('bio_risk')
export class BioRiskEntity extends SourcedEntity {
  @PrimaryGeneratedColumn({ type: 'bigint', unsigned: true })
  id: number;

  @Column({ type: 'enum', enum: ['commune', 'department'] })
  scope: 'commune' | 'department';

  @Column({ name: 'area_code', type: 'varchar', length: 5 })
  areaCode: string;

  @Column({ type: 'varchar', length: 48 })
  species: string;

  @Column({ type: 'varchar', length: 80 })
  status: string;

  @Column({ type: 'smallint', unsigned: true })
  year: number;

  @Column({ name: 'reference_url', type: 'varchar', length: 500, nullable: true })
  referenceUrl: string | null;

  @Column({ type: 'varchar', length: 500, nullable: true })
  notes: string | null;
}
