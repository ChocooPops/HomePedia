import { Controller, Get, Query } from '@nestjs/common';
import { ApiOperation, ApiPropertyOptional, ApiTags } from '@nestjs/swagger';
import { InjectRepository } from '@nestjs/typeorm';
import { IsIn, IsOptional, IsString } from 'class-validator';
import { Repository } from 'typeorm';
import { PaginationQueryDto } from '../common/dto/common.dto';
import { DataSourceEntity, FetchLogEntity } from './entities/sources.entities';

class FetchLogQueryDto extends PaginationQueryDto {
  @ApiPropertyOptional()
  @IsOptional()
  @IsString()
  source?: string;

  @ApiPropertyOptional({ enum: ['success', 'error', 'skipped'] })
  @IsOptional()
  @IsIn(['success', 'error', 'skipped'])
  status?: 'success' | 'error' | 'skipped';

  @ApiPropertyOptional({ description: 'Préfixe de cible, ex. « address:12 »' })
  @IsOptional()
  @IsString()
  target?: string;
}

@ApiTags('sources')
@Controller('sources')
export class SourcesController {
  constructor(
    @InjectRepository(DataSourceEntity) private readonly sources: Repository<DataSourceEntity>,
    @InjectRepository(FetchLogEntity) private readonly logs: Repository<FetchLogEntity>,
  ) {}

  @Get()
  @ApiOperation({ summary: 'Registre des sources (statut de vérification, TTL, clé requise)' })
  list() {
    return this.sources.find({ order: { domain: 'ASC', code: 'ASC' } });
  }

  @Get('fetch-logs')
  @ApiOperation({ summary: 'Journal des collectes (traçabilité, erreurs, durées)' })
  async fetchLogs(@Query() q: FetchLogQueryDto) {
    const qb = this.logs.createQueryBuilder('l').orderBy('l.fetched_at', 'DESC');
    if (q.source) qb.andWhere('l.source_code = :source', { source: q.source });
    if (q.status) qb.andWhere('l.status = :status', { status: q.status });
    if (q.target) qb.andWhere('l.target_key LIKE :target', { target: `${q.target}%` });
    const [items, total] = await qb
      .skip((q.page! - 1) * q.limit!)
      .take(q.limit)
      .getManyAndCount();
    return { total, page: q.page, limit: q.limit, items };
  }
}
