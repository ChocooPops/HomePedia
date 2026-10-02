import { Module } from '@nestjs/common';
import { TypeOrmModule } from '@nestjs/typeorm';
import { GeoModule } from '../geo/geo.module';
import { EnergyController } from './energy.controller';
import { ElectricityConsumptionEntity, EnergyNetworkAccessEntity } from './energy.entities';
import { EnergyService } from './energy.service';

@Module({
  imports: [GeoModule, TypeOrmModule.forFeature([EnergyNetworkAccessEntity, ElectricityConsumptionEntity])],
  controllers: [EnergyController],
  providers: [EnergyService],
  exports: [EnergyService],
})
export class EnergyModule {}
