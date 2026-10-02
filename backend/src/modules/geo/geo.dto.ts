import { ApiPropertyOptional } from '@nestjs/swagger';
import { Type } from 'class-transformer';
import { IsInt, IsLatitude, IsLongitude, IsOptional, IsString, Matches, Max, Min, MinLength, ValidateIf } from 'class-validator';
import { PaginationQueryDto } from '../../common/dto/common.dto';

export class CreateAddressDto {
  @ApiPropertyOptional({ example: '2 rue de la République, Amiens', description: 'Adresse en texte libre (ou lat/lon)' })
  @ValidateIf((o) => o.lat === undefined || o.lon === undefined)
  @IsString()
  @MinLength(3)
  q?: string;

  @ApiPropertyOptional({ example: 49.892808 })
  @ValidateIf((o) => !o.q)
  @Type(() => Number)
  @IsLatitude()
  lat?: number;

  @ApiPropertyOptional({ example: 2.297087 })
  @ValidateIf((o) => !o.q)
  @Type(() => Number)
  @IsLongitude()
  lon?: number;
}

export class SearchQueryDto {
  @IsString()
  @MinLength(3)
  q: string;

  @ApiPropertyOptional({ default: 5, maximum: 20 })
  @IsOptional()
  @Type(() => Number)
  @IsInt()
  @Min(1)
  @Max(20)
  limit?: number = 5;
}

export class AddressListQueryDto extends PaginationQueryDto {
  @ApiPropertyOptional({ example: '80021' })
  @IsOptional()
  @Matches(/^(\d{5}|2[AB]\d{3})$/)
  insee?: string;
}

export class CommuneListQueryDto extends PaginationQueryDto {
  @ApiPropertyOptional({ example: '80' })
  @IsOptional()
  @Matches(/^(\d{2,3}|2[AB])$/)
  department?: string;

  @ApiPropertyOptional({ example: '32' })
  @IsOptional()
  @Matches(/^\d{2}$/)
  region?: string;
}

export class IduParamDto {
  @Matches(/^[0-9AB]{5}[0-9]{3}[0-9A-Z]{2}[0-9]{4}$/, { message: 'idu doit être un identifiant de parcelle à 14 caractères' })
  idu: string;
}

export class DepartmentParamDto {
  @Matches(/^(\d{2,3}|2[AB])$/)
  dep: string;
}
