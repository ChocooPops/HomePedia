import { Controller, Get, Param, ParseIntPipe, Post, Query } from '@nestjs/common';
import { ApiOperation, ApiProperty, ApiTags } from '@nestjs/swagger';
import { IsIn } from 'class-validator';
import { CollectQueryDto, InseeParamDto } from '../../common/dto/common.dto';
import { GeoService } from '../geo/geo.service';
import { WATER_PARAMETERS } from './water.clients';
import { WaterService } from './water.service';

class ParameterQueryDto {
  @ApiProperty({ enum: Object.keys(WATER_PARAMETERS), example: '1340', description: 'Code SANDRE du paramètre' })
  @IsIn(Object.keys(WATER_PARAMETERS))
  parameter: string;
}

@ApiTags('water')
@Controller()
export class WaterController {
  constructor(
    private readonly water: WaterService,
    private readonly geo: GeoService,
  ) {}

  @Post('addresses/:id/water/collect')
  @ApiOperation({ summary: 'Collecte qualité de l’eau (Hub’Eau), nappes, restrictions sécheresse (VigiEau)' })
  async collect(@Param('id', ParseIntPipe) id: number, @Query() q: CollectQueryDto) {
    return this.water.collect(await this.geo.getAddress(id), q.force);
  }

  @Get('addresses/:id/water')
  @ApiOperation({ summary: 'Dernières analyses (nitrates, pesticides, PFAS, dureté), sécheresse, nappes' })
  async read(@Param('id', ParseIntPipe) id: number) {
    return this.water.read(await this.geo.getAddress(id));
  }

  @Get('communes/:insee/water-quality')
  @ApiOperation({ summary: 'Historique d’un paramètre de qualité de l’eau dans la commune' })
  history(@Param() p: InseeParamDto, @Query() q: ParameterQueryDto) {
    return this.water.history(p.insee, q.parameter);
  }
}
