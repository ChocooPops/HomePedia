import { ApiPropertyOptional } from '@nestjs/swagger';
import { Transform, Type } from 'class-transformer';
import { IsBoolean, IsIn, IsInt, IsOptional, IsString, Matches, Max, Min } from 'class-validator';

export class CollectQueryDto {
  @ApiPropertyOptional({ description: 'Ignore le cache et force un nouvel appel aux API', default: false })
  @IsOptional()
  @Transform(({ value }) => value === true || value === 'true' || value === '1')
  @IsBoolean()
  force?: boolean = false;
}

export class RadiusQueryDto extends CollectQueryDto {
  @ApiPropertyOptional({ description: 'Rayon de recherche en mètres', default: 1000, minimum: 50, maximum: 5000 })
  @IsOptional()
  @Type(() => Number)
  @IsInt()
  @Min(50)
  @Max(5000)
  radius?: number;
}

export class InseeParamDto {
  @IsString()
  @Matches(/^(\d{5}|2[AB]\d{3})$/, { message: 'insee doit être un code commune INSEE (5 caractères)' })
  insee: string;
}

export class PaginationQueryDto {
  @ApiPropertyOptional({ default: 1 })
  @IsOptional()
  @Type(() => Number)
  @IsInt()
  @Min(1)
  page?: number = 1;

  @ApiPropertyOptional({ default: 50, maximum: 500 })
  @IsOptional()
  @Type(() => Number)
  @IsInt()
  @Min(1)
  @Max(500)
  limit?: number = 50;
}

export class ModulesQueryDto extends CollectQueryDto {
  @ApiPropertyOptional({
    description: 'Modules à collecter, séparés par des virgules (défaut : tous)',
    example: 'geo,risk,water',
  })
  @IsOptional()
  @IsString()
  modules?: string;
}

export const PROFILES = ['car', 'pedestrian'] as const;
export class ProfileQueryDto {
  @IsOptional()
  @IsIn(PROFILES)
  profile?: (typeof PROFILES)[number];
}
