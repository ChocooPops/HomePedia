/**
 * Limites de débit appliquées côté client, par source.
 * Valeurs volontairement prudentes, sous les quotas publiés :
 *  - BAN / API Géo : 50 req/s ; recherche-entreprises : 7 req/s
 *  - Overpass : 2 requêtes simultanées max par IP, on reste à 1
 *  - Sirene : 30 req/min ; Melodi (anonyme) : 30 req/min
 *  - Open-Meteo gratuit : 600 req/min
 */
export interface RateLimit {
  /** Requêtes simultanées autorisées. */
  concurrency: number;
  /** Intervalle minimal entre deux départs de requête (ms). */
  minIntervalMs: number;
}

export const DEFAULT_RATE_LIMIT: RateLimit = { concurrency: 4, minIntervalMs: 100 };

export const RATE_LIMITS: Record<string, RateLimit> = {
  ban: { concurrency: 5, minIntervalMs: 25 },
  geo_api: { concurrency: 5, minIntervalMs: 25 },
  apicarto_cadastre: { concurrency: 2, minIntervalMs: 200 },
  apicarto_gpu: { concurrency: 2, minIntervalMs: 200 },
  overpass: { concurrency: 1, minIntervalMs: 1500 },
  opensky: { concurrency: 1, minIntervalMs: 10000 },
  recherche_entreprises: { concurrency: 2, minIntervalMs: 150 },
  sirene: { concurrency: 1, minIntervalMs: 2100 },
  insee_melodi: { concurrency: 1, minIntervalMs: 2100 },
  open_meteo_archive: { concurrency: 2, minIntervalMs: 200 },
  open_meteo_climate: { concurrency: 1, minIntervalMs: 500 },
  pvgis: { concurrency: 2, minIntervalMs: 100 },
  georisques: { concurrency: 3, minIntervalMs: 100 },
  tabular: { concurrency: 2, minIntervalMs: 200 },
  ign_navigation: { concurrency: 2, minIntervalMs: 100 },
  bdnb: { concurrency: 1, minIntervalMs: 500 },
};
