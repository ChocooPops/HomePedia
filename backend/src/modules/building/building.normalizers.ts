import { createHash } from 'crypto';
import { geoJsonToWkt, pointWkt } from '../../common/geo/geo.utils';
import { boolFromFlag, int, isoDate, num, quantile, str } from '../../common/utils/parse';
import { Stamp } from '../../sources/collector.service';
import { BuildingEntity, CondominiumEntity, DpeCertificateEntity, DvfMutationEntity, PriceIndexEntity } from './building.entities';

export function normalizeRnb(b: any, insee: string | null, stamp: Stamp): Partial<BuildingEntity> {
  const [lon, lat] = b.point.coordinates;
  return {
    rnbId: b.rnb_id,
    status: str(b.status, 24),
    inseeCode: b.addresses?.[0]?.city_insee_code ?? insee,
    latitude: lat,
    longitude: lon,
    location: pointWkt(lon, lat),
    shape: b.shape ? geoJsonToWkt(b.shape) : null,
    ...stamp,
  };
}

/** Enrichissement BDNB (champs descriptifs du groupe de bâtiments). */
export function normalizeBdnb(g: any): Partial<BuildingEntity> {
  return {
    bdnbGroupId: g.batiment_groupe_id,
    inseeCode: g.code_commune_insee ?? undefined,
    constructionYear: int(g.annee_construction),
    heightM: num(g.hauteur_mean),
    levels: int(g.nb_niveau),
    dwellings: int(g.nb_log),
    wallMaterial: str(g.mat_mur_txt, 80),
    roofMaterial: str(g.mat_toit_txt, 80),
    mainUsage: str(g.usage_niveau_1_txt, 80),
    dpeClassBdnb: str(g.classe_bilan_dpe, 1),
    condoRegistration: str(g.numero_immat_principal, 16),
    irisCode: str(g.code_iris, 9),
    footprintM2: int(g.surface_emprise_sol),
    groundAltitudeM: num(g.altitude_sol_mean),
  };
}

export function normalizeDpe(d: any, stamp: Stamp): Partial<DpeCertificateEntity> {
  const [lat, lon] = String(d._geopoint ?? '').split(',').map((x) => num(x));
  return {
    numeroDpe: d.numero_dpe,
    rnbId: str(d.id_rnb, 12),
    banId: str(d.identifiant_ban, 64),
    addressLabel: str(d.adresse_ban, 255),
    inseeCode: str(d.code_insee_ban, 5),
    issuedAt: isoDate(d.date_etablissement_dpe),
    energyClass: str(d.etiquette_dpe, 1),
    ghgClass: str(d.etiquette_ges, 1),
    energyKwhM2: num(d.conso_5_usages_par_m2_ep),
    ghgKgM2: num(d.emission_ges_5_usages_par_m2),
    constructionYear: int(d.annee_construction),
    constructionPeriod: str(d.periode_construction, 24),
    buildingType: str(d.type_batiment, 24),
    livingAreaM2: num(d.surface_habitable_logement),
    ceilingHeightM: num(d.hauteur_sous_plafond),
    heatingEnergy: str(d.type_energie_principale_chauffage, 80),
    annualCostEur: num(d.cout_total_5_usages),
    latitude: lat ?? null,
    longitude: lon ?? null,
    ...stamp,
  };
}

export function normalizeDvfRow(r: Record<string, string>, stamp: Stamp): Partial<DvfMutationEntity> | null {
  if (!r.id_mutation || !r.date_mutation || !r.code_commune) return null;
  const address = [r.adresse_numero, r.adresse_suffixe, r.adresse_nom_voie, r.code_postal, r.nom_commune].filter(Boolean).join(' ');
  return {
    // Une ligne DVF n'a pas d'identifiant propre : on hache son contenu pour dédoublonner les imports.
    rowHash: createHash('sha1').update(Object.values(r).join('|')).digest('hex'),
    mutationId: r.id_mutation,
    mutationDate: r.date_mutation,
    nature: r.nature_mutation,
    priceEur: num(r.valeur_fonciere),
    inseeCode: r.code_commune,
    parcelIdu: str(r.id_parcelle, 14),
    addressLabel: str(address, 255),
    propertyType: str(r.type_local, 48),
    builtAreaM2: int(r.surface_reelle_bati),
    rooms: int(r.nombre_pieces_principales),
    landAreaM2: int(r.surface_terrain),
    lotsCount: int(r.nombre_lots),
    latitude: num(r.latitude),
    longitude: num(r.longitude),
    ...stamp,
  };
}

