import { Injectable } from '@nestjs/common';
import { InjectRepository } from '@nestjs/typeorm';
import { In, Repository } from 'typeorm';
import { OverpassElement } from '../../common/clients/open-data.clients';
import { LatLon, pointWkt } from '../../common/geo/geo.utils';
import { entitiesWithDistance, withinRadius } from '../../common/geo/spatial-query';
import { boolFromFlag, chunk, int, num, str } from '../../common/utils/parse';
import { CollectOutcome, CollectorService, Stamp } from '../../sources/collector.service';
import { AddressEntity } from '../geo/geo.entities';
import { GeoService } from '../geo/geo.service';
import {
  EducationClient,
  IgnNavigationClient,
  KeyedHealthClients,
  NAF_CATEGORIES,
  RechercheEntreprisesClient,
  ServicesOverpassClient,
} from './services.clients';
import { SchoolEntity, ServicePlaceEntity, TravelTimeEntity } from './services.entities';

const SERVICES_RADIUS_M = 2000;
const EMERGENCY_RADIUS_M = 30000;
const SCHOOLS_RADIUS_M = 1500;

/** Destinations pour lesquelles on calcule un temps de trajet réel (réseau routier IGN). */
const TRAVEL_TARGETS: Array<{ kind: string; category: string; profiles: Array<'car' | 'pedestrian'>; radiusM: number }> = [
  { kind: 'nearest_general_practitioner', category: 'general_practitioner', profiles: ['car', 'pedestrian'], radiusM: SERVICES_RADIUS_M },
  { kind: 'nearest_pharmacy', category: 'pharmacy', profiles: ['car', 'pedestrian'], radiusM: SERVICES_RADIUS_M },
  { kind: 'nearest_emergency', category: 'emergency', profiles: ['car'], radiusM: EMERGENCY_RADIUS_M },
];

function osmCategory(t: Record<string, string>): string | null {
  if (t.emergency === 'yes' && (t.amenity === 'hospital' || t.healthcare === 'hospital')) return 'emergency';
  if (t.amenity === 'pharmacy') return 'pharmacy';
  if (t.amenity === 'childcare' || t.amenity === 'kindergarten') return 'childcare';
  if (t.shop === 'bakery') return 'bakery';
  return null;
}

/** Heuristique : horaires OSM mentionnant le dimanche (« Su ») hors « Su off ». */
export function opensOnSunday(hours: string | null | undefined): boolean | null {
  if (!hours) return null;
  if (/Su\s*(off|closed)/i.test(hours)) return false;
  return /\bSu\b|Mo-Su|24\/7/.test(hours);
}

function normalizeOsmService(e: OverpassElement, stamp: Stamp): Partial<ServicePlaceEntity> | null {
  const t = e.tags ?? {};
  const category = osmCategory(t);
  const lat = e.lat ?? e.center?.lat;
  const lon = e.lon ?? e.center?.lon;
  if (!category || lat === undefined || lon === undefined) return null;
  return {
    externalId: `osm:${e.type}/${e.id}`,
    category,
    name: str(t.name, 255),
    addressLabel: str([t['addr:housenumber'], t['addr:street'], t['addr:city']].filter(Boolean).join(' '), 255),
    openingHours: str(t.opening_hours, 255),
    details: { opensOnSunday: opensOnSunday(t.opening_hours), operator: t.operator ?? null },
    latitude: lat,
    longitude: lon,
    location: pointWkt(lon, lat),
    ...stamp,
  };
}

function normalizeEstablishment(e: any, stamp: Stamp): Partial<ServicePlaceEntity> | null {
  const lat = num(e.latitude);
  const lon = num(e.longitude);
  const category = NAF_CATEGORIES[e.activite_principale];
  if (e.etat_administratif !== 'A' || lat === null || lon === null || !category) return null;
  return {
    externalId: `siret:${e.siret}`,
    category,
    name: str(e.nom_commercial ?? e.liste_enseignes?.[0] ?? e.nom_complet, 255),
    addressLabel: str(e.adresse, 255),
    inseeCode: str(e.commune, 5),
    details: { siret: e.siret, naf: e.activite_principale, createdAt: e.date_creation },
    latitude: lat,
    longitude: lon,
    location: pointWkt(lon, lat),
    ...stamp,
  };
}

