import { AddressIndicatorInput } from '../geo/geo.service';

const round1 = (v: number) => Math.round(v * 10) / 10;

/**
 * Agrégats climatiques annuels moyens à partir des séries journalières Open-Meteo (réanalyse ERA5).
 * Maille ~10 km : les phénomènes très locaux (îlot de chaleur, brouillard de vallée) sont lissés.
 */
export function climateIndicators(daily: Record<string, Array<number | null>>, meta: object): AddressIndicatorInput[] {
  const days = daily.time as unknown as string[];
  const years = new Set(days.map((d) => d.slice(0, 4))).size || 1;
  const count = (key: string, pred: (v: number) => boolean) => (daily[key] ?? []).filter((v) => v !== null && pred(v)).length / years;
  const sum = (key: string, filter: (i: number) => boolean = () => true) =>
    (daily[key] ?? []).reduce<number>((acc, v, i) => acc + (v !== null && filter(i) ? v : 0), 0) / years;
  const winter = (i: number) => ['12', '01', '02'].includes(days[i].slice(5, 7));

  const items: Array<[string, number, string]> = [
    ['frost_days_per_year', count('temperature_2m_min', (v) => v < 0), 'jours/an'],
    ['severe_frost_days_per_year', count('temperature_2m_min', (v) => v <= -5), 'jours/an'],
    ['tropical_nights_per_year', count('temperature_2m_min', (v) => v >= 20), 'nuits/an'],
    ['hot_days_per_year', count('temperature_2m_max', (v) => v >= 30), 'jours/an'],
    ['snowfall_per_year', sum('snowfall_sum'), 'cm/an'],
    ['snow_days_per_year', count('snowfall_sum', (v) => v >= 1), 'jours/an'],
    ['strong_wind_days_per_year', count('wind_gusts_10m_max', (v) => v >= 80), 'jours/an'],
    ['sunshine_hours_per_year', sum('sunshine_duration') / 3600, 'h/an'],
    ['winter_sunshine_hours', sum('sunshine_duration', winter) / 3600, 'h/hiver'],
    ['precipitation_per_year', sum('precipitation_sum'), 'mm/an'],
  ];
  return items.map(([indicator, value, unit]) => ({ indicator, valueNum: round1(value), unit, details: meta }));
}

/** Indicateurs par modèle sur une période (moyennes annuelles). */
export function projectionIndicators(daily: Record<string, Array<number | null>>, model: string) {
  const days = daily.time as unknown as string[];
  const tmax = daily[`temperature_2m_max_${model}`] ?? [];
  const tmin = daily[`temperature_2m_min_${model}`] ?? [];
  const prcp = daily[`precipitation_sum_${model}`] ?? [];
  const validYears = new Set(days.filter((_, i) => tmax[i] !== null && tmax[i] !== undefined).map((d) => d.slice(0, 4))).size;
  if (validYears === 0) return [];
  const per = (arr: Array<number | null>, pred: (v: number) => boolean) => arr.filter((v) => v !== null && pred(v)).length / validYears;
  const mean = (arr: Array<number | null>) => {
    const vals = arr.filter((v): v is number => v !== null);
    return vals.reduce((a, b) => a + b, 0) / (vals.length || 1);
  };
  return [
    { indicator: 'mean_tmax', value: round1(mean(tmax)), unit: '°C' },
    { indicator: 'hot_days_per_year', value: round1(per(tmax, (v) => v >= 30)), unit: 'jours/an' },
    { indicator: 'tropical_nights_per_year', value: round1(per(tmin, (v) => v >= 20)), unit: 'nuits/an' },
    { indicator: 'frost_days_per_year', value: round1(per(tmin, (v) => v < 0)), unit: 'jours/an' },
    { indicator: 'precipitation_per_year', value: round1(prcp.reduce<number>((a, v) => a + (v ?? 0), 0) / validYears), unit: 'mm/an' },
  ];
}
