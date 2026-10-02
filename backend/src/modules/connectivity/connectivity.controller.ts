import { Controller, Get, Param, ParseIntPipe, Post, Query } from '@nestjs/common';
import { ApiOperation, ApiTags } from '@nestjs/swagger';
import { CollectQueryDto } from '../../common/dto/common.dto';
import { GeoService } from '../geo/geo.service';
import { ConnectivityService } from './connectivity.service';

@ApiTags('connectivity')
@Controller()
export class ConnectivityController {
  constructor(
    private readonly connectivity: ConnectivityService,
    private readonly geo: GeoService,
  ) {}

  @Post('connectivity/fixed/import')
  @ApiOperation({ summary: 'Importe l’éligibilité fixe par commune (ARCEP, ~35 000 communes)' })
  importFixed(@Query() q: CollectQueryDto) {
    return this.connectivity.importFixed(q.force);
  }

  @Post('connectivity/mobile-sites/import')
  @ApiOperation({ summary: 'Importe les sites mobiles 2G/3G/4G/5G par opérateur (ARCEP, ~125 000 sites)' })
  importMobile(@Query() q: CollectQueryDto) {
    return this.connectivity.importMobileSites(q.force);
  }

  @Post('addresses/:id/connectivity/collect')
  @ApiOperation({ summary: 'S’assure que les référentiels ARCEP sont chargés' })
  async collect(@Param('id', ParseIntPipe) id: number, @Query() q: CollectQueryDto) {
    return this.connectivity.collect(await this.geo.getAddress(id), q.force);
  }

  @Get('addresses/:id/connectivity')
  @ApiOperation({ summary: 'Fibre (taux communal) et proximité des antennes 4G/5G par opérateur' })
  async read(@Param('id', ParseIntPipe) id: number) {
    return this.connectivity.read(await this.geo.getAddress(id));
  }
}
