import { Body, Controller, Delete, Get, HttpCode, Param, ParseIntPipe, Post, Query } from '@nestjs/common';
import { ApiOperation, ApiTags } from '@nestjs/swagger';
import { CollectQueryDto, InseeParamDto, RadiusQueryDto } from '../../common/dto/common.dto';
import { AddressListQueryDto, CommuneListQueryDto, CreateAddressDto, DepartmentParamDto, IduParamDto, SearchQueryDto } from './geo.dto';
import { GeoService } from './geo.service';
import { UrbanismService } from './urbanism.service';

@ApiTags('geo')
@Controller()
export class GeoController {
  constructor(
    private readonly geo: GeoService,
    private readonly urbanism: UrbanismService,
  ) {}

  @Get('geo/search')
  @ApiOperation({ summary: 'Autocomplétion BAN (sans enregistrement)' })
  search(@Query() q: SearchQueryDto) {
    return this.geo.search(q.q, q.limit);
  }

  @Post('addresses')
  @ApiOperation({ summary: 'Géocode (texte ou lat/lon) et enregistre une adresse + sa commune + sa parcelle' })
  create(@Body() dto: CreateAddressDto, @Query() q: CollectQueryDto) {
    return dto.q ? this.geo.geocodeAndSave(dto.q, q.force) : this.geo.reverseAndSave({ lat: dto.lat!, lon: dto.lon! }, q.force);
  }

  @Get('addresses')
  @ApiOperation({ summary: 'Liste des adresses enregistrées' })
  async list(@Query() q: AddressListQueryDto) {
    const [items, total] = await this.geo.listAddresses({ insee: q.insee }, q.page!, q.limit!);
    return { total, page: q.page, limit: q.limit, items };
  }

  @Get('addresses/:id')
  @ApiOperation({ summary: 'Adresse avec sa commune et sa parcelle (géométrie GeoJSON)' })
  get(@Param('id', ParseIntPipe) id: number) {
    return this.geo.getAddressDetails(id);
  }

  @Delete('addresses/:id')
  @HttpCode(204)
  @ApiOperation({ summary: 'Supprime une adresse et les données qui lui sont rattachées' })
  remove(@Param('id', ParseIntPipe) id: number) {
    return this.geo.deleteAddress(id);
  }

  @Get('addresses/:id/indicators')
  @ApiOperation({ summary: 'Indicateurs calculés à l’adresse (tous domaines)' })
  indicators(@Param('id', ParseIntPipe) id: number) {
    return this.geo.indicatorsOf(id);
  }

  @Post('addresses/:id/urbanism/collect')
  @ApiOperation({ summary: 'Collecte PLU (zones, prescriptions), servitudes (AC1) et monuments historiques' })
  async collectUrbanism(@Param('id', ParseIntPipe) id: number, @Query() q: CollectQueryDto) {
    return this.urbanism.collect(await this.geo.getAddress(id), q.force);
  }

  @Get('addresses/:id/urbanism')
  @ApiOperation({ summary: 'Zonage PLU au point et alentours, emplacements réservés, périmètres MH' })
  async readUrbanism(@Param('id', ParseIntPipe) id: number, @Query() q: RadiusQueryDto) {
    return this.urbanism.read(await this.geo.getAddress(id), q.radius ?? 250);
  }

  @Get('communes')
  @ApiOperation({ summary: 'Communes enregistrées (filtre département / région)' })
  async communes(@Query() q: CommuneListQueryDto) {
    const [items, total] = await this.geo.listCommunes({ department: q.department, region: q.region }, q.page!, q.limit!);
    return { total, page: q.page, limit: q.limit, items };
  }

  @Get('communes/:insee')
  @ApiOperation({ summary: 'Commune (collectée à la volée si absente)' })
  commune(@Param() p: InseeParamDto) {
    return this.geo.getCommune(p.insee);
  }

  @Post('communes/:insee/collect')
  @ApiOperation({ summary: 'Recharge une commune depuis l’API Géo' })
  collectCommune(@Param() p: InseeParamDto, @Query() q: CollectQueryDto) {
    return this.geo.ensureCommune(p.insee, q.force);
  }

  @Post('departments/:dep/communes/collect')
  @ApiOperation({ summary: 'Importe toutes les communes d’un département' })
  collectDepartment(@Param() p: DepartmentParamDto, @Query() q: CollectQueryDto) {
    return this.geo.collectDepartmentCommunes(p.dep, q.force);
  }

  @Get('parcels/:idu')
  @ApiOperation({ summary: 'Parcelle cadastrale (collectée à la volée si absente)' })
  parcel(@Param() p: IduParamDto, @Query() q: CollectQueryDto) {
    return this.geo.getParcel(p.idu, q.force);
  }
}
