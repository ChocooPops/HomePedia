import { Module } from '@nestjs/common';
import { TypeOrmModule } from '@nestjs/typeorm';
import { ConnectivityModule } from '../connectivity/connectivity.module';
import { GeoModule } from '../geo/geo.module';
import { NuisanceOverpassClient, OpenSkyClient } from './nuisance.clients';
import { NuisanceController } from './nuisance.controller';
import { FlightObservationEntity, NuisanceLineEntity, NuisancePoiEntity } from './nuisance.entities';
import { NuisanceService } from './nuisance.service';

@Module({
  imports: [GeoModule, ConnectivityModule, TypeOrmModule.forFeature([NuisancePoiEntity, NuisanceLineEntity, FlightObservationEntity])],
  controllers: [NuisanceController],
  providers: [NuisanceService, NuisanceOverpassClient, OpenSkyClient],
  exports: [NuisanceService],
})
export class NuisanceModule {}
