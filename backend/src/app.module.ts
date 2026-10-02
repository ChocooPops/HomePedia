import { Module } from '@nestjs/common';
import { ConfigModule } from '@nestjs/config';
import { TypeOrmModule } from '@nestjs/typeorm';
import { ClientsModule } from './common/clients/clients.module';
import { HttpModule } from './common/http/http.module';
import configuration from './config/configuration';
import { buildTypeOrmOptions } from './database/typeorm-options';
import { CollectionModule } from './modules/collection/collection.module';
import { SourcesModule } from './sources/sources.module';

@Module({
  imports: [
    ConfigModule.forRoot({ isGlobal: true, load: [configuration] }),
    TypeOrmModule.forRootAsync({
      // Les migrations sont appliquées au démarrage ; le schéma n'est jamais synchronisé automatiquement.
      useFactory: () => ({ ...buildTypeOrmOptions(), entities: undefined, autoLoadEntities: true, migrationsRun: true }),
    }),
    HttpModule,
    ClientsModule,
    SourcesModule,
    // CollectionModule importe les 11 modules de domaine (géo, bâtiment, risques, eau, climat,
    // nuisances, énergie, services, socio-démo, mobilité, connectivité).
    CollectionModule,
  ],
})
export class AppModule {}
