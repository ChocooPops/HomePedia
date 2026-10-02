import { Controller, Get, Param, Post, Query } from '@nestjs/common';
import { ApiOperation, ApiTags } from '@nestjs/swagger';
import { CollectQueryDto, InseeParamDto } from '../../common/dto/common.dto';
import { SocioService } from './socio.service';

@ApiTags('socio')
@Controller('communes/:insee/socio')
export class SocioController {
  constructor(private readonly socio: SocioService) {}

  @Post('collect')
  @ApiOperation({ summary: 'Collecte recensement (Melodi), fiscalité locale (DGFiP), délinquance (SSMSI)' })
  collect(@Param() p: InseeParamDto, @Query() q: CollectQueryDto) {
    return this.socio.collect(p.insee, q.force);
  }

  @Get()
  @ApiOperation({ summary: 'Âge, résidences secondaires, vacance, ancienneté, taxe foncière, délinquance' })
  read(@Param() p: InseeParamDto) {
    return this.socio.read(p.insee);
  }
}
