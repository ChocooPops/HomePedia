import { Module } from '@nestjs/common';
import { TypeOrmModule } from '@nestjs/typeorm';
import { GeoModule } from '../geo/geo.module';
import { ConnectivityController } from './connectivity.controller';
import { FixedCoverageEntity, MobileSiteEntity } from './connectivity.entities';
import { ConnectivityService } from './connectivity.service';

@Module({
  imports: [GeoModule, TypeOrmModule.forFeature([FixedCoverageEntity, MobileSiteEntity])],
  controllers: [ConnectivityController],
  providers: [ConnectivityService],
  exports: [ConnectivityService],
})
export class ConnectivityModule {}
