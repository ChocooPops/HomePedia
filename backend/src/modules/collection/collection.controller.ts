import { Body, Controller, Get, Param, ParseIntPipe, Post, Query } from '@nestjs/common';
import { ApiOperation, ApiTags } from '@nestjs/swagger';
import { ModulesQueryDto } from '../../common/dto/common.dto';
import { CreateAddressDto } from '../geo/geo.dto';
import { GeoService } from '../geo/geo.service';
import { CollectionService } from './collection.service';

@ApiTags('collection')
@Controller('addresses')
export class CollectionController {
  constructor(
    private readonly collection: CollectionService,
    private readonly geo: GeoService,
  ) {}

  @Post('collect')
  @ApiOperation({ summary: 'Géocode une adresse puis lance la collecte de tous les modules (one-shot)' })
  async geocodeAndCollect(@Body() dto: CreateAddressDto, @Query() q: ModulesQueryDto) {
    const modules = this.collection.parseModules(q.modules);
    const { address } = dto.q ? await this.geo.geocodeAndSave(dto.q, q.force) : await this.geo.reverseAndSave({ lat: dto.lat!, lon: dto.lon! }, q.force);
    return this.collection.collectAll(address.id, modules, q.force);
  }

  @Post(':id/collect')
  @ApiOperation({ summary: 'Collecte tous les modules (ou une sélection) pour une adresse enregistrée' })
  collect(@Param('id', ParseIntPipe) id: number, @Query() q: ModulesQueryDto) {
    return this.collection.collectAll(id, this.collection.parseModules(q.modules), q.force);
  }

  @Get(':id/report')
  @ApiOperation({ summary: 'Rapport consolidé de l’adresse (lecture des données stockées, sans appel externe)' })
  report(@Param('id', ParseIntPipe) id: number) {
    return this.collection.report(id);
  }
}
