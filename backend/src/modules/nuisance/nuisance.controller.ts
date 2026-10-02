import { Controller, Get, Param, ParseIntPipe, Post, Query } from '@nestjs/common';
import { ApiOperation, ApiTags } from '@nestjs/swagger';
import { RadiusQueryDto } from '../../common/dto/common.dto';
import { GeoService } from '../geo/geo.service';
import { NuisanceService } from './nuisance.service';

@ApiTags('nuisance')
@Controller()
export class NuisanceController {
  constructor(
    private readonly nuisances: NuisanceService,
    private readonly geo: GeoService,
  ) {}

  @Post('addresses/:id/nuisances/collect')
  @ApiOperation({ summary: 'Collecte OSM (bars, lieux de culte, élevages, STEP, lignes HT, éoliennes...), PEB, survols OpenSky' })
  async collect(@Param('id', ParseIntPipe) id: number, @Query() q: RadiusQueryDto) {
    return this.nuisances.collect(await this.geo.getAddress(id), q.force, q.radius ?? 1000);
  }

  @Get('addresses/:id/nuisances')
  @ApiOperation({ summary: 'Sources de nuisance par catégorie (nombre, plus proche), antennes, survols' })
  async read(@Param('id', ParseIntPipe) id: number, @Query() q: RadiusQueryDto) {
    return this.nuisances.read(await this.geo.getAddress(id), q.radius ?? 1000);
  }
}
