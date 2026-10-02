import { Module } from '@nestjs/common';
import { TypeOrmModule } from '@nestjs/typeorm';
import { GeoModule } from '../geo/geo.module';
import { BdnbClient, DpeClient, DvfClient, RnbClient, RnicClient } from './building.clients';
import { BuildingController } from './building.controller';
import { BuildingEntity, CondominiumEntity, DpeCertificateEntity, DvfMutationEntity, PriceIndexEntity } from './building.entities';
import { BuildingService } from './building.service';

@Module({
  imports: [
    GeoModule,
    TypeOrmModule.forFeature([BuildingEntity, DpeCertificateEntity, DvfMutationEntity, PriceIndexEntity, CondominiumEntity]),
  ],
  controllers: [BuildingController],
  providers: [BuildingService, RnbClient, BdnbClient, DpeClient, DvfClient, RnicClient],
  exports: [BuildingService],
})
export class BuildingModule {}
