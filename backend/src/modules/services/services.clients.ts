import { Injectable } from '@nestjs/common';
import { ConfigService } from '@nestjs/config';
import { OdsClient, OverpassClient } from '../../common/clients/open-data.clients';
import { LatLon } from '../../common/geo/geo.utils';
import { MissingApiKeyError } from '../../common/http/external-api.error';
import { HttpClientService } from '../../common/http/http-client.service';

/** Codes NAF -> catégorie de service. */
export const NAF_CATEGORIES: Record<string, string> = {
  '86.21Z': 'general_practitioner',
  '47.73Z': 'pharmacy',
  '86.10Z': 'hospital',
  '10.71C': 'bakery',
  '88.91A': 'childcare',
  '47.11F': 'supermarket',
  '47.11D': 'supermarket',
  '53.10Z': 'post_office',
};

@Injectable()
export class RechercheEntreprisesClient {
  constructor(private readonly http: HttpClientService) {}

  /** Établissements actifs dans un rayon (km), filtrés par code NAF. */
  async nearPoint(p: LatLon, radiusKm: number, naf: string[], maxPages = 8): Promise<any[]> {
    const out: any[] = [];
    for (let page = 1; page <= maxPages; page++) {
      const res: any = await this.http.get('https://recherche-entreprises.api.gouv.fr/near_point', {
        source: 'recherche_entreprises',
        params: { lat: p.lat, long: p.lon, radius: radiusKm, activite_principale: naf.join(','), per_page: 25, page },
      });
      for (const ul of res.results ?? []) {
        for (const e of ul.matching_etablissements ?? []) out.push({ ...e, nom_complet: ul.nom_complet });
      }
      if (page >= (res.total_pages ?? 1)) break;
    }
    return out;
  }
}

@Injectable()
export class ServicesOverpassClient {
  constructor(private readonly overpass: OverpassClient) {}

  /** Urgences (rayon large), pharmacies, boulangeries et crèches avec horaires OSM. */
  around(p: LatLon, radiusM: number, emergencyRadiusM: number) {
    const a = `around:${radiusM},${p.lat},${p.lon}`;
    const e = `around:${emergencyRadiusM},${p.lat},${p.lon}`;
    return this.overpass.query(`[out:json][timeout:60];
(
  nwr(${e})[amenity=hospital][emergency=yes];
  nwr(${e})[healthcare=hospital][emergency=yes];
  nwr(${a})[amenity~"^(pharmacy|childcare|kindergarten)$"];
  nwr(${a})[shop=bakery];
);
out center tags;`);
  }
}

@Injectable()
export class EducationClient {
  static readonly BASE = 'https://data.education.gouv.fr/api/explore/v2.1';

  constructor(private readonly ods: OdsClient) {}

  schoolsAround(p: LatLon, radiusM: number) {
    return this.ods.records('education', EducationClient.BASE, 'fr-en-annuaire-education', {
      where: `within_distance(position, geom'POINT(${p.lon} ${p.lat})', ${radiusM}m) AND etat="OUVERT"`,
    }, 200);
  }

  /** IPS : jeux distincts écoles / collèges ; on garde la rentrée la plus récente. */
  ips(dataset: 'fr-en-ips-ecoles-ap2022' | 'fr-en-ips-colleges-ap2023', uais: string[]) {
    if (uais.length === 0) return Promise.resolve([]);
    return this.ods.records('education', EducationClient.BASE, dataset, {
      where: `uai IN (${uais.map((u) => `"${u}"`).join(',')})`,
      select: 'uai,ips,rentree_scolaire',
      order_by: 'rentree_scolaire DESC',
    }, 500);
  }

  headcounts(uais: string[]) {
    if (uais.length === 0) return Promise.resolve([]);
    return this.ods.records('education', EducationClient.BASE, 'fr-en-ecoles-effectifs-nb_classes', {
      where: `numero_ecole IN (${uais.map((u) => `"${u}"`).join(',')})`,
      select: 'numero_ecole,rentree_scolaire,nombre_total_classes,nombre_total_eleves',
      order_by: 'rentree_scolaire DESC',
    }, 500);
  }
}

@Injectable()
export class IgnNavigationClient {
  constructor(private readonly http: HttpClientService) {}

  async route(from: LatLon, to: LatLon, profile: 'car' | 'pedestrian'): Promise<{ durationS: number; distanceM: number }> {
    const res: any = await this.http.get('https://data.geopf.fr/navigation/itineraire', {
      source: 'ign_navigation',
      params: {
        resource: 'bdtopo-osrm',
        start: `${from.lon},${from.lat}`,
        end: `${to.lon},${to.lat}`,
        profile,
        optimization: 'fastest',
        timeUnit: 'second',
        distanceUnit: 'meter',
        getSteps: false,
        geometryFormat: 'geojson',
      },
    });
    return { durationS: Math.round(res.duration), distanceM: Math.round(res.distance) };
  }
}

/** Sources à clé : non testées sans compte, implémentées d'après la documentation officielle. */
@Injectable()
export class KeyedHealthClients {
  constructor(
    private readonly http: HttpClientService,
    private readonly config: ConfigService,
  ) {}

  /** Nombre d'organisations de santé (Annuaire Santé FHIR) sur un code postal. */
  async fhirOrganizationsCount(postcode: string): Promise<number> {
    const key = this.config.get<string>('keys.esante');
    if (!key) throw new MissingApiKeyError('esante_fhir', 'ESANTE_API_KEY');
    const res: any = await this.http.get('https://gateway.api.esante.gouv.fr/fhir/v2/Organization', {
      source: 'esante_fhir',
      headers: { 'ESANTE-API-KEY': key },
      params: { 'address-postalcode': postcode, _summary: 'count' },
    });
    return res.total ?? 0;
  }

  /** Nombre d'établissements actifs d'un code NAF dans une commune (Sirene 3.11). */
  async sireneCount(insee: string, naf: string): Promise<number> {
    const key = this.config.get<string>('keys.sirene');
    if (!key) throw new MissingApiKeyError('sirene', 'INSEE_SIRENE_API_KEY');
    const res: any = await this.http.get('https://api.insee.fr/api-sirene/3.11/siret', {
      source: 'sirene',
      headers: { 'X-INSEE-Api-Key-Integration': key },
      params: {
        q: `codeCommuneEtablissement:${insee} AND periode(activitePrincipaleEtablissement:${naf} AND etatAdministratifEtablissement:A)`,
        nombre: 1,
      },
      allowStatuses: [404],
    });
    return res?.header?.total ?? 0;
  }
}
