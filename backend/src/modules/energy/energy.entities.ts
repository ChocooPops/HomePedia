import { Column, Entity, PrimaryGeneratedColumn } from 'typeorm';
import { bool, decimal, json, SourcedEntity } from '../../common/entities/sourced.entity';

@Entity('energy_network_access')
export class EnergyNetworkAccessEntity extends SourcedEntity {
  @PrimaryGeneratedColumn({ type: 'bigint', unsigned: true })
  id: number;

  @Column({ name: 'address_id', type: 'bigint', unsigned: true })
  addressId: number;

  @Column({ name: 'network_type', type: 'enum', enum: ['heat', 'gas'] })
  networkType: 'heat' | 'gas';

  @Column({ type: 'tinyint', width: 1, transformer: bool })
  available: boolean;

  @Column({ name: 'distance_m', type: 'int', unsigned: true, nullable: true })
  distanceM: number | null;

  @Column({ name: 'operator_name', type: 'varchar', length: 160, nullable: true })
  operatorName: string | null;

  @Column({ name: 'network_name', type: 'varchar', length: 160, nullable: true })
  networkName: string | null;

  @Column({ type: 'longtext', nullable: true, transformer: json })
  details: any;
}

@Entity('electricity_consumption')
export class ElectricityConsumptionEntity extends SourcedEntity {
  @PrimaryGeneratedColumn({ type: 'bigint', unsigned: true })
  id: number;

  @Column({ name: 'insee_code', type: 'char', length: 5 })
  inseeCode: string;

  @Column({ name: 'address_key', type: 'varchar', length: 191 })
  addressKey: string;

  @Column({ type: 'smallint', unsigned: true })
  year: number;

  @Column({ name: 'iris_code', type: 'char', length: 9, nullable: true })
  irisCode: string | null;

  @Column({ type: 'int', unsigned: true, nullable: true })
  dwellings: number | null;

  @Column({ name: 'total_mwh', type: 'decimal', precision: 12, scale: 3, nullable: true, transformer: decimal })
  totalMwh: number | null;

  @Column({ name: 'avg_per_site_mwh', type: 'decimal', precision: 10, scale: 3, nullable: true, transformer: decimal })
  avgPerSiteMwh: number | null;

  @Column({ name: 'commune_avg_mwh', type: 'decimal', precision: 10, scale: 3, nullable: true, transformer: decimal })
  communeAvgMwh: number | null;
}
