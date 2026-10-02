import { Controller, Get, Param, ParseIntPipe, Post, Query } from '@nestjs/common';
import { ApiOperation, ApiTags } from '@nestjs/swagger';
import { CollectQueryDto } from '../../common/dto/common.dto';
import { GeoService } from '../geo/geo.service';
import { EnergyService } from './energy.service';

@ApiTags('energy')
@Controller()
export class EnergyController {
  constructor(
    private readonly energy: EnergyService,
    private readonly geo: GeoService,
  ) {}

  @Post('addresses/:id/energy/collect')
  @ApiOperation({ summary: 'Collecte réseau de chaleur (FCU), desserte gaz (GRDF), consommation électrique (Enedis)' })
  async collect(@Param('id', ParseIntPipe) id: number, @Query() q: CollectQueryDto) {
    return this.energy.collect(await this.geo.getAddress(id), q.force);
  }

  @Get('addresses/:id/energy')
  @ApiOperation({ summary: 'Réseaux disponibles et consommation électrique résidentielle' })
  async read(@Param('id', ParseIntPipe) id: number) {
    return this.energy.read(await this.geo.getAddress(id));
  }
}
