import { climateIndicators, projectionIndicators } from './climate.normalizers';

describe('climateIndicators', () => {
  it('calcule des moyennes annuelles', () => {
    const daily: any = {
      time: ['2023-01-01', '2023-07-01', '2024-01-01', '2024-07-01'],
      temperature_2m_min: [-3, 21, -6, 15],
      temperature_2m_max: [2, 32, 1, 28],
      snowfall_sum: [2, 0, 0, 0],
      wind_gusts_10m_max: [90, 20, 30, 40],
      sunshine_duration: [3600, 36000, 7200, 36000],
      precipitation_sum: [10, 0, 5, 1],
    };
    const byKey = Object.fromEntries(climateIndicators(daily, {}).map((i) => [i.indicator, i.valueNum]));
    expect(byKey.frost_days_per_year).toBe(1);
    expect(byKey.severe_frost_days_per_year).toBe(0.5);
    expect(byKey.tropical_nights_per_year).toBe(0.5);
    expect(byKey.hot_days_per_year).toBe(0.5);
    expect(byKey.strong_wind_days_per_year).toBe(0.5);
    expect(byKey.winter_sunshine_hours).toBe(1.5);
    expect(byKey.precipitation_per_year).toBe(8);
  });
});

describe('projectionIndicators', () => {
  it('ignore un modèle sans données', () => {
    const daily: any = { time: ['2050-01-01'], temperature_2m_max_A: [null], temperature_2m_min_A: [null], precipitation_sum_A: [null] };
    expect(projectionIndicators(daily, 'A')).toEqual([]);
  });
});
