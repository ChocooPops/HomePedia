import { Module } from '@nestjs/common';
import { TypeOrmModule } from '@nestjs/typeorm';
import { GeoModule } from '../geo/geo.module';
import { HubeauClient, VigieauClient } from './water.clients';
import { WaterController } from './water.controller';
import { DroughtRestrictionEntity, GroundwaterStationEntity, WaterQualityResultEntity } from './water.entities';
import { WaterService } from './water.service';

@Module({
  imports: [GeoModule, TypeOrmModule.forFeature([WaterQualityResultEntity, GroundwaterStationEntity, DroughtRestrictionEntity])],
  controllers: [WaterController],
  providers: [WaterService, HubeauClient, VigieauClient],
  exports: [WaterService],
})
export class WaterModule {}
