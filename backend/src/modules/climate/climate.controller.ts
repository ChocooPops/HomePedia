import { Controller, Get, Param, ParseIntPipe, Post, Query } from '@nestjs/common';
import { ApiOperation, ApiTags } from '@nestjs/swagger';
import { CollectQueryDto } from '../../common/dto/common.dto';
import { GeoService } from '../geo/geo.service';
import { ClimateService } from './climate.service';

@ApiTags('climate')
@Controller()
export class ClimateController {
  constructor(
    private readonly climate: ClimateService,
    private readonly geo: GeoService,
  ) {}

  @Post('addresses/:id/climate/collect')
  @ApiOperation({ summary: 'Collecte climat observé (10 ans), projections 2031-2050, potentiel solaire, air/pollens' })
  async collect(@Param('id', ParseIntPipe) id: number, @Query() q: CollectQueryDto) {
    return this.climate.collect(await this.geo.getAddress(id), q.force);
  }

  @Get('addresses/:id/climate')
  @ApiOperation({ summary: 'Gel, nuits tropicales, neige, vent, ensoleillement, projections, solaire, qualité de l’air' })
  async read(@Param('id', ParseIntPipe) id: number) {
    return this.climate.read(await this.geo.getAddress(id));
  }
}
