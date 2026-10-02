import { Injectable } from '@nestjs/common';
import { LatLon } from '../../common/geo/geo.utils';
import { HttpClientService } from '../../common/http/http-client.service';

/**
 * Géorisques API v1. Endpoints vérifiés le 2026-10-02.
 * Obsolètes / défaillants : /rga (corps vide), /tri, /canalisations, /remontees_nappes (404),
 * /gaspar/pprn (ignore le filtre code_insee). Le « rapport de risque » couvre ces aléas à l'adresse.
 */
@Injectable()
export class GeorisquesClient {
  static readonly BASE = 'https://georisques.gouv.fr/api/v1';

  constructor(private readonly http: HttpClientService) {}

  private get<T = any>(path: string, params: Record<string, any>): Promise<T> {
    return this.http.get(`${GeorisquesClient.BASE}/${path}`, { source: 'georisques', params, timeout: 45000 });
  }

  /** Toutes les pages d'un endpoint paginé (`data`, `total_pages`). */
  private async paged(path: string, params: Record<string, any>, maxPages = 10): Promise<any[]> {
    const out: any[] = [];
    for (let page = 1; page <= maxPages; page++) {
      const res: any = await this.get(path, { ...params, page, page_size: 50 });
      out.push(...(res?.data ?? []));
      if (!res?.total_pages || page >= res.total_pages) break;
    }
    return out;
  }

  report(p: LatLon) {
    return this.get('resultats_rapport_risque', { latlon: `${p.lon},${p.lat}` });
  }

  async radon(insee: string) {
    return (await this.get('radon', { code_insee: insee }))?.data?.[0] ?? null;
  }

  async seismicZone(insee: string) {
    return (await this.get('zonage_sismique', { code_insee: insee }))?.data?.[0] ?? null;
  }

  async communeRisks(insee: string) {
    return (await this.get('gaspar/risques', { code_insee: insee }))?.data?.[0] ?? null;
  }

  floodAtlases(insee: string) {
    return this.paged('gaspar/azi', { code_insee: insee }, 2);
  }

  catnat(insee: string) {
    return this.paged('gaspar/catnat', { code_insee: insee }, 20);
  }

  cavities(p: LatLon, radiusM: number) {
    return this.paged('cavites', { latlon: `${p.lon},${p.lat}`, rayon: radiusM }, 5);
  }

  groundMovements(p: LatLon, radiusM: number) {
    return this.paged('mvt', { latlon: `${p.lon},${p.lat}`, rayon: radiusM }, 5);
  }

  /** Sols pollués : réponse groupée par base ({ casias: {data}, ... }). */
  pollutedSoils(p: LatLon, radiusM: number) {
    return this.get('ssp', { latlon: `${p.lon},${p.lat}`, rayon: radiusM, page_size: 50 });
  }

  installations(p: LatLon, radiusM: number) {
    return this.paged('installations_classees', { latlon: `${p.lon},${p.lat}`, rayon: radiusM }, 6);
  }
}
