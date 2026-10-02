import { Global, Module } from '@nestjs/common';
import { DataFairClient, OdsClient, OverpassClient, TabularClient, WfsClient } from './open-data.clients';

const clients = [TabularClient, OdsClient, DataFairClient, OverpassClient, WfsClient];

@Global()
@Module({ providers: clients, exports: clients })
export class ClientsModule {}
