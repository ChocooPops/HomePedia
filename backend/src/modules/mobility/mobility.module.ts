import { Module } from '@nestjs/common';
import { TypeOrmModule } from '@nestjs/typeorm';
import { GeoModule } from '../geo/geo.module';
import { MobilityController } from './mobility.controller';
import { ChargingStationEntity, ParkingFacilityEntity, TransitFeedEntity, TransitStopEntity } from './mobility.entities';
import { MobilityService } from './mobility.service';

@Module({
  imports: [GeoModule, TypeOrmModule.forFeature([ChargingStationEntity, ParkingFacilityEntity, TransitStopEntity, TransitFeedEntity])],
  controllers: [MobilityController],
  providers: [MobilityService],
  exports: [MobilityService],
})
export class MobilityModule {}
