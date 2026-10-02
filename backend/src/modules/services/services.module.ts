import { Module } from '@nestjs/common';
import { TypeOrmModule } from '@nestjs/typeorm';
import { GeoModule } from '../geo/geo.module';
import {
  EducationClient,
  IgnNavigationClient,
  KeyedHealthClients,
  RechercheEntreprisesClient,
  ServicesOverpassClient,
} from './services.clients';
import { ServicesController } from './services.controller';
import { SchoolEntity, ServicePlaceEntity, TravelTimeEntity } from './services.entities';
import { ServicesService } from './services.service';

@Module({
  imports: [GeoModule, TypeOrmModule.forFeature([ServicePlaceEntity, SchoolEntity, TravelTimeEntity])],
  controllers: [ServicesController],
  providers: [ServicesService, RechercheEntreprisesClient, ServicesOverpassClient, EducationClient, IgnNavigationClient, KeyedHealthClients],
  exports: [ServicesService],
})
export class ServicesModule {}
