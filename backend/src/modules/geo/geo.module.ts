import { Module } from '@nestjs/common';
import { TypeOrmModule } from '@nestjs/typeorm';
import { BanClient, CadastreClient, GeoApiClient, GpuClient, MonumentsClient } from './geo.clients';
import { GeoController } from './geo.controller';
import {
  AddressEntity,
  AddressIndicatorEntity,
  CommuneEntity,
  MonumentEntity,
  ParcelEntity,
  PluPrescriptionEntity,
  PluZoneEntity,
  PublicEasementEntity,
} from './geo.entities';
import { GeoService } from './geo.service';
import { UrbanismService } from './urbanism.service';

@Module({
  imports: [
    TypeOrmModule.forFeature([
      CommuneEntity,
      ParcelEntity,
      AddressEntity,
      AddressIndicatorEntity,
      PluZoneEntity,
      PluPrescriptionEntity,
      PublicEasementEntity,
      MonumentEntity,
    ]),
  ],
  controllers: [GeoController],
  providers: [GeoService, UrbanismService, BanClient, GeoApiClient, CadastreClient, GpuClient, MonumentsClient],
  exports: [GeoService, UrbanismService],
})
export class GeoModule {}
