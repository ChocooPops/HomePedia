import { Injectable } from '@nestjs/common';
import { ConfigService } from '@nestjs/config';
import { OdsClient, TabularClient } from '../../common/clients/open-data.clients';
import { HttpClientService } from '../../common/http/http-client.service';

/** INSEE Melodi (recensement). Accès anonyme possible, quota relevé avec une clé. */
@Injectable()
export class MelodiClient {
  static readonly BASE = 'https://api.insee.fr/melodi';
  private readonly headers: Record<string, string>;

  constructor(
    private readonly http: HttpClientService,
    config: ConfigService,
  ) {
    const key = config.get<string>('keys.insee');
    this.headers = key ? { 'X-INSEE-Api-Key-Integration': key } : {};
  }

  async observations(dataset: string, filters: Record<string, string>): Promise<any[]> {
    const res: any = await this.http.get(`${MelodiClient.BASE}/data/${dataset}`, {
      source: 'insee_melodi',
      headers: this.headers,
      params: { ...filters, maxResult: 1000 },
      timeout: 60000,
    });
    return res.observations ?? [];
  }
}

@Injectable()
export class FiscaliteClient {
  constructor(private readonly ods: OdsClient) {}

  byCommune(insee: string) {
    return this.ods.records('fiscalite_locale', 'https://data.economie.gouv.fr/api/explore/v2.1', 'fiscalite-locale-des-particuliers', {
      where: `insee_com="${insee}"`,
      order_by: 'exercice DESC',
    }, 20);
  }
}

/** SSMSI : base communale de la délinquance enregistrée (fichier publié sur data.gouv.fr). */
@Injectable()
export class SsmsiClient {
  static readonly RESOURCE_ID = '44ef4323-1097-48d5-8719-3c544b55d294';

  constructor(private readonly tabular: TabularClient) {}

  byCommune(insee: string) {
    return this.tabular.query('ssmsi', SsmsiClient.RESOURCE_ID, { CODGEO_2026: insee }, { maxRows: 600 });
  }
}
