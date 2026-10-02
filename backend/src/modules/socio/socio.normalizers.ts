import { boolFromFlag, int, num, str } from '../../common/utils/parse';
import { Stamp } from '../../sources/collector.service';
import { CrimeStatEntity, LocalTaxRateEntity, SocioIndicatorEntity } from './socio.entities';

type Indicator = Partial<SocioIndicatorEntity>;
const round = (v: number, d = 2) => Math.round(v * 10 ** d) / 10 ** d;
const value = (o: any) => num(o?.measures?.OBS_VALUE_NIVEAU?.value);

/** Tranches d'âge disjointes du recensement et leur âge médian, pour estimer l'âge moyen. */
const AGE_BRACKETS: Record<string, number> = { Y_LT15: 7.5, Y15T24: 19.5, Y25T39: 32, Y40T54: 47, Y55T64: 59.5, Y65T79: 72, Y_GE80: 86 };

export function populationIndicators(obs: any[], insee: string, stamp: Stamp): Indicator[] {
  const out: Indicator[] = [];
  const years = [...new Set(obs.map((o) => o.dimensions.TIME_PERIOD))];
  for (const y of years) {
    const rows = obs.filter((o) => o.dimensions.TIME_PERIOD === y && o.dimensions.SEX === '_T');
    const get = (age: string) => value(rows.find((o) => o.dimensions.AGE === age));
    const total = get('_T');
    if (!total) continue;
    const year = Number(y);
    out.push({ inseeCode: insee, indicator: 'population', year, value: Math.round(total), unit: 'habitants', ...stamp });
    const brackets = Object.entries(AGE_BRACKETS).map(([k, mid]) => [get(k) ?? 0, mid]);
    const covered = brackets.reduce((s, [n]) => s + n, 0);
    if (covered > 0) {
      out.push({ inseeCode: insee, indicator: 'mean_age_estimated', year, value: round(brackets.reduce((s, [n, m]) => s + n * m, 0) / covered, 1), unit: 'ans', ...stamp });
    }
    const over65 = get('Y_GE65');
    if (over65 !== null) out.push({ inseeCode: insee, indicator: 'share_65_plus', year, value: round((over65 / total) * 100), unit: '%', ...stamp });
    const under20 = get('Y_LT20');
    if (under20 !== null) out.push({ inseeCode: insee, indicator: 'share_under_20', year, value: round((under20 / total) * 100), unit: '%', ...stamp });
  }
  return out;
}

export function housingIndicators(occupancy: any[], stay: any[], insee: string, stamp: Stamp): Indicator[] {
  const out: Indicator[] = [];
  for (const y of [...new Set(occupancy.map((o) => o.dimensions.TIME_PERIOD))]) {
    const rows = occupancy.filter((o) => o.dimensions.TIME_PERIOD === y);
    const get = (ocs: string) => value(rows.find((o) => o.dimensions.OCS === ocs));
    const total = get('_T');
    if (!total) continue;
    const year = Number(y);
    const secondary = get('DW_SEC_DW_OCC');
    const vacant = get('DW_VAC');
    out.push({ inseeCode: insee, indicator: 'dwellings_total', year, value: Math.round(total), unit: 'logements', ...stamp });
    if (secondary !== null) {
      out.push({ inseeCode: insee, indicator: 'secondary_homes', year, value: Math.round(secondary), unit: 'logements', ...stamp });
      out.push({ inseeCode: insee, indicator: 'share_secondary_homes', year, value: round((secondary / total) * 100), unit: '%', ...stamp });
    }
    if (vacant !== null) {
      out.push({ inseeCode: insee, indicator: 'vacant_dwellings', year, value: Math.round(vacant), unit: 'logements', ...stamp });
      out.push({ inseeCode: insee, indicator: 'share_vacant_dwellings', year, value: round((vacant / total) * 100), unit: '%', ...stamp });
    }
  }

  for (const y of [...new Set(stay.map((o) => o.dimensions.TIME_PERIOD))]) {
    const rows = stay.filter((o) => o.dimensions.TIME_PERIOD === y);
    const get = (measure: string, lstay: string) => value(rows.find((o) => o.dimensions.RP_MEASURE === measure && o.dimensions.L_STAY === lstay));
    const dwellings = get('DWELLINGS', '_T');
    const years = get('DWELLING_L_STAY', '_T');
    const recent = get('DWELLINGS', 'Y_LT2');
    if (!dwellings) continue;
    const year = Number(y);
    if (years !== null) out.push({ inseeCode: insee, indicator: 'mean_length_of_stay', year, value: round(years / dwellings, 1), unit: 'ans', ...stamp });
    if (recent !== null) out.push({ inseeCode: insee, indicator: 'share_moved_in_last_2_years', year, value: round((recent / dwellings) * 100), unit: '%', ...stamp });
  }
  return out;
}

export function normalizeTax(r: any, stamp: Stamp): Partial<LocalTaxRateEntity> | null {
  const year = int(r.exercice);
  if (!year || !r.insee_com) return null;
  return {
    inseeCode: r.insee_com,
    year,
    epciCode: str(r.sirepci, 9),
    propertyTaxRate: num(r.taux_global_tfb),
    landTaxRate: num(r.taux_global_tfnb),
    wasteTaxRate: num(r.taux_plein_teom),
    housingTaxRate: num(r.taux_global_th),
    secondaryHomeSurcharge: boolFromFlag(r.ind_majothrs),
    secondaryHomeSurchargeRate: num(r.thsurtaxrstau),
    ...stamp,
  };
}

export function normalizeCrime(r: any, insee: string, stamp: Stamp): Partial<CrimeStatEntity> | null {
  const year = int(r.annee);
  if (!year || !r.indicateur) return null;
  return {
    inseeCode: insee,
    year,
    indicator: str(r.indicateur, 128)!,
    countUnit: str(r.unite_de_compte, 32),
    count: int(r.nombre),
    ratePerThousand: num(r.taux_pour_mille),
    isPublished: r.est_diffuse === 'diff',
    ...stamp,
  };
}
