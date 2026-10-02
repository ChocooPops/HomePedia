import { Injectable } from '@nestjs/common';
import { bboxAround, LatLon } from '../../common/geo/geo.utils';
import { HttpClientService } from '../../common/http/http-client.service';

/** Paramètres suivis (codes SANDRE). */
export const WATER_PARAMETERS: Record<string, string> = {
  '1340': 'nitrates',
  '6276': 'total_pesticides',
  '1345': 'hardness',
  '8847': 'pfas_sum_20',
  '9268': 'pfas_sum_4',
};

@Injectable()
export class HubeauClient {
  static readonly BASE = 'https://hubeau.eaufrance.fr/api/v1';

  constructor(private readonly http: HttpClientService) {}

  /** Résultats d'analyse au robinet (réseau de distribution) d'une commune, les plus récents d'abord. */
  async drinkingWater(insee: string, sinceIso: string, maxRows = 1000): Promise<any[]> {
    const out: any[] = [];
    let url: string | null = `${HubeauClient.BASE}/qualite_eau_potable/resultats_dis`;
    let params: any = {
      code_commune: insee,
      code_parametre: Object.keys(WATER_PARAMETERS).join(','),
      date_min_prelevement: sinceIso,
      size: 500,
      sort: 'desc',
    };
    while (url && out.length < maxRows) {
      const res: any = await this.http.get(url, { source: 'hubeau_eau_potable', params, allowStatuses: [206] });
      out.push(...(res.data ?? []));
      url = res.next ?? null;
      params = undefined;
    }
    return out;
  }

  async groundwaterStations(p: LatLon, radiusM: number): Promise<any[]> {
    const b = bboxAround(p, radiusM);
    const res: any = await this.http.get(`${HubeauClient.BASE}/niveaux_nappes/stations`, {
      source: 'hubeau_nappes',
      params: { bbox: `${b.minLon},${b.minLat},${b.maxLon},${b.maxLat}`, size: 200 },
      allowStatuses: [206],
    });
    return res.data ?? [];
  }

  async lastGroundwaterMeasure(codeBss: string): Promise<any | null> {
    const res: any = await this.http.get(`${HubeauClient.BASE}/niveaux_nappes/chroniques`, {
      source: 'hubeau_nappes',
      params: { code_bss: codeBss, size: 1, sort: 'desc' },
      allowStatuses: [206],
    });
    return res.data?.[0] ?? null;
  }
}

@Injectable()
export class VigieauClient {
  static readonly BASE = 'https://api.vigieau.gouv.fr/api';

  constructor(private readonly http: HttpClientService) {}

  /** Zones d'alerte et restrictions en vigueur. zoneType : SUP (superficiel), SOU (souterrain), AEP (eau potable). */
  async zones(p: LatLon, insee: string, zoneType: 'SUP' | 'SOU' | 'AEP'): Promise<any[]> {
    const res = await this.http.get(`${VigieauClient.BASE}/zones`, {
      source: 'vigieau',
      params: { lon: p.lon, lat: p.lat, commune: insee, profil: 'particulier', zoneType },
      allowStatuses: [404],
    });
    return Array.isArray(res) ? res : [];
  }
}
