import { Injectable } from '@nestjs/common';
import { TabularClient } from '../../common/clients/open-data.clients';
import { LatLon, squareGeoJson } from '../../common/geo/geo.utils';
import { HttpClientService } from '../../common/http/http-client.service';

/** Récupération brute (aucune transformation) des sources du module géo. */

export interface BanFeature {
  type: 'Feature';
  geometry: { type: 'Point'; coordinates: [number, number] };
  properties: {
    label: string;
    score: number;
    housenumber?: string;
    id: string;
    banId?: string;
    name?: string;
    postcode?: string;
    citycode: string;
    city?: string;
    street?: string;
    type: 'housenumber' | 'street' | 'locality' | 'municipality';
  };
}

@Injectable()
export class BanClient {
  static readonly BASE = 'https://data.geopf.fr/geocodage';

  constructor(private readonly http: HttpClientService) {}

  async search(q: string, opts: { limit?: number; postcode?: string; citycode?: string; near?: LatLon } = {}): Promise<BanFeature[]> {
    const res: any = await this.http.get(`${BanClient.BASE}/search`, {
      source: 'ban',
      params: {
        q,
        limit: opts.limit ?? 5,
        postcode: opts.postcode,
        citycode: opts.citycode,
        lat: opts.near?.lat,
        lon: opts.near?.lon,
        index: 'address',
      },
    });
    return res.features ?? [];
  }

  async reverse(p: LatLon, limit = 1): Promise<BanFeature[]> {
    const res: any = await this.http.get(`${BanClient.BASE}/reverse`, {
      source: 'ban',
      params: { lat: p.lat, lon: p.lon, limit, index: 'address' },
    });
    return res.features ?? [];
  }
}

@Injectable()
export class GeoApiClient {
  static readonly BASE = 'https://geo.api.gouv.fr';
  private static readonly FIELDS =
    'nom,code,codesPostaux,codeDepartement,codeRegion,departement,region,codeEpci,population,surface,centre';

  constructor(private readonly http: HttpClientService) {}

  async commune(insee: string): Promise<any | null> {
    const res: any[] = await this.http.get(`${GeoApiClient.BASE}/communes`, {
      source: 'geo_api',
      params: { code: insee, fields: GeoApiClient.FIELDS, format: 'json' },
    });
    return res[0] ?? null;
  }

  async communesOfDepartment(dep: string): Promise<any[]> {
    return this.http.get(`${GeoApiClient.BASE}/departements/${dep}/communes`, {
      source: 'geo_api',
      params: { fields: GeoApiClient.FIELDS, format: 'json' },
    });
  }
}

@Injectable()
export class CadastreClient {
  static readonly URL = 'https://apicarto.ign.fr/api/cadastre/parcelle';

  constructor(private readonly http: HttpClientService) {}

  /** L'API ne renvoie rien pour une géométrie Point : on interroge avec un carré de quelques mètres. */
  async parcelsAround(p: LatLon, halfSideM = 6): Promise<any[]> {
    const res: any = await this.http.get(CadastreClient.URL, {
      source: 'apicarto_cadastre',
      params: { geom: JSON.stringify(squareGeoJson(p, halfSideM)), _limit: 50 },
    });
    return res.features ?? [];
  }

  async parcelByIdu(idu: string): Promise<any | null> {
    const res: any = await this.http.get(CadastreClient.URL, {
      source: 'apicarto_cadastre',
      params: { code_insee: idu.slice(0, 5), com_abs: idu.slice(5, 8), section: idu.slice(8, 10), numero: idu.slice(10, 14) },
    });
    return (res.features ?? []).find((f: any) => f.properties?.idu === idu) ?? null;
  }
}

export type GpuLayer = 'zone-urba' | 'prescription-surf' | 'prescription-lin' | 'prescription-pct' | 'assiette-sup-s';

@Injectable()
export class GpuClient {
  static readonly BASE = 'https://apicarto.ign.fr/api/gpu';

  constructor(private readonly http: HttpClientService) {}

  /** Objets d'une couche GPU intersectant une géométrie GeoJSON. */
  async layer(layer: GpuLayer, geometry: object): Promise<any[]> {
    const res: any = await this.http.get(`${GpuClient.BASE}/${layer}`, {
      source: 'apicarto_gpu',
      params: { geom: JSON.stringify(geometry) },
      timeout: 60000,
    });
    return res.features ?? [];
  }
}

/**
 * Liste des immeubles protégés MH (Ministère de la Culture).
 * data.culture.gouv.fr a migré (redirection vers culture.data.gouv.fr, sans API Opendatasoft) :
 * on interroge la même ressource publiée sur data.gouv.fr via l'API tabulaire.
 */
@Injectable()
export class MonumentsClient {
  static readonly RESOURCE_ID = '3a52af4a-f9da-4dcc-8110-b07774dfb3bc';

  constructor(private readonly tabular: TabularClient) {}

  byCommune(insee: string) {
    return this.tabular.query('monuments', MonumentsClient.RESOURCE_ID, { COG_Insee_lors_de_la_protection: insee }, { maxRows: 500 });
  }
}
