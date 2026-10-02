import { Body, Controller, Get, Param, ParseIntPipe, Post, Query } from '@nestjs/common';
import { ApiOperation, ApiProperty, ApiPropertyOptional, ApiTags } from '@nestjs/swagger';
import { Type } from 'class-transformer';
import { ArrayMinSize, IsArray, IsIn, IsInt, IsOptional, IsString, IsUrl, Matches, Max, MaxLength, Min, ValidateNested } from 'class-validator';
import { CollectQueryDto, InseeParamDto, RadiusQueryDto } from '../../common/dto/common.dto';
import { GeoService } from '../geo/geo.service';
import { RiskService } from './risk.service';

export const BIO_SPECIES = ['tiger_mosquito', 'asian_hornet', 'termite', 'dry_rot', 'wolf', 'wild_boar', 'tick_lyme', 'bed_bug', 'rat'] as const;

class BioRiskDto {
  @ApiProperty({ enum: ['commune', 'department'] })
  @IsIn(['commune', 'department'])
  scope: 'commune' | 'department';

  @ApiProperty({ example: '80', description: 'Code INSEE commune ou code département' })
  @Matches(/^(\d{2,3}|2[AB]|\d{5}|2[AB]\d{3})$/)
  areaCode: string;

  @ApiProperty({ enum: BIO_SPECIES })
  @IsIn(BIO_SPECIES)
  species: string;

  @ApiProperty({ example: 'colonisé' })
  @IsString()
  @MaxLength(80)
  status: string;

  @ApiProperty({ example: 2026 })
  @Type(() => Number)
  @IsInt()
  @Min(1990)
  @Max(2100)
  year: number;

  @ApiPropertyOptional()
  @IsOptional()
  @IsUrl()
  referenceUrl?: string;

  @ApiPropertyOptional()
  @IsOptional()
  @IsString()
  @MaxLength(500)
  notes?: string;
}

class BioRiskBatchDto {
  @ApiProperty({ type: [BioRiskDto] })
  @IsArray()
  @ArrayMinSize(1)
  @ValidateNested({ each: true })
  @Type(() => BioRiskDto)
  items: BioRiskDto[];
}

class BioRiskQueryDto {
  @ApiPropertyOptional({ example: '80' })
  @IsOptional()
  @IsString()
  areaCode?: string;

  @ApiPropertyOptional({ example: 'tiger_mosquito,termite' })
  @IsOptional()
  @IsString()
  species?: string;
}

@ApiTags('risk')
@Controller()
export class RiskController {
  constructor(
    private readonly risks: RiskService,
    private readonly geo: GeoService,
  ) {}

  @Post('addresses/:id/risks/collect')
  @ApiOperation({ summary: 'Collecte Géorisques (rapport, radon, sismicité, CatNat, sites ICPE/SSP/cavités) + OLD' })
  async collect(@Param('id', ParseIntPipe) id: number, @Query() q: CollectQueryDto) {
    return this.risks.collect(await this.geo.getAddress(id), q.force);
  }

  @Get('addresses/:id/risks')
  @ApiOperation({ summary: 'Synthèse des risques à l’adresse' })
  async read(@Param('id', ParseIntPipe) id: number, @Query() q: RadiusQueryDto) {
    return this.risks.read(await this.geo.getAddress(id), q.radius ?? 1000);
  }

  @Get('communes/:insee/catnat')
  @ApiOperation({ summary: 'Historique des arrêtés de catastrophe naturelle de la commune' })
  catnat(@Param() p: InseeParamDto) {
    return this.risks.catnatOf(p.insee);
  }

  @Post('bio-risks')
  @ApiOperation({ summary: 'Saisie / import de risques biologiques (aucune API nationale : moustique tigre, termites...)' })
  async upsertBio(@Body() dto: BioRiskBatchDto) {
    await this.risks.upsertBioRisks(dto.items);
    return { upserted: dto.items.length };
  }

  @Get('bio-risks')
  @ApiOperation({ summary: 'Liste des risques biologiques saisis' })
  listBio(@Query() q: BioRiskQueryDto) {
    return this.risks.listBioRisks(q);
  }
}