@Injectable()
export class ServicesService {
  constructor(
    private readonly collector: CollectorService,
    private readonly geo: GeoService,
    private readonly entreprises: RechercheEntreprisesClient,
    private readonly overpass: ServicesOverpassClient,
    private readonly education: EducationClient,
    private readonly navigation: IgnNavigationClient,
    private readonly keyed: KeyedHealthClients,
    @InjectRepository(ServicePlaceEntity) private readonly places: Repository<ServicePlaceEntity>,
    @InjectRepository(SchoolEntity) private readonly schools: Repository<SchoolEntity>,
    @InjectRepository(TravelTimeEntity) private readonly travel: Repository<TravelTimeEntity>,
  ) {}

  async collect(address: AddressEntity, force = false): Promise<CollectOutcome[]> {
    const p: LatLon = { lat: address.latitude, lon: address.longitude };
    const target = `address:${address.id}`;

    const companies = this.collector.run('recherche_entreprises', target, { force }, async (stamp) => {
      const raw = await this.entreprises.nearPoint(p, SERVICES_RADIUS_M / 1000, Object.keys(NAF_CATEGORIES));
      const rows = raw.map((e) => normalizeEstablishment(e, stamp)).filter((r): r is Partial<ServicePlaceEntity> => r !== null);
      for (const c of chunk(rows, 200)) await this.places.upsert(c, ['sourceCode', 'externalId', 'category']);
      return { items: rows.length };
    });

    const osm = this.collector.run('overpass', `${target}:services`, { force }, async (stamp) => {
      const raw = await this.overpass.around(p, SERVICES_RADIUS_M, EMERGENCY_RADIUS_M);
      const rows = raw.map((e) => normalizeOsmService(e, stamp)).filter((r): r is Partial<ServicePlaceEntity> => r !== null);
      for (const c of chunk(rows, 200)) await this.places.upsert(c, ['sourceCode', 'externalId', 'category']);
      return { items: rows.length };
    });

    const schools = this.collector.run('education', target, { force }, async (stamp) => {
      const raw = await this.education.schoolsAround(p, SCHOOLS_RADIUS_M);
      const uais = raw.map((r) => r.identifiant_de_l_etablissement);
      const [ipsSchools, ipsColleges, headcounts] = await Promise.all([
        this.education.ips('fr-en-ips-ecoles-ap2022', uais),
        this.education.ips('fr-en-ips-colleges-ap2023', uais),
        this.education.headcounts(uais),
      ]);
      const latest = <T extends Record<string, any>>(rows: T[], key: string) => {
        const m = new Map<string, T>();
        for (const r of rows) if (!m.has(r[key])) m.set(r[key], r); // trié par rentrée décroissante
        return m;
      };
      const ips = latest([...ipsSchools, ...ipsColleges], 'uai');
      const heads = latest(headcounts, 'numero_ecole');

      const rows: Partial<SchoolEntity>[] = raw
        .filter((r) => r.latitude && r.longitude)
        .map((r) => {
          const i = ips.get(r.identifiant_de_l_etablissement);
          const h = heads.get(r.identifiant_de_l_etablissement);
          const classes = int(h?.nombre_total_classes);
          const students = int(h?.nombre_total_eleves);
          return {
            uai: r.identifiant_de_l_etablissement,
            name: r.nom_etablissement,
            schoolType: str(r.type_etablissement, 48),
            natureLabel: str(r.libelle_nature, 120),
            sector: str(r.statut_public_prive, 16),
            inseeCode: str(r.code_commune, 5),
            hasPreschool: boolFromFlag(r.ecole_maternelle),
            hasElementary: boolFromFlag(r.ecole_elementaire),
            hasCanteen: boolFromFlag(r.restauration),
            priorityEducation: str(r.appartenance_education_prioritaire, 32),
            ips: num(i?.ips),
            ipsSchoolYear: str(i?.rentree_scolaire, 9),
            classesCount: classes,
            studentsCount: students,
            avgClassSize: classes && students ? Math.round((students / classes) * 10) / 10 : null,
            headcountYear: str(h?.rentree_scolaire, 9),
            latitude: r.latitude,
            longitude: r.longitude,
            location: pointWkt(r.longitude, r.latitude),
            ...stamp,
          };
        });
      for (const c of chunk(rows, 200)) await this.schools.upsert(c, ['uai']);
      return { items: rows.length };
    });

    const keyedHealth = this.collector.run('esante_fhir', `postcode:${address.postcode}`, { force }, async (stamp) => {
      const count = await this.keyed.fhirOrganizationsCount(address.postcode ?? '');
      await this.geo.upsertIndicators(address.id, 'services', [{ indicator: 'health_organizations_in_postcode', valueNum: count }], stamp);
      return { items: 1 };
    });

    const keyedSirene = this.collector.run('sirene', `commune:${address.inseeCode}:bakeries`, { force }, async (stamp) => {
      const count = await this.keyed.sireneCount(address.inseeCode, '10.71C');
      await this.geo.upsertIndicators(address.id, 'services', [{ indicator: 'active_bakeries_in_commune', valueNum: count }], stamp);
      return { items: 1 };
    });

    const outcomes = await Promise.all([companies, osm, schools, keyedHealth, keyedSirene]);

    // Temps de trajet réels vers les services les plus proches (après la collecte des lieux).
    outcomes.push(
      await this.collector.run('ign_navigation', target, { force }, async (stamp) => {
        let count = 0;
        for (const t of TRAVEL_TARGETS) {
          const [nearest] = await entitiesWithDistance(
            withinRadius(this.places.createQueryBuilder('s').where('s.category = :c', { c: t.category }), 's', 'location', p, t.radiusM).limit(1),
          );
          if (!nearest) continue;
          for (const profile of t.profiles) {
            const route = await this.navigation.route(p, { lat: nearest.latitude, lon: nearest.longitude }, profile);
            await this.travel.upsert(
              {
                addressId: address.id,
                destinationKind: t.kind,
                profile,
                destinationLabel: nearest.name ?? nearest.addressLabel,
                destinationLat: nearest.latitude,
                destinationLon: nearest.longitude,
                durationS: route.durationS,
                distanceM: route.distanceM,
                ...stamp,
              },
              ['addressId', 'destinationKind', 'profile'],
            );
            count++;
          }
        }
        return { items: count };
      }),
    );
    return outcomes;
  }

