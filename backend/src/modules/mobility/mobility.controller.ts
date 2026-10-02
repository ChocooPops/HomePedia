import { Controller, Get, Param, ParseIntPipe, Post, Query } from '@nestjs/common';
import { ApiOperation, ApiTags } from '@nestjs/swagger';
import { CollectQueryDto } from '../../common/dto/common.dto';
import { GeoService } from '../geo/geo.service';
import { MobilityService } from './mobility.service';

@ApiTags('mobility')
@Controller()
export class MobilityController {
  constructor(
    private readonly mobility: MobilityService,
    private readonly geo: GeoService,
  ) {}

  @Post('addresses/:id/mobility/collect')
  @ApiOperation({ summary: 'Collecte bornes IRVE, parkings, arrêts de transport, aménagements cyclables, flux GTFS' })
  async collect(@Param('id', ParseIntPipe) id: number, @Query() q: CollectQueryDto) {
    return this.mobility.collect(await this.geo.getAddress(id), q.force);
  }

  @Get('addresses/:id/mobility')
  @ApiOperation({ summary: 'Arrêts à moins de 800 m, bornes de recharge, parkings, pistes cyclables' })
  async read(@Param('id', ParseIntPipe) id: number) {
    return this.mobility.read(await this.geo.getAddress(id));
  }
}
