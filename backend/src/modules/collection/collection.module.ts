import { Module } from '@nestjs/common';
import { BuildingModule } from '../building/building.module';
import { ClimateModule } from '../climate/climate.module';
import { ConnectivityModule } from '../connectivity/connectivity.module';
import { EnergyModule } from '../energy/energy.module';
import { GeoModule } from '../geo/geo.module';
import { MobilityModule } from '../mobility/mobility.module';
import { NuisanceModule } from '../nuisance/nuisance.module';
import { RiskModule } from '../risk/risk.module';
import { ServicesModule } from '../services/services.module';
import { SocioModule } from '../socio/socio.module';
import { WaterModule } from '../water/water.module';
import { CollectionController } from './collection.controller';
import { CollectionService } from './collection.service';

@Module({
  imports: [
    GeoModule,
    BuildingModule,
    RiskModule,
    WaterModule,
    ClimateModule,
    NuisanceModule,
    EnergyModule,
    ServicesModule,
    SocioModule,
    MobilityModule,
    ConnectivityModule,
  ],
  controllers: [CollectionController],
  providers: [CollectionService],
})
export class CollectionModule {}
