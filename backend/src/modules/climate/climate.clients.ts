import { Injectable } from '@nestjs/common';
import { ConfigService } from '@nestjs/config';
import { LatLon } from '../../common/geo/geo.utils';
import { MissingApiKeyError } from '../../common/http/external-api.error';
import { HttpClientService } from '../../common/http/http-client.service';

export const ARCHIVE_DAILY_VARS = [
  'temperature_2m_min', 'temperature_2m_max', 'snowfall_sum', 'wind_gusts_10m_max', 'sunshine_duration', 'precipitation_sum',
];

/**
 * Modèles CMIP6 HighResMIP d'Open-Meteo retenus (EC_Earth3P_HR renvoie des valeurs nulles après 2049).
 * Open-Meteo facture les requêtes au volume (variables × durée) : 3 modèles × 2 périodes de 10 ans
 * restent sous le quota gratuit de 600 « appels » par minute.
 */
export const CLIMATE_MODELS = ['MRI_AGCM3_2_S', 'CMCC_CM2_VHR4', 'MPI_ESM1_2_XR'];

@Injectable()
export class OpenMeteoClient {
  constructor(private readonly http: HttpClientService) {}

  archive(p: LatLon, start: string, end: string) {
    return this.http.get('https://archive-api.open-meteo.com/v1/archive', {
      source: 'open_meteo_archive',
      params: { latitude: p.lat, longitude: p.lon, start_date: start, end_date: end, daily: ARCHIVE_DAILY_VARS.join(','), timezone: 'Europe/Paris' },
      timeout: 60000,
    });
  }

  climate(p: LatLon, start: string, end: string) {
    return this.http.get('https://climate-api.open-meteo.com/v1/climate', {
      source: 'open_meteo_climate',
      params: {
        latitude: p.lat,
        longitude: p.lon,
        start_date: start,
        end_date: end,
        models: CLIMATE_MODELS.join(','),
        daily: 'temperature_2m_max,temperature_2m_min,precipitation_sum',
      },
      timeout: 90000,
    });
  }
}

@Injectable()
export class PvgisClient {
  constructor(private readonly http: HttpClientService) {}

  /** Production d'un système de 1 kWc, inclinaison/orientation optimales, masque d'horizon topographique inclus. */
  pvcalc(p: LatLon) {
    return this.http.get('https://re.jrc.ec.europa.eu/api/v5_3/PVcalc', {
      source: 'pvgis',
      params: { lat: p.lat, lon: p.lon, peakpower: 1, loss: 14, optimalangles: 1, usehorizon: 1, outputformat: 'json' },
    });
  }
}

/**
 * Atmo France (indice ATMO et pollens). Authentification par compte : POST /login -> jeton.
 * Non testé faute de compte : implémenté d'après la documentation publique de l'API.
 */
@Injectable()
export class AtmoClient {
  static readonly BASE = 'https://admindata.atmo-france.org/api';
  private token: { value: string; expires: number } | null = null;

  constructor(
    private readonly http: HttpClientService,
    private readonly config: ConfigService,
  ) {}

  private async auth(): Promise<string> {
    const username = this.config.get<string>('keys.atmoUsername');
    const password = this.config.get<string>('keys.atmoPassword');
    if (!username || !password) throw new MissingApiKeyError('atmo', 'ATMO_USERNAME / ATMO_PASSWORD');
    if (this.token && this.token.expires > Date.now()) return this.token.value;
    const res: any = await this.http.post(`${AtmoClient.BASE}/login`, { username, password }, { source: 'atmo' });
    this.token = { value: res.token, expires: Date.now() + 20 * 3600 * 1000 };
    return res.token;
  }

  async indices(kind: 'atmo' | 'pollens', insee: string, date: string): Promise<any[]> {
    const token = await this.auth();
    const res: any = await this.http.get(`${AtmoClient.BASE}/v2/data/indices/${kind}`, {
      source: 'atmo',
      headers: { Authorization: `Bearer ${token}` },
      params: { format: 'geojson', code_zone: insee, date, date_historique: date },
    });
    return res.features ?? [];
  }
}
