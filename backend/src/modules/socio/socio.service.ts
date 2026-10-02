import { Injectable } from '@nestjs/common';
import { InjectRepository } from '@nestjs/typeorm';
import { Repository } from 'typeorm';
import { chunk } from '../../common/utils/parse';
import { CollectOutcome, CollectorService } from '../../sources/collector.service';
import { GeoService } from '../geo/geo.service';
import { FiscaliteClient, MelodiClient, SsmsiClient } from './socio.clients';
import { CrimeStatEntity, LocalTaxRateEntity, SocioIndicatorEntity } from './socio.entities';
import { housingIndicators, normalizeCrime, normalizeTax, populationIndicators } from './socio.normalizers';

const LOGEMENT_TOTALS = { BUILD_END: '_T', TDW: '_T', CARS: '_T', NRG_SRC: '_T', TSH: '_T', CARPARK: '_T', NOR: '_T' };

/** Indicateurs SSMSI mis en avant dans la synthèse. */
const KEY_CRIME_INDICATORS = [/cambriolages/i, /vols? (sans violence|avec violence)/i, /violences physiques/i, /destructions/i];

@Injectable()
export class SocioService {
  constructor(
    private readonly collector: CollectorService,
    private readonly geo: GeoService,
    private readonly melodi: MelodiClient,
    private readonly fiscalite: FiscaliteClient,
    private readonly ssmsi: SsmsiClient,
    @InjectRepository(SocioIndicatorEntity) private readonly indicators: Repository<SocioIndicatorEntity>,
    @InjectRepository(CrimeStatEntity) private readonly crimes: Repository<CrimeStatEntity>,
    @InjectRepository(LocalTaxRateEntity) private readonly taxes: Repository<LocalTaxRateEntity>,
  ) {}

  async collect(insee: string, force = false): Promise<CollectOutcome[]> {
    await this.geo.ensureCommune(insee);
    const geoFilter = `COM-${insee}`;

    const census = this.collector.run('insee_melodi', `commune:${insee}`, { force }, async (stamp) => {
      const population = await this.melodi.observations('DS_RP_POPULATION_PRINC', { GEO: geoFilter, SEX: '_T' });
      const occupancy = await this.melodi.observations('DS_RP_LOGEMENT_PRINC', { GEO: geoFilter, ...LOGEMENT_TOTALS, L_STAY: '_T', RP_MEASURE: 'DWELLINGS' });
      const stay = await this.melodi.observations('DS_RP_LOGEMENT_PRINC', { GEO: geoFilter, ...LOGEMENT_TOTALS, OCS: 'DW_MAIN' });
      const rows = [...populationIndicators(population, insee, stamp), ...housingIndicators(occupancy, stay, insee, stamp)];
      for (const c of chunk(rows, 200)) await this.indicators.upsert(c, ['inseeCode', 'indicator', 'year']);
      return { items: rows.length };
    });

    const tax = this.collector.run('fiscalite_locale', `commune:${insee}`, { force }, async (stamp) => {
      const rows = (await this.fiscalite.byCommune(insee)).map((r) => normalizeTax(r, stamp)).filter((r): r is Partial<LocalTaxRateEntity> => r !== null);
      if (rows.length) await this.taxes.upsert(rows, ['inseeCode', 'year']);
      return { items: rows.length };
    });

    const crime = this.collector.run('ssmsi', `commune:${insee}`, { force }, async (stamp) => {
      const rows = (await this.ssmsi.byCommune(insee)).map((r) => normalizeCrime(r, insee, stamp)).filter((r): r is Partial<CrimeStatEntity> => r !== null);
      for (const c of chunk(rows, 200)) await this.crimes.upsert(c, ['inseeCode', 'year', 'indicator']);
      return { items: rows.length };
    });

    return Promise.all([census, tax, crime]);
  }

  async read(insee: string) {
    const [indicators, taxes, crimes] = await Promise.all([
      this.indicators.find({ where: { inseeCode: insee }, order: { indicator: 'ASC', year: 'ASC' } }),
      this.taxes.find({ where: { inseeCode: insee }, order: { year: 'ASC' } }),
      this.crimes.find({ where: { inseeCode: insee }, order: { year: 'ASC' } }),
    ]);

    const series: Record<string, Array<{ year: number; value: number | null; unit: string | null }>> = {};
    for (const i of indicators) (series[i.indicator] ??= []).push({ year: i.year, value: i.value, unit: i.unit });
    const latest = Object.fromEntries(Object.entries(series).map(([k, v]) => [k, v[v.length - 1]]));

    const first = taxes[0];
    const last = taxes[taxes.length - 1];
    const lastCrimeYear = crimes.length ? Math.max(...crimes.map((c) => c.year)) : null;

    return {
      demography: { latest, series },
      taxes: {
        history: taxes,
        propertyTaxRateChange: first && last && first.propertyTaxRate !== null && last.propertyTaxRate !== null
          ? { from: first.year, to: last.year, points: Math.round((last.propertyTaxRate - first.propertyTaxRate) * 100) / 100 }
          : null,
      },
      crime: {
        year: lastCrimeYear,
        highlights: crimes.filter((c) => c.year === lastCrimeYear && KEY_CRIME_INDICATORS.some((r) => r.test(c.indicator))),
        all: crimes,
      },
      notCovered: ['Part de locations Airbnb (pas de donnée officielle)', 'Vie associative (fichier RNA non interrogeable par API)'],
    };
  }
}
