import { Module } from '@nestjs/common';
import { TypeOrmModule } from '@nestjs/typeorm';
import { GeoModule } from '../geo/geo.module';
import { AtmoClient, OpenMeteoClient, PvgisClient } from './climate.clients';
import { ClimateController } from './climate.controller';
import { AirQualityIndexEntity, ClimateProjectionEntity, SolarPotentialEntity } from './climate.entities';
import { ClimateService } from './climate.service';

@Module({
  imports: [GeoModule, TypeOrmModule.forFeature([ClimateProjectionEntity, SolarPotentialEntity, AirQualityIndexEntity])],
  controllers: [ClimateController],
  providers: [ClimateService, OpenMeteoClient, PvgisClient, AtmoClient],
  exports: [ClimateService],
})
export class ClimateModule {}
