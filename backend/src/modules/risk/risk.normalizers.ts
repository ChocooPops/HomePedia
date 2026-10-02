import { pointWkt } from '../../common/geo/geo.utils';
import { int, isoDate, num, str } from '../../common/utils/parse';
import { Stamp } from '../../sources/collector.service';
import { CatnatDecreeEntity, CommuneRiskProfileEntity, RiskAssessmentEntity, RiskSiteEntity, RiskSiteType } from './risk.entities';

export function normalizeReport(report: any, addressId: number, stamp: Stamp): Partial<RiskAssessmentEntity>[] {
  const out: Partial<RiskAssessmentEntity>[] = [];
  const groups: Array<[string, 'natural' | 'technological']> = [
    ['risquesNaturels', 'natural'],
    ['risquesTechnologiques', 'technological'],
  ];
  for (const [key, category] of groups) {
    for (const [hazardCode, r] of Object.entries<any>(report?.[key] ?? {})) {
      out.push({
        addressId,
        hazardCode,
        category,
        label: r.libelle ?? hazardCode,
        present: Boolean(r.present),
        communeStatus: str(r.libelleStatutCommune, 80),
        addressStatus: str(r.libelleStatutAdresse, 80),
        details: r.specifique ?? null,
        ...stamp,
      });
    }
  }
  return out;
}

export function normalizeCommuneProfile(
  insee: string,
  radon: any,
  seismic: any,
  risks: any,
  azi: any[],
  stamp: Stamp,
): Partial<CommuneRiskProfileEntity> {
  return {
    inseeCode: insee,
    radonClass: int(radon?.classe_potentiel),
    seismicZone: str(seismic?.zone_sismicite, 32),
    knownRisks: (risks?.risques_detail ?? []).map((r: any) => r.libelle_risque_long),
    floodAtlases: azi.map((a) => ({ code: a.code_national_azi, label: a.libelle_azi, published: isoDate(a.date_diffusion) })),
    ...stamp,
  };
}

export function normalizeCatnat(r: any, stamp: Stamp): Partial<CatnatDecreeEntity> {
  return {
    codeNational: r.code_national_catnat,
    inseeCode: r.code_insee,
    hazardLabel: str(r.libelle_risque_jo, 160) ?? 'Inconnu',
    eventStart: isoDate(r.date_debut_evt),
    eventEnd: isoDate(r.date_fin_evt),
    decreeDate: isoDate(r.date_publication_arrete),
    journalDate: isoDate(r.date_publication_jo),
    ...stamp,
  };
}

function site(
  siteType: RiskSiteType,
  externalId: unknown,
  lat: number | null,
  lon: number | null,
  fields: Partial<RiskSiteEntity>,
  stamp: Stamp,
): Partial<RiskSiteEntity> | null {
  if (!externalId || lat === null || lon === null) return null;
  return {
    siteType,
    externalId: String(externalId).slice(0, 64),
    latitude: lat,
    longitude: lon,
    location: pointWkt(lon, lat),
    ...fields,
    ...stamp,
  };
}

/** Point représentatif d'une géométrie GeoJSON (centre de l'emprise). */
function representativePoint(geom: any): { lat: number; lon: number } | null {
  if (!geom) return null;
  if (geom.type === 'Point') return { lon: geom.coordinates[0], lat: geom.coordinates[1] };
  const coords: number[][] = JSON.stringify(geom.coordinates)
    .match(/-?\d+(\.\d+)?,-?\d+(\.\d+)?/g)!
    .map((pair) => pair.split(',').map(Number));
  const lons = coords.map((c) => c[0]);
  const lats = coords.map((c) => c[1]);
  return { lon: (Math.min(...lons) + Math.max(...lons)) / 2, lat: (Math.min(...lats) + Math.max(...lats)) / 2 };
}

export function normalizeCavity(r: any, stamp: Stamp) {
  return site('cavity', r.identifiant, num(r.latitude), num(r.longitude), {
    name: str(r.nom, 255), subtype: str(r.type, 120), inseeCode: str(r.code_insee, 5),
  }, stamp);
}

export function normalizeGroundMovement(r: any, stamp: Stamp) {
  return site('ground_movement', r.identifiant, num(r.latitude), num(r.longitude), {
    name: str(r.lieu, 255), subtype: str(r.type, 120), inseeCode: str(r.code_insee, 5),
    details: { date: r.date_debut, reliability: r.fiabilite, comment: r.commentaire_mvt },
  }, stamp);
}

export function normalizePollutedSoils(res: any, stamp: Stamp): Array<Partial<RiskSiteEntity> | null> {
  const out: Array<Partial<RiskSiteEntity> | null> = [];
  for (const [base, block] of Object.entries<any>(res ?? {})) {
    for (const r of block?.data ?? []) {
      const p = representativePoint(r.geom);
      out.push(site(base === 'casias' ? 'casias' : 'ssp', r.identifiant_ssp ?? r.identifiant_casias, p?.lat ?? null, p?.lon ?? null, {
        name: str(r.nom_etablissement ?? r.adresse, 255),
        subtype: str(r.activite_principale ?? base, 120),
        status: str(r.statut, 80),
        inseeCode: str(r.code_insee, 5),
        details: { address: r.adresse, sheet: r.fiche_risque },
      }, stamp));
    }
  }
  return out;
}

export function normalizeInstallation(r: any, stamp: Stamp) {
  const activities = ['bovins', 'porcs', 'volailles', 'carriere', 'eolienne', 'industrie'].filter((k) => r[k]);
  return site('icpe', r.codeAIOT, num(r.latitude), num(r.longitude), {
    name: str(r.raisonSociale, 255),
    inseeCode: str(r.codeInsee, 5),
    status: str(r.etatActivite ?? r.regime, 80),
    sevesoStatus: str(r.statutSeveso, 48),
    subtype: activities.join(',') || str(r.codeNaf, 120),
    details: { regime: r.regime, naf: r.codeNaf, siret: r.siret, ied: r.ied, priority: r.prioriteNationale },
  }, stamp);
}
