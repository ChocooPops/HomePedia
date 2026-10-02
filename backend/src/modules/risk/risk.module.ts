import { Module } from '@nestjs/common';
import { TypeOrmModule } from '@nestjs/typeorm';
import { GeoModule } from '../geo/geo.module';
import { GeorisquesClient } from './risk.clients';
import { RiskController } from './risk.controller';
import { BioRiskEntity, CatnatDecreeEntity, CommuneRiskProfileEntity, RiskAssessmentEntity, RiskSiteEntity } from './risk.entities';
import { RiskService } from './risk.service';

@Module({
  imports: [
    GeoModule,
    TypeOrmModule.forFeature([RiskAssessmentEntity, CommuneRiskProfileEntity, CatnatDecreeEntity, RiskSiteEntity, BioRiskEntity]),
  ],
  controllers: [RiskController],
  providers: [RiskService, GeorisquesClient],
  exports: [RiskService],
})
export class RiskModule {}
