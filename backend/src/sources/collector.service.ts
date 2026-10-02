import { Injectable, Logger, NotFoundException, OnModuleInit } from '@nestjs/common';
import { ConfigService } from '@nestjs/config';
import { InjectRepository } from '@nestjs/typeorm';
import { MoreThan, Repository } from 'typeorm';
import { ExternalApiError, MissingApiKeyError } from '../common/http/external-api.error';
import { DataSourceEntity, FetchLogEntity, RawPayloadEntity } from './entities/sources.entities';

/** Horodatage de fraîcheur à recopier dans chaque ligne persistée. */
export interface Stamp {
  sourceCode: string;
  fetchedAt: Date;
  expiresAt: Date;
}

export interface CollectOutcome {
  source: string;
  target: string;
  status: 'success' | 'cached' | 'error' | 'skipped';
  items: number;
  fetchedAt?: Date;
  expiresAt?: Date | null;
  error?: string;
}

export interface CollectResult {
  items: number;
  /** Réponse brute à archiver (optionnel). */
  raw?: unknown;
}

const MAX_RAW_PAYLOAD_CHARS = 4 * 1024 * 1024;

/**
 * Exécute une collecte « source × cible » en gérant :
 *  - le cache : si une collecte réussie non expirée existe, on ne rappelle pas l'API ;
 *  - la journalisation (fetch_log) : statut, durée, nombre d'éléments, erreur ;
 *  - l'archivage optionnel de la réponse brute (raw_payload).
 * Les erreurs sont capturées et renvoyées dans le résultat : une source en panne
 * n'interrompt pas la collecte des autres.
 */
@Injectable()
export class CollectorService implements OnModuleInit {
  private readonly logger = new Logger(CollectorService.name);
  private sources = new Map<string, DataSourceEntity>();
  private readonly storeRaw: boolean;

  constructor(
    @InjectRepository(DataSourceEntity) private readonly sourceRepo: Repository<DataSourceEntity>,
    @InjectRepository(FetchLogEntity) private readonly logRepo: Repository<FetchLogEntity>,
    @InjectRepository(RawPayloadEntity) private readonly rawRepo: Repository<RawPayloadEntity>,
    config: ConfigService,
  ) {
    this.storeRaw = config.get<boolean>('storeRawPayloads', true);
  }

  async onModuleInit() {
    await this.reloadSources();
  }

  async reloadSources() {
    const all = await this.sourceRepo.find();
    this.sources = new Map(all.map((s) => [s.code, s]));
  }

  source(code: string): DataSourceEntity {
    const s = this.sources.get(code);
    if (!s) throw new NotFoundException(`Source inconnue : ${code}`);
    return s;
  }

  stamp(code: string, at = new Date()): Stamp {
    const s = this.source(code);
    return { sourceCode: code, fetchedAt: at, expiresAt: new Date(at.getTime() + s.ttlSeconds * 1000) };
  }

  /** Dernière collecte réussie et encore valide pour cette cible. */
  async freshLog(sourceCode: string, targetKey: string): Promise<FetchLogEntity | null> {
    return this.logRepo.findOne({
      where: { sourceCode, targetKey, status: 'success', expiresAt: MoreThan(new Date()) },
      order: { fetchedAt: 'DESC' },
    });
  }

  async run(
    sourceCode: string,
    targetKey: string,
    opts: { force?: boolean },
    task: (stamp: Stamp) => Promise<CollectResult>,
  ): Promise<CollectOutcome> {
    if (!opts.force) {
      const fresh = await this.freshLog(sourceCode, targetKey);
      if (fresh) {
        return {
          source: sourceCode,
          target: targetKey,
          status: 'cached',
          items: fresh.itemsCount,
          fetchedAt: fresh.fetchedAt,
          expiresAt: fresh.expiresAt,
        };
      }
    }

    const stamp = this.stamp(sourceCode);
    const started = Date.now();
    try {
      const result = await task(stamp);
      const log = await this.logRepo.save(
        this.logRepo.create({
          sourceCode,
          targetKey,
          status: 'success',
          itemsCount: result.items,
          durationMs: Date.now() - started,
          fetchedAt: stamp.fetchedAt,
          expiresAt: stamp.expiresAt,
        }),
      );
      await this.archive(log, result.raw);
      return { source: sourceCode, target: targetKey, status: 'success', items: result.items, fetchedAt: stamp.fetchedAt, expiresAt: stamp.expiresAt };
    } catch (err) {
      const skipped = err instanceof MissingApiKeyError;
      const message = this.errorMessage(err);
      if (!skipped) this.logger.warn(`[${sourceCode}] ${targetKey} : ${message}`);
      await this.logRepo.save(
        this.logRepo.create({
          sourceCode,
          targetKey,
          status: skipped ? 'skipped' : 'error',
          httpStatus: err instanceof ExternalApiError ? (err.upstreamStatus ?? null) : null,
          durationMs: Date.now() - started,
          errorMessage: message.slice(0, 1000),
          fetchedAt: stamp.fetchedAt,
          expiresAt: null,
        }),
      );
      return { source: sourceCode, target: targetKey, status: skipped ? 'skipped' : 'error', items: 0, error: message };
    }
  }

  private async archive(log: FetchLogEntity, raw: unknown) {
    if (!this.storeRaw || raw === undefined) return;
    const payload = JSON.stringify(raw);
    if (payload.length > MAX_RAW_PAYLOAD_CHARS) return;
    await this.rawRepo.insert({ fetchLogId: log.id, sourceCode: log.sourceCode, targetKey: log.targetKey, payload });
  }

  private errorMessage(err: any): string {
    if (err instanceof ExternalApiError || err instanceof MissingApiKeyError) {
      const body: any = err.getResponse();
      return body.message ?? err.message;
    }
    return err?.message ?? String(err);
  }
}
