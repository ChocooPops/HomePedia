import { Global, Module } from '@nestjs/common';
import { TypeOrmModule } from '@nestjs/typeorm';
import { CollectorService } from './collector.service';
import { DataSourceEntity, FetchLogEntity, RawPayloadEntity } from './entities/sources.entities';
import { SourcesController } from './sources.controller';

@Global()
@Module({
  imports: [TypeOrmModule.forFeature([DataSourceEntity, FetchLogEntity, RawPayloadEntity])],
  controllers: [SourcesController],
  providers: [CollectorService],
  exports: [CollectorService],
})
export class SourcesModule {}
