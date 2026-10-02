import { geoJsonToWkt, LatLon, pointInGeometry, pointWkt, distanceToGeometryMeters } from '../../common/geo/geo.utils';
import { int, isoDate, num, str } from '../../common/utils/parse';
import { Stamp } from '../../sources/collector.service';
import { BanFeature } from './geo.clients';
import {
  AddressEntity,
  CommuneEntity,
  MonumentEntity,
  ParcelEntity,
  PluPrescriptionEntity,
  PluZoneEntity,
  PublicEasementEntity,
} from './geo.entities';

/** Transformation des réponses brutes en lignes de la base (fonctions pures, testables). */

export function normalizeBanFeature(f: BanFeature, stamp: Stamp): Partial<AddressEntity> {
  const [lon, lat] = f.geometry.coordinates;
  const p = f.properties;
  return {
    banId: p.id,
    label: p.label,
    housenumber: str(p.housenumber, 16),
    street: str(p.street ?? (p.type === 'street' ? p.name : null), 160),
    postcode: str(p.postcode, 5),
    city: str(p.city, 120),
    inseeCode: p.citycode,
    latitude: lat,
    longitude: lon,
    location: pointWkt(lon, lat),
    geocodeScore: num(p.score),
    geocodeType: p.type,
    ...stamp,
  };
}

export function normalizeCommune(c: any, stamp: Stamp): Partial<CommuneEntity> {
  const [lon, lat] = c.centre?.coordinates ?? [0, 0];
  return {
    inseeCode: c.code,
    name: c.nom,
    departmentCode: c.codeDepartement,
    departmentName: c.departement?.nom ?? null,
    regionCode: c.codeRegion ?? null,
    regionName: c.region?.nom ?? null,
    epciCode: c.codeEpci ?? null,
    postalCodes: c.codesPostaux ?? [],
    population: int(c.population),
    surfaceHa: num(c.surface),
    latitude: lat,
    longitude: lon,
    center: pointWkt(lon, lat),
    ...stamp,
  };
}

export function normalizeParcel(f: any, stamp: Stamp): Partial<ParcelEntity> {
  const p = f.properties;
  return {
    idu: p.idu,
    inseeCode: p.code_insee ?? `${p.code_dep}${p.code_com}`,
    prefix: p.com_abs ?? '000',
    section: p.section,
    numero: p.numero,
    sheet: int(p.feuille),
    areaM2: int(p.contenance),
    geom: geoJsonToWkt(f.geometry),
    ...stamp,
  };
}

/** Parcelle contenant le point, à défaut la plus proche. */
export function pickParcel(features: any[], p: LatLon): any | null {
  if (features.length === 0) return null;
  const containing = features.find((f) => pointInGeometry(p, f.geometry));
  if (containing) return containing;
  return [...features].sort((a, b) => distanceToGeometryMeters(p, a.geometry) - distanceToGeometryMeters(p, b.geometry))[0];
}

/** « DU_80021 » -> « 80021 » (les PLUi ont un SIREN d'EPCI : on garde alors la commune de l'adresse). */
function inseeFromPartition(partition: string | undefined, fallback: string | null): string | null {
  const m = partition?.match(/^DU_(\d{5}|2[AB]\d{3})$/);
  return m ? m[1] : fallback;
}

const yyyymmdd = (v: unknown) => {
  const s = str(v);
  return s && /^\d{8}$/.test(s) ? `${s.slice(0, 4)}-${s.slice(4, 6)}-${s.slice(6, 8)}` : isoDate(s);
};

export function normalizePluZone(f: any, fallbackInsee: string | null, stamp: Stamp): Partial<PluZoneEntity> {
  const p = f.properties;
  return {
    gpuId: String(f.id ?? `zone_urba.${p.gid}`),
    inseeCode: inseeFromPartition(p.partition, fallbackInsee),
    documentId: str(p.idurba, 64),
    label: str(p.libelle, 64),
    labelLong: str(p.libelong, 255),
    zoneType: str(p.typezone, 8),
    approvedAt: yyyymmdd(p.datappro ?? p.datvalid),
    regulationFile: str(p.urlfic || p.nomfic, 255),
    geom: geoJsonToWkt(f.geometry),
    ...stamp,
  };
}

const KIND: Record<string, 'surface' | 'line' | 'point'> = {
  'prescription-surf': 'surface',
  'prescription-lin': 'line',
  'prescription-pct': 'point',
};

export function normalizePrescription(f: any, layer: string, fallbackInsee: string | null, stamp: Stamp): Partial<PluPrescriptionEntity> {
  const p = f.properties;
  return {
    gpuId: String(f.id ?? `${layer}.${p.gid}`),
    inseeCode: inseeFromPartition(p.partition, fallbackInsee),
    documentId: str(p.idurba, 64),
    geometryKind: KIND[layer],
    typeCode: str(p.typepsc, 4),
    subtypeCode: str(p.stypepsc, 4),
    label: str(p.libelle, 255),
    nature: str(p.nature ?? p.txt, 255),
    geom: geoJsonToWkt(f.geometry),
    ...stamp,
  };
}

/** Certains libellés GPU arrivent doublement encodés (UTF-8 lu en Latin-1). */
export function fixMojibake(s: string | null): string | null {
  if (!s || !/[ÃÂ]/.test(s)) return s;
  try {
    const fixed = Buffer.from(s, 'latin1').toString('utf8');
    return fixed.includes('�') ? s : fixed;
  } catch {
    return s;
  }
}

export function normalizeEasement(f: any, stamp: Stamp): Partial<PublicEasementEntity> {
  const p = f.properties;
  return {
    gpuId: String(f.id ?? `assiette_sup_s.${p.gid}`),
    supType: String(p.suptype ?? '').toLowerCase().slice(0, 8),
    name: fixMojibake(str(p.nomsuplitt ?? p.nomass, 255)),
    assietteType: str(p.typeass, 120),
    generatorId: str(p.idgen, 120),
    geom: geoJsonToWkt(f.geometry),
    ...stamp,
  };
}

export function normalizeMonument(r: any, stamp: Stamp): Partial<MonumentEntity> | null {
  if (!r.Reference) return null;
  const [lat, lon] = String(r.coordonnees_au_format_WGS84 ?? '')
    .split(',')
    .map((x) => num(x));
  return {
    reference: r.Reference,
    name: str(r.Titre_editorial_de_la_notice ?? r.Denomination_de_l_edifice, 255),
    inseeCode: r.COG_Insee_lors_de_la_protection,
    denomination: str(r.Denomination_de_l_edifice, 255),
    protectionType: str(r.Typologie_de_la_protection, 120),
    protectionText: str(r.Precision_de_la_protection ?? r.Date_et_typologie_de_la_protection, 1000),
    latitude: lat ?? null,
    longitude: lon ?? null,
    ...stamp,
  };
}
