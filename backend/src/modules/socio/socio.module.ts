import { Module } from '@nestjs/common';
import { TypeOrmModule } from '@nestjs/typeorm';
import { GeoModule } from '../geo/geo.module';
import { FiscaliteClient, MelodiClient, SsmsiClient } from './socio.clients';
import { SocioController } from './socio.controller';
import { CrimeStatEntity, LocalTaxRateEntity, SocioIndicatorEntity } from './socio.entities';
import { SocioService } from './socio.service';

@Module({
  imports: [GeoModule, TypeOrmModule.forFeature([SocioIndicatorEntity, CrimeStatEntity, LocalTaxRateEntity])],
  controllers: [SocioController],
  providers: [SocioService, MelodiClient, FiscaliteClient, SsmsiClient],
  exports: [SocioService],
})
export class SocioModule {}
