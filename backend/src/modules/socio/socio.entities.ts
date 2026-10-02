import { Column, Entity, PrimaryColumn, PrimaryGeneratedColumn } from 'typeorm';
import { bool, decimal, SourcedEntity } from '../../common/entities/sourced.entity';

@Entity('socio_indicator')
export class SocioIndicatorEntity extends SourcedEntity {
  @PrimaryGeneratedColumn({ type: 'bigint', unsigned: true })
  id: number;

  @Column({ name: 'insee_code', type: 'char', length: 5 })
  inseeCode: string;

  @Column({ type: 'varchar', length: 64 })
  indicator: string;

  @Column({ type: 'smallint', unsigned: true })
  year: number;

  @Column({ type: 'decimal', precision: 18, scale: 4, nullable: true, transformer: decimal })
  value: number | null;

  @Column({ type: 'varchar', length: 24, nullable: true })
  unit: string | null;
}

@Entity('crime_stat')
export class CrimeStatEntity extends SourcedEntity {
  @PrimaryGeneratedColumn({ type: 'bigint', unsigned: true })
  id: number;

  @Column({ name: 'insee_code', type: 'char', length: 5 })
  inseeCode: string;

  @Column({ type: 'smallint', unsigned: true })
  year: number;

  @Column({ type: 'varchar', length: 128 })
  indicator: string;

  @Column({ name: 'count_unit', type: 'varchar', length: 32, nullable: true })
  countUnit: string | null;

  @Column({ type: 'int', unsigned: true, nullable: true })
  count: number | null;

  @Column({ name: 'rate_per_thousand', type: 'decimal', precision: 10, scale: 4, nullable: true, transformer: decimal })
  ratePerThousand: number | null;

  @Column({ name: 'is_published', type: 'tinyint', width: 1, transformer: bool })
  isPublished: boolean;
}

@Entity('local_tax_rate')
export class LocalTaxRateEntity extends SourcedEntity {
  @PrimaryColumn({ name: 'insee_code', type: 'char', length: 5 })
  inseeCode: string;

  @PrimaryColumn({ type: 'smallint', unsigned: true })
  year: number;

  @Column({ name: 'epci_code', type: 'varchar', length: 9, nullable: true })
  epciCode: string | null;

  @Column({ name: 'property_tax_rate', type: 'decimal', precision: 6, scale: 3, nullable: true, transformer: decimal })
  propertyTaxRate: number | null;

  @Column({ name: 'land_tax_rate', type: 'decimal', precision: 6, scale: 3, nullable: true, transformer: decimal })
  landTaxRate: number | null;

  @Column({ name: 'waste_tax_rate', type: 'decimal', precision: 6, scale: 3, nullable: true, transformer: decimal })
  wasteTaxRate: number | null;

  @Column({ name: 'housing_tax_rate', type: 'decimal', precision: 6, scale: 3, nullable: true, transformer: decimal })
  housingTaxRate: number | null;

  @Column({ name: 'secondary_home_surcharge', type: 'tinyint', width: 1, nullable: true, transformer: bool })
  secondaryHomeSurcharge: boolean | null;

  @Column({ name: 'secondary_home_surcharge_rate', type: 'decimal', precision: 6, scale: 3, nullable: true, transformer: decimal })
  secondaryHomeSurchargeRate: number | null;
}