export function normalizeRnic(r: any, stamp: Stamp): Partial<CondominiumEntity> {
  const refs = [1, 2, 3].map((i) => str(r[`reference_cadastrale_${i}`])).filter((x): x is string => !!x);
  return {
    registrationNumber: r.numero_d_immatriculation,
    name: str(r.nom_d_usage_de_la_copropriete, 255),
    addressLabel: str(r.adresse_de_reference, 255),
    inseeCode: str(r.code_officiel_commune ?? r.commune, 5),
    totalLots: int(r.nombre_total_de_lots),
    housingLots: int(r.nombre_de_lots_a_usage_d_habitation),
    parkingLots: int(r.nombre_de_lots_de_stationnement),
    syndicType: str(r.type_de_syndic_benevole_professionnel_non_connu, 32),
    syndicName: str(r.raison_sociale_du_representant_legal, 255),
    mandateStatus: str(r.mandat_en_cours_dans_la_copropriete, 64),
    mandateEndDate: isoDate(r.date_de_fin_du_dernier_mandat),
    constructionPeriod: str(r.periode_de_construction, 32),
    regulationDate: isoDate(r.date_du_reglement_de_copropriete),
    isAided: boolFromFlag(r.copro_aidee),
    priorityDistrict: str(r.nom_qp_2024, 120),
    cadastralRefs: refs,
    latitude: num(r.lat),
    longitude: num(r.long),
    ...stamp,
  };
}

/**
 * Prix au m² par commune / année / type, à partir des ventes « simples » :
 * une mutation de type Vente comportant exactement un local Maison ou Appartement.
 * Valeurs hors [200 ; 30 000] €/m² écartées (erreurs de saisie, ventes en bloc).
 */
export function computePriceIndex(rows: DvfMutationEntity[], computedAt = new Date()): PriceIndexEntity[] {
  const byMutation = new Map<string, DvfMutationEntity[]>();
  for (const r of rows) {
    if (r.nature !== 'Vente') continue;
    const list = byMutation.get(r.mutationId) ?? [];
    list.push(r);
    byMutation.set(r.mutationId, list);
  }

  const buckets = new Map<string, { insee: string; year: number; type: string; values: number[] }>();
  for (const lines of byMutation.values()) {
    const dwellings = lines.filter((l) => l.propertyType === 'Maison' || l.propertyType === 'Appartement');
    if (dwellings.length !== 1) continue;
    const d = dwellings[0];
    if (!d.priceEur || !d.builtAreaM2) continue;
    const m2 = d.priceEur / d.builtAreaM2;
    if (m2 < 200 || m2 > 30000) continue;
    const year = Number(String(d.mutationDate).slice(0, 4));
    for (const type of [d.propertyType!, 'Ensemble']) {
      const key = `${d.inseeCode}|${year}|${type}`;
      const b = buckets.get(key) ?? { insee: d.inseeCode, year, type, values: [] };
      b.values.push(m2);
      buckets.set(key, b);
    }
  }

  return [...buckets.values()].map((b) => {
    const sorted = b.values.sort((x, y) => x - y);
    const mean = sorted.reduce((s, v) => s + v, 0) / sorted.length;
    return Object.assign(new PriceIndexEntity(), {
      inseeCode: b.insee,
      year: b.year,
      propertyType: b.type,
      salesCount: sorted.length,
      medianPriceM2: round2(quantile(sorted, 0.5)),
      meanPriceM2: round2(mean),
      q1PriceM2: round2(quantile(sorted, 0.25)),
      q3PriceM2: round2(quantile(sorted, 0.75)),
      computedAt,
    });
  });
}

const round2 = (v: number | null) => (v === null ? null : Math.round(v * 100) / 100);

/** Calendrier légal d'interdiction de mise en location (loi Climat et résilience). */
export const RENTAL_BAN_DATES: Record<string, string> = { G: '2025-01-01', F: '2028-01-01', E: '2034-01-01' };

/** Présomptions réglementaires liées à l'année de construction (pas un diagnostic). */
export function buildingPresumptions(year: number | null, energyClass: string | null, now = new Date()) {
  const ban = energyClass ? RENTAL_BAN_DATES[energyClass] : undefined;
  return {
    leadRisk: year === null ? null : year < 1949,
    asbestosRisk: year === null ? null : year < 1997,
    rentalBanDate: ban ?? null,
    rentalBanned: ban ? new Date(ban) <= now : false,
    notes: [
      'Plomb : constat (CREP) obligatoire pour les logements construits avant le 01/01/1949.',
      'Amiante : repérage obligatoire si le permis de construire est antérieur au 01/07/1997.',
    ],
  };
}
