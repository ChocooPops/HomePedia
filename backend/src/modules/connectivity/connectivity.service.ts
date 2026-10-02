import { Injectable } from '@nestjs/common';
import { InjectRepository } from '@nestjs/typeorm';
import { parse } from 'csv-parse/sync';
import { Repository } from 'typeorm';
import { LatLon, pointWkt } from '../../common/geo/geo.utils';
import { entitiesWithDistance, withinRadius } from '../../common/geo/spatial-query';
import { HttpClientService } from '../../common/http/http-client.service';
import { chunk, int, num, str } from '../../common/utils/parse';
import { CollectOutcome, CollectorService, Stamp } from '../../sources/collector.service';
import { AddressEntity } from '../geo/geo.entities';
import { FixedCoverageEntity, MobileSiteEntity } from './connectivity.entities';

const FIXED_URL = 'https://data.arcep.fr/fixe/maconnexioninternet/statistiques/last/commune/commune_techno.csv';
const MOBILE_DIR = 'https://data.arcep.fr/mobile/sites/last/';

/** Une ligne par commune : nombre de locaux et locaux éligibles par technologie. */
function normalizeFixed(r: Record<string, string>, stamp: Stamp): Partial<FixedCoverageEntity> | null {
  if (r.type !== 'all' || !r.code_insee) return null;
  const premises = int(r.nbr) ?? 0;
  const ftth = int(r.elig_ftth) ?? 0;
  return {
    inseeCode: r.code_insee.padStart(5, '0'),
    periodDate: r.date,
    premises,
    ftthEligible: ftth,
    cableEligible: int(r.elig_coax) ?? 0,
    copperEligible: int(r.elig_cu) ?? 0,
    thdRadioEligible: int(r.elig_thdr) ?? 0,
    fixed4gEligible: int(r.elig_4gf) ?? 0,
    satelliteEligible: int(r.elig_sat) ?? 0,
    ftthRate: premises ? Math.round((ftth / premises) * 10000) / 100 : null,
    ...stamp,
  };
}

function normalizeSite(r: Record<string, string>, stamp: Stamp): Partial<MobileSiteEntity> | null {
  const lat = num(r.latitude);
  const lon = num(r.longitude);
  if (!r.code_op || !r.num_site || lat === null || lon === null) return null;
  const flag = (k: string) => r[k] === '1';
  return {
    operatorCode: r.code_op,
    siteNumber: r.num_site,
    operatorName: r.nom_op,
    anfrStationId: str(r.id_station_anfr, 24),
    inseeCode: r.insee_com ? r.insee_com.padStart(5, '0') : null,
    has2g: flag('site_2g'),
    has3g: flag('site_3g'),
    has4g: flag('site_4g'),
    has5g: flag('site_5g'),
    has5g3500: flag('site_5g_3500_m_hz'),
    latitude: lat,
    longitude: lon,
    location: pointWkt(lon, lat),
    ...stamp,
  };
}

/**
 * Connectivité. Les deux sources ARCEP sont des fichiers nationaux (pas d'API à l'adresse) :
 * on les importe en base puis on interroge localement (index spatial pour les sites mobiles).
 */
@Injectable()
export class ConnectivityService {
  constructor(
    private readonly collector: CollectorService,
    private readonly http: HttpClientService,
    @InjectRepository(FixedCoverageEntity) private readonly fixed: Repository<FixedCoverageEntity>,
    @InjectRepository(MobileSiteEntity) private readonly sites: Repository<MobileSiteEntity>,
  ) {}

  importFixed(force = false): Promise<CollectOutcome> {
    return this.collector.run('arcep_fixe', 'france:commune_techno', { force }, async (stamp) => {
      const csv: string = await this.http.get(FIXED_URL, { source: 'arcep_fixe', responseType: 'text', timeout: 120000 });
      const rows = (parse(csv, { columns: true, delimiter: ';', skip_empty_lines: true }) as Record<string, string>[])
        .map((r) => normalizeFixed(r, stamp))
        .filter((r): r is Partial<FixedCoverageEntity> => r !== null);
      for (const c of chunk(rows, 1000)) await this.fixed.upsert(c, ['inseeCode']);
      return { items: rows.length };
    });
  }

  importMobileSites(force = false): Promise<CollectOutcome> {
    return this.collector.run('arcep_mobile', 'france:sites', { force }, async (stamp) => {
      const listing: string = await this.http.get(MOBILE_DIR, { source: 'arcep_mobile', responseType: 'text' });
      const files = [...listing.matchAll(/href="([^"]*_sites_(?:Metropole|Outremer)\.csv)"/g)].map((m) => m[1]);
      if (files.length === 0) throw new Error(`Aucun fichier de sites trouvé dans ${MOBILE_DIR}`);
      let total = 0;
      for (const file of files) {
        const csv: string = await this.http.get(new URL(file, MOBILE_DIR).toString(), { source: 'arcep_mobile', responseType: 'text', timeout: 300000 });
        const rows = (parse(csv, { columns: true, delimiter: ';', skip_empty_lines: true, relax_column_count: true }) as Record<string, string>[])
          .map((r) => normalizeSite(r, stamp))
          .filter((r): r is Partial<MobileSiteEntity> => r !== null);
        for (const c of chunk(rows, 1000)) await this.sites.upsert(c, ['operatorCode', 'siteNumber']);
        total += rows.length;
      }
      return { items: total, raw: { files } };
    });
  }

  /** Collecte « à l'adresse » : s'assure que les deux référentiels nationaux sont chargés et à jour. */
  async collect(_address: AddressEntity, force = false): Promise<CollectOutcome[]> {
    return [await this.importFixed(force), await this.importMobileSites(force)];
  }

  async sitesAround(p: LatLon, radiusM: number) {
    return entitiesWithDistance(withinRadius(this.sites.createQueryBuilder('m'), 'm', 'location', p, radiusM));
  }

  async read(address: AddressEntity) {
    const p: LatLon = { lat: address.latitude, lon: address.longitude };
    const [fixed, sites] = await Promise.all([this.fixed.findOneBy({ inseeCode: address.inseeCode }), this.sitesAround(p, 3000)]);

    const operators = [...new Set(sites.map((s) => s.operatorName))].sort();
    const mobile = operators.map((op) => {
      const own = sites.filter((s) => s.operatorName === op);
      const nearest = (pred: (s: MobileSiteEntity) => boolean) => own.find(pred)?.distanceM ?? null;
      return {
        operator: op,
        sitesWithin1km: own.filter((s) => s.distanceM <= 1000).length,
        nearest4gM: nearest((s) => s.has4g),
        nearest5gM: nearest((s) => s.has5g),
        nearest5g3500M: nearest((s) => s.has5g3500),
      };
    });

    return {
      fixed: fixed
        ? { ...fixed, scope: 'commune', note: 'Taux communal d’éligibilité : l’éligibilité exacte du logement n’est pas publiée en API' }
        : null,
      mobile,
      note: 'Couverture intérieure non mesurée : indicateurs de proximité des sites ARCEP par opérateur',
      notCovered: ['Réception TNT et satellite à l’adresse'],
    };
  }
}
