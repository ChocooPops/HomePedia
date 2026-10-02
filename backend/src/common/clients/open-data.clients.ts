import { Injectable } from '@nestjs/common';
import { HttpClientService } from '../http/http-client.service';

/**
 * Clients génériques pour les grandes familles de portails open data.
 * Ils gèrent la pagination ; la normalisation reste dans chaque module.
 */

/** API tabulaire data.gouv.fr : interroge un CSV publié sans le télécharger. */
@Injectable()
export class TabularClient {
  static readonly BASE = 'https://tabular-api.data.gouv.fr/api/resources';

  constructor(private readonly http: HttpClientService) {}

  /**
   * @param filters colonne -> valeur exacte (traduit en `col__exact=valeur`)
   */
  async query<T = Record<string, any>>(
    source: string,
    resourceId: string,
    filters: Record<string, string | number>,
    opts: { pageSize?: number; maxRows?: number; extra?: Record<string, string> } = {},
  ): Promise<T[]> {
    const pageSize = Math.min(opts.pageSize ?? 50, 50);
    const maxRows = opts.maxRows ?? 1000;
    const params: Record<string, string | number> = { page_size: pageSize, ...(opts.extra ?? {}) };
    for (const [k, v] of Object.entries(filters)) params[`${k}__exact`] = v;

    const rows: T[] = [];
    let url: string | null = `${TabularClient.BASE}/${resourceId}/data/`;
    let first = true;
    while (url && rows.length < maxRows) {
      const page: any = await this.http.get(url, { source, limiterKey: 'tabular', params: first ? params : undefined });
      rows.push(...(page.data ?? []));
      url = page.links?.next ?? null;
      first = false;
    }
    return rows.slice(0, maxRows);
  }
}

/** API Explore v2.1 des portails Opendatasoft (data.education, data.economie, GRDF...). */
@Injectable()
export class OdsClient {
  constructor(private readonly http: HttpClientService) {}

  async records<T = Record<string, any>>(
    source: string,
    baseUrl: string,
    dataset: string,
    params: { where?: string; select?: string; order_by?: string; refine?: string },
    maxRecords = 100,
  ): Promise<T[]> {
    const out: T[] = [];
    const limit = Math.min(100, maxRecords);
    for (let offset = 0; offset < maxRecords && offset < 10000; offset += limit) {
      const page: any = await this.http.get(`${baseUrl}/catalog/datasets/${dataset}/records`, {
        source,
        params: { ...params, limit, offset },
      });
      const results: T[] = page.results ?? [];
      out.push(...results);
      if (results.length < limit || out.length >= (page.total_count ?? 0)) break;
    }
    return out.slice(0, maxRecords);
  }
}

/** API data-fair (ADEME, Enedis). */
@Injectable()
export class DataFairClient {
  constructor(private readonly http: HttpClientService) {}

  async lines<T = Record<string, any>>(
    source: string,
    datasetUrl: string,
    params: Record<string, string | number>,
    maxRows = 100,
  ): Promise<T[]> {
    const out: T[] = [];
    let url: string | null = `${datasetUrl}/lines`;
    let first = true;
    while (url && out.length < maxRows) {
      const page: any = await this.http.get(url, {
        source,
        params: first ? { size: Math.min(maxRows, 1000), ...params } : undefined,
      });
      out.push(...(page.results ?? []));
      url = page.next ?? null;
      first = false;
    }
    return out.slice(0, maxRows);
  }
}

export interface OverpassElement {
  type: 'node' | 'way' | 'relation';
  id: number;
  lat?: number;
  lon?: number;
  center?: { lat: number; lon: number };
  geometry?: Array<{ lat: number; lon: number }>;
  tags?: Record<string, string>;
}

/**
 * OpenStreetMap Overpass. Le serveur principal renvoie 406 si le User-Agent est absent ou factice,
 * et 504 quand il est saturé : on bascule alors sur un miroir public.
 */
@Injectable()
export class OverpassClient {
  static readonly ENDPOINTS = ['https://overpass-api.de/api/interpreter', 'https://overpass.kumi.systems/api/interpreter'];

  constructor(private readonly http: HttpClientService) {}

  async query(ql: string): Promise<OverpassElement[]> {
    const body = new URLSearchParams({ data: ql }).toString();
    let lastError: unknown;
    for (const url of OverpassClient.ENDPOINTS) {
      try {
        const res: any = await this.http.post(url, body, {
          source: 'overpass',
          headers: { 'Content-Type': 'application/x-www-form-urlencoded', Accept: '*/*' },
          timeout: 90000,
        });
        return res.elements ?? [];
      } catch (err) {
        lastError = err;
      }
    }
    throw lastError;
  }
}

/** WFS de la Géoplateforme IGN (GeoJSON, WGS84). */
@Injectable()
export class WfsClient {
  static readonly URL = 'https://data.geopf.fr/wfs/ows';

  constructor(private readonly http: HttpClientService) {}

  async features(
    typeName: string,
    bbox: { minLat: number; minLon: number; maxLat: number; maxLon: number },
    count = 200,
  ): Promise<any[]> {
    const res: any = await this.http.get(WfsClient.URL, {
      source: 'geopf_wfs',
      params: {
        SERVICE: 'WFS',
        VERSION: '2.0.0',
        REQUEST: 'GetFeature',
        TYPENAMES: typeName,
        OUTPUTFORMAT: 'application/json',
        SRSNAME: 'EPSG:4326',
        COUNT: count,
        // En WFS 2.0 + EPSG:4326, l'ordre des axes du BBOX est lat,lon.
        BBOX: `${bbox.minLat},${bbox.minLon},${bbox.maxLat},${bbox.maxLon},urn:ogc:def:crs:EPSG::4326`,
      },
    });
    return res.features ?? [];
  }
}
