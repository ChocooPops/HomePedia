import { Controller, Get, Param, ParseIntPipe, Post, Query } from '@nestjs/common';
import { ApiOperation, ApiPropertyOptional, ApiTags } from '@nestjs/swagger';
import { Transform, Type } from 'class-transformer';
import { IsArray, IsIn, IsInt, IsOptional, Max, Min } from 'class-validator';
import { CollectQueryDto, InseeParamDto, PaginationQueryDto, RadiusQueryDto } from '../../common/dto/common.dto';
import { GeoService } from '../geo/geo.service';
import { BuildingService } from './building.service';

class DvfCollectQueryDto extends CollectQueryDto {
  @ApiPropertyOptional({ description: 'Années à importer (défaut : toutes)', example: '2023,2024' })
  @IsOptional()
  @Transform(({ value }) => String(value).split(',').map((v) => parseInt(v, 10)))
  @IsArray()
  @IsInt({ each: true })
  years?: number[];
}

class DvfListQueryDto extends PaginationQueryDto {
  @ApiPropertyOptional({ example: 2024 })
  @IsOptional()
  @Type(() => Number)
  @IsInt()
  @Min(2014)
  @Max(2100)
  year?: number;

  @ApiPropertyOptional({ enum: ['Maison', 'Appartement', 'Dépendance', 'Local industriel. commercial ou assimilé'] })
  @IsOptional()
  @IsIn(['Maison', 'Appartement', 'Dépendance', 'Local industriel. commercial ou assimilé'])
  type?: string;
}

@ApiTags('building')
@Controller()
export class BuildingController {
  constructor(
    private readonly buildings: BuildingService,
    private readonly geo: GeoService,
  ) {}

  @Post('addresses/:id/building/collect')
  @ApiOperation({ summary: 'Collecte RNB + BDNB + DPE + copropriété (RNIC) + DVF de la commune' })
  async collect(@Param('id', ParseIntPipe) id: number, @Query() q: CollectQueryDto) {
    return this.buildings.collect(await this.geo.getAddress(id), q.force);
  }

  @Get('addresses/:id/building')
  @ApiOperation({ summary: 'Bâtiment, DPE, copropriété et présomptions (plomb, amiante, interdiction de louer)' })
  async read(@Param('id', ParseIntPipe) id: number) {
    return this.buildings.read(await this.geo.getAddress(id));
  }

  @Get('addresses/:id/dvf')
  @ApiOperation({ summary: 'Ventes DVF autour de l’adresse' })
  async around(@Param('id', ParseIntPipe) id: number, @Query() q: RadiusQueryDto) {
    return this.buildings.mutationsAround(await this.geo.getAddress(id), q.radius ?? 500);
  }

  @Post('communes/:insee/dvf/collect')
  @ApiOperation({ summary: 'Importe les ventes DVF d’une commune et recalcule l’indice de prix' })
  collectDvf(@Param() p: InseeParamDto, @Query() q: DvfCollectQueryDto) {
    return this.buildings.collectDvf(p.insee, q.years, q.force);
  }

  @Get('communes/:insee/dvf')
  @ApiOperation({ summary: 'Ventes DVF d’une commune (filtre année / type)' })
  listDvf(@Param() p: InseeParamDto, @Query() q: DvfListQueryDto) {
    return this.buildings.listMutations(p.insee, { year: q.year, type: q.type }, q.page!, q.limit!);
  }

  @Get('communes/:insee/price-index')
  @ApiOperation({ summary: 'Prix au m² (médiane, moyenne, quartiles) par année et type de bien' })
  priceIndex(@Param() p: InseeParamDto) {
    return this.buildings.priceIndex(p.insee);
  }

  @Post('communes/:insee/price-index/compute')
  @ApiOperation({ summary: 'Recalcule l’indice de prix à partir des ventes stockées' })
  compute(@Param() p: InseeParamDto) {
    return this.buildings.computePriceIndex(p.insee);
  }
}