  async read(address: AddressEntity) {
    const p: LatLon = { lat: address.latitude, lon: address.longitude };
    const [places, emergencies, schools, travel, indicators] = await Promise.all([
      entitiesWithDistance(withinRadius(this.places.createQueryBuilder('s'), 's', 'location', p, SERVICES_RADIUS_M)),
      entitiesWithDistance(withinRadius(this.places.createQueryBuilder('s').where("s.category = 'emergency'"), 's', 'location', p, EMERGENCY_RADIUS_M)),
      this.schoolsAround(address),
      this.travel.find({ where: { addressId: address.id } }),
      this.geo.indicatorsOf(address.id, 'services'),
    ]);

    const categories = [...new Set(places.map((s) => s.category))].sort();
    const byCategory = Object.fromEntries(
      categories.map((c) => {
        const list = places.filter((s) => s.category === c);
        return [c, { countWithin2km: list.length, nearest: list.slice(0, 3) }];
      }),
    );
    const bakeries = places.filter((s) => s.category === 'bakery');

    return {
      byCategory,
      emergency: emergencies.slice(0, 3),
      sundayBakeries: bakeries.filter((b) => b.details?.opensOnSunday === true).slice(0, 5),
      travelTimes: travel,
      schools,
      indicators,
      notCovered: [
        'Médecins acceptant de nouveaux patients',
        'Pharmacie de garde',
        'Carte scolaire (école de secteur)',
        'Maternités (FINESS non interrogeable par API)',
        'Trajet domicile-travail avec trafic aux heures de pointe',
      ],
    };
  }

  async schoolsAround(address: AddressEntity, radiusM = SCHOOLS_RADIUS_M) {
    return entitiesWithDistance(
      withinRadius(this.schools.createQueryBuilder('e'), 'e', 'location', { lat: address.latitude, lon: address.longitude }, radiusM),
    );
  }

  placesByCategory(insee: string, categories: string[]) {
    return this.places.find({ where: { inseeCode: insee, category: In(categories) }, order: { category: 'ASC', name: 'ASC' } });
  }
}
