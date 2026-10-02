import { Injectable } from '@nestjs/common';
import { InjectRepository } from '@nestjs/typeorm';
import { Repository } from 'typeorm';
import { LatLon } from '../../common/geo/geo.utils';
import { int, num, str } from '../../common/utils/parse';
import { CollectOutcome, CollectorService } from '../../sources/collector.service';
import { AddressEntity } from '../geo/geo.entities';
import { GeoService } from '../geo/geo.service';
import { AtmoClient, CLIMATE_MODELS, OpenMeteoClient, PvgisClient } from './climate.clients';
import { AirQualityIndexEntity, ClimateProjectionEntity, SolarPotentialEntity } from './climate.entities';
import { climateIndicators, projectionIndicators } from './climate.normalizers';

/** Période de référence modélisée vs horizon 2050 (l'API s'arrête au 31/12/2050). */
const PERIODS = [
  { key: '2005-2014', start: '2005-01-01', end: '2014-12-31' },
  { key: '2041-2050', start: '2041-01-01', end: '2050-12-31' },
];

@Injectable()
export class ClimateService {
  constructor(
    private readonly collector: CollectorService,
    private readonly geo: GeoService,
    private readonly openMeteo: OpenMeteoClient,
    private readonly pvgis: PvgisClient,
    private readonly atmo: AtmoClient,
    @InjectRepository(ClimateProjectionEntity) private readonly projections: Repository<ClimateProjectionEntity>,
    @InjectRepository(SolarPotentialEntity) private readonly solar: Repository<SolarPotentialEntity>,
    @InjectRepository(AirQualityIndexEntity) private readonly air: Repository<AirQualityIndexEntity>,
  ) {}

  async collect(address: AddressEntity, force = false): Promise<CollectOutcome[]> {
    const p: LatLon = { lat: address.latitude, lon: address.longitude };
    const target = `address:${address.id}`;

    const history = this.collector.run('open_meteo_archive', target, { force }, async (stamp) => {
      const lastYear = new Date().getFullYear() - 1;
      const res: any = await this.openMeteo.archive(p, `${lastYear - 9}-01-01`, `${lastYear}-12-31`);
      const meta = { period: `${lastYear - 9}-${lastYear}`, gridLat: res.latitude, gridLon: res.longitude, elevation: res.elevation };
      const items = climateIndicators(res.daily, meta);
      await this.geo.upsertIndicators(address.id, 'climate', items, stamp);
      return { items: items.length, raw: { meta, units: res.daily_units } };
    });

    const projection = this.collector.run('open_meteo_climate', target, { force }, async (stamp) => {
      const rows: Partial<ClimateProjectionEntity>[] = [];
      for (const period of PERIODS) {
        const res: any = await this.openMeteo.climate(p, period.start, period.end);
        for (const model of CLIMATE_MODELS) {
          for (const i of projectionIndicators(res.daily, model)) {
            rows.push({ addressId: address.id, model, period: period.key, indicator: i.indicator, value: i.value, unit: i.unit, ...stamp });
          }
        }
      }
      if (rows.length) await this.projections.upsert(rows, ['addressId', 'model', 'period', 'indicator']);
      return { items: rows.length };
    });

    const solar = this.collector.run('pvgis', target, { force }, async (stamp) => {
      const res: any = await this.pvgis.pvcalc(p);
      const fixed = res.inputs?.mounting_system?.fixed;
      const monthly = (res.outputs?.monthly?.fixed ?? []).map((m: any) => ({ month: m.month, kwh: m.E_m, irradiation: m['H(i)_m'] }));
      const winter = monthly.filter((m: any) => [12, 1, 2].includes(m.month)).reduce((s: number, m: any) => s + m.kwh, 0);
      await this.solar.upsert(
        {
          addressId: address.id,
          tiltDeg: int(fixed?.slope?.value) ?? 35,
          azimuthDeg: int(fixed?.azimuth?.value) ?? 0,
          yearlyKwhPerKwp: num(res.outputs?.totals?.fixed?.E_y),
          yearlyIrradiationKwhM2: num(res.outputs?.totals?.fixed?.['H(i)_y']),
          winterKwhPerKwp: Math.round(winter * 100) / 100,
          monthly,
          ...stamp,
        },
        ['addressId', 'tiltDeg', 'azimuthDeg'],
      );
      return { items: 1, raw: res.outputs?.totals };
    });

    const air = this.collector.run('atmo', `commune:${address.inseeCode}`, { force }, async (stamp) => {
      const today = new Date().toISOString().slice(0, 10);
      const rows: Partial<AirQualityIndexEntity>[] = [];
      for (const kind of ['atmo', 'pollens'] as const) {
        for (const f of await this.atmo.indices(kind, address.inseeCode, today)) {
          const pr = f.properties ?? {};
          rows.push({
            inseeCode: address.inseeCode,
            indexType: kind === 'atmo' ? 'atmo' : 'pollen',
            indexDate: String(pr.date_ech ?? today).slice(0, 10),
            levelCode: int(pr.code_qual),
            levelLabel: str(pr.lib_qual, 48),
            responsible: str(pr.pollen_resp ?? null, 120),
            details: pr,
            ...stamp,
          });
        }
      }
      if (rows.length) await this.air.upsert(rows, ['inseeCode', 'indexType', 'indexDate']);
      return { items: rows.length };
    });

    return Promise.all([history, projection, solar, air]);
  }

  async read(address: AddressEntity) {
    const [indicators, projections, solar, air] = await Promise.all([
      this.geo.indicatorsOf(address.id, 'climate'),
      this.projections.find({ where: { addressId: address.id } }),
      this.solar.find({ where: { addressId: address.id } }),
      this.air.find({ where: { inseeCode: address.inseeCode }, order: { indexDate: 'DESC' }, take: 14 }),
    ]);

    // Moyenne multi-modèles et écart futur - passé pour chaque indicateur.
    const ensemble: Record<string, Record<string, number | null>> = {};
    for (const indicator of [...new Set(projections.map((p) => p.indicator))]) {
      ensemble[indicator] = {};
      for (const period of PERIODS.map((p) => p.key)) {
        const vals = projections.filter((p) => p.indicator === indicator && p.period === period && p.value !== null).map((p) => p.value!);
        ensemble[indicator][period] = vals.length ? Math.round((vals.reduce((a, b) => a + b, 0) / vals.length) * 10) / 10 : null;
      }
      const [past, future] = PERIODS.map((p) => ensemble[indicator][p.key]);
      ensemble[indicator].change = past !== null && future !== null ? Math.round((future - past) * 10) / 10 : null;
    }

    return {
      observed: Object.fromEntries(indicators.map((i) => [i.indicator, { value: i.valueNum, unit: i.unit }])),
      observedMeta: indicators[0]?.details ?? null,
      projections2050: { models: CLIMATE_MODELS, ensemble, perModel: projections },
      solar: solar[0] ?? null,
      airQuality: air.filter((a) => a.indexType === 'atmo'),
      pollens: air.filter((a) => a.indexType === 'pollen'),
      caveats: [
        'Réanalyse ERA5 (maille ~10 km) : l’îlot de chaleur urbain et les effets de relief local sont lissés.',
        'sunshine_duration ERA5 surestime nettement l’ensoleillement mesuré par héliographe : à utiliser en comparaison entre adresses, pas en valeur absolue.',
      ],
      notCovered: ['Brouillard (pas de climatologie ouverte à l’adresse)', 'Masques solaires dus aux bâtiments voisins'],
    };
  }
}
