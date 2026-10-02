import { Column, Entity, PrimaryColumn, PrimaryGeneratedColumn } from 'typeorm';
import { bool } from '../../common/entities/sourced.entity';

@Entity('data_source')
export class DataSourceEntity {
  @PrimaryColumn({ type: 'varchar', length: 48 })
  code: string;

  @Column({ type: 'varchar', length: 160 })
  name: string;

  @Column({ type: 'varchar', length: 32 })
  domain: string;

  @Column({ name: 'base_url', type: 'varchar', length: 255 })
  baseUrl: string;

  @Column({ name: 'ttl_seconds', type: 'int', unsigned: true })
  ttlSeconds: number;

  @Column({ name: 'requires_key', type: 'tinyint', width: 1, transformer: bool })
  requiresKey: boolean;

  @Column({ type: 'enum', enum: ['verified', 'degraded', 'obsolete', 'untested'] })
  status: 'verified' | 'degraded' | 'obsolete' | 'untested';

  @Column({ type: 'varchar', length: 500, nullable: true })
  notes: string | null;
}

export type FetchStatus = 'success' | 'error' | 'skipped';

@Entity('fetch_log')
export class FetchLogEntity {
  @PrimaryGeneratedColumn({ type: 'bigint', unsigned: true })
  id: number;

  @Column({ name: 'source_code', type: 'varchar', length: 48 })
  sourceCode: string;

  @Column({ name: 'target_key', type: 'varchar', length: 191 })
  targetKey: string;

  @Column({ type: 'enum', enum: ['success', 'error', 'skipped'] })
  status: FetchStatus;

  @Column({ name: 'items_count', type: 'int', unsigned: true, default: 0 })
  itemsCount: number;

  @Column({ name: 'http_status', type: 'smallint', unsigned: true, nullable: true })
  httpStatus: number | null;

  @Column({ name: 'duration_ms', type: 'int', unsigned: true, default: 0 })
  durationMs: number;

  @Column({ name: 'error_message', type: 'varchar', length: 1000, nullable: true })
  errorMessage: string | null;

  @Column({ name: 'fetched_at', type: 'datetime', precision: 3 })
  fetchedAt: Date;

  @Column({ name: 'expires_at', type: 'datetime', precision: 3, nullable: true })
  expiresAt: Date | null;
}

@Entity('raw_payload')
export class RawPayloadEntity {
  @PrimaryGeneratedColumn({ type: 'bigint', unsigned: true })
  id: number;

  @Column({ name: 'fetch_log_id', type: 'bigint', unsigned: true })
  fetchLogId: number;

  @Column({ name: 'source_code', type: 'varchar', length: 48 })
  sourceCode: string;

  @Column({ name: 'target_key', type: 'varchar', length: 191 })
  targetKey: string;

  @Column({ type: 'longtext' })
  payload: string;

  @Column({ name: 'created_at', type: 'datetime', precision: 3, default: () => 'CURRENT_TIMESTAMP(3)' })
  createdAt: Date;
}
