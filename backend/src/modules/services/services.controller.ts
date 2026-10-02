import { Controller, Get, Param, ParseIntPipe, Post, Query } from '@nestjs/common';
import { ApiOperation, ApiTags } from '@nestjs/swagger';
import { CollectQueryDto, RadiusQueryDto } from '../../common/dto/common.dto';
import { GeoService } from '../geo/geo.service';
import { ServicesService } from './services.service';

@ApiTags('services')
@Controller()
export class ServicesController {
  constructor(
    private readonly services: ServicesService,
    private readonly geo: GeoService,
  ) {}

  @Post('addresses/:id/services/collect')
  @ApiOperation({ summary: 'Collecte santé, commerces, crèches, écoles (IPS, effectifs) et temps de trajet IGN' })
  async collect(@Param('id', ParseIntPipe) id: number, @Query() q: CollectQueryDto) {
    return this.services.collect(await this.geo.getAddress(id), q.force);
  }

  @Get('addresses/:id/services')
  @ApiOperation({ summary: 'Services par catégorie, urgences, boulangeries ouvertes le dimanche, temps de trajet' })
  async read(@Param('id', ParseIntPipe) id: number) {
    return this.services.read(await this.geo.getAddress(id));
  }

  @Get('addresses/:id/schools')
  @ApiOperation({ summary: 'Écoles, collèges, lycées à proximité avec IPS et taille moyenne des classes' })
  async schools(@Param('id', ParseIntPipe) id: number, @Query() q: RadiusQueryDto) {
    return this.services.schoolsAround(await this.geo.getAddress(id), q.radius ?? 1500);
  }
}
