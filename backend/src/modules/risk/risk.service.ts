import { Injectable } from '@nestjs/common';
import { InjectRepository } from '@nestjs/typeorm';
import { In, Repository } from 'typeorm';
import { WfsClient } from '../../common/clients/open-data.clients';
import { bboxAround, LatLon, pointInGeometry } from '../../common/geo/geo.utils';
import { entitiesWithDistance, withinRadius } from '../../common/geo/spatial-query';
import { chunk } from '../../common/utils/parse';
import { CollectOutcome, CollectorService } from '../../sources/collector.service';
import { AddressEntity } from '../geo/geo.entities';
import { GeoService } from '../geo/geo.service';
import { GeorisquesClient } from './risk.clients';
import { BioRiskEntity, CatnatDecreeEntity, CommuneRiskProfileEntity, RiskAssessmentEntity, RiskSiteEntity } from './risk.entities';
import {
  normalizeCatnat,
  normalizeCavity,
  normalizeCommuneProfile,
  normalizeGroundMovement,
  normalizeInstallation,
  normalizePollutedSoils,
  normalizeReport,
} from './risk.normalizers';

const SITES_RADIUS_M = 1000;
const ICPE_RADIUS_M = 3000;

@Injectable()
export class RiskService {
  constructor(
    private readonly collector: CollectorService,
    private readonly geo: GeoService,
    private readonly georisques: GeorisquesClient,
    private readonly wfs: WfsClient,
    @InjectRepository(RiskAssessmentEntity) private readonly assessments: Repository<RiskAssessmentEntity>,
    @InjectRepository(CommuneRiskProfileEntity) private readonly profiles: Repository<CommuneRiskProfileEntity>,
    @InjectRepository(CatnatDecreeEntity) private readonly catnats: Repository<CatnatDecreeEntity>,
    @InjectRepository(RiskSiteEntity) private readonly sites: Repository<RiskSiteEntity>,
    @InjectRepository(BioRiskEntity) private readonly bio: Repository<BioRiskEntity>,
  ) {}

  async collect(address: AddressEntity, force = false): Promise<CollectOutcome[]> {
    const p: LatLon = { lat: address.latitude, lon: address.longitude };
    const target = `address:${address.id}`;
    const insee = address.inseeCode;

    const report = this.collector.run('georisques', `${target}:report`, { force }, async (stamp) => {
      const raw = await this.georisques.report(p);
      const rows = normalizeReport(raw, address.id, stamp);
      if (rows.length) await this.assessments.upsert(rows, ['addressId', 'hazardCode']);
      return { items: rows.length, raw };
    });

    const profile = this.collector.run('georisques', `commune:${insee}:profile`, { force }, async (stamp) => {
      const [radon, seismic, risks, azi] = await Promise.all([
        this.georisques.radon(insee),
        this.georisques.seismicZone(insee),
        this.georisques.communeRisks(insee),
        this.georisques.floodAtlases(insee),
      ]);
      await this.profiles.upsert(normalizeCommuneProfile(insee, radon, seismic, risks, azi, stamp), ['inseeCode']);
      return { items: 1, raw: { radon, seismic, risks, azi } };
    });

    const catnat = this.collector.run('georisques', `commune:${insee}:catnat`, { force }, async (stamp) => {
      const raw = await this.georisques.catnat(insee);
      const rows = raw.filter((r) => r.code_national_catnat).map((r) => normalizeCatnat(r, stamp));
      for (const c of chunk(rows, 200)) await this.catnats.upsert(c, ['codeNational', 'inseeCode']);
      return { items: rows.length };
    });

    const sites = this.collector.run('georisques', `${target}:sites`, { force }, async (stamp) => {
      const [cavities, movements, soils, icpe] = await Promise.all([
        this.georisques.cavities(p, SITES_RADIUS_M),
        this.georisques.groundMovements(p, SITES_RADIUS_M),
        this.georisques.pollutedSoils(p, SITES_RADIUS_M),
        this.georisques.installations(p, ICPE_RADIUS_M),
      ]);
      const rows = [
        ...cavities.map((r) => normalizeCavity(r, stamp)),
        ...movements.map((r) => normalizeGroundMovement(r, stamp)),
        ...normalizePollutedSoils(soils, stamp),
        ...icpe.map((r) => normalizeInstallation(r, stamp)),
      ].filter((r): r is Partial<RiskSiteEntity> => r !== null);
      for (const c of chunk(rows, 200)) await this.sites.upsert(c, ['siteType', 'externalId']);
      return { items: rows.length };
    });

    // Obligations légales de débroussaillement (couche nationale IGN, WFS).
    const old = this.collector.run('geopf_wfs', `${target}:debroussaillement`, { force }, async (stamp) => {
      const features = await this.wfs.features('DEBROUSSAILLEMENT:debroussaillement', bboxAround(p, 50), 20);
      const hit = features.find((f) => pointInGeometry(p, f.geometry));
      await this.assessments.upsert(
        {
          addressId: address.id,
          hazardCode: 'obligationDebroussaillement',
          category: 'regulatory',
          label: 'Obligation légale de débroussaillement (OLD)',
          present: Boolean(hit),
          communeStatus: null,
          addressStatus: hit ? 'Zone soumise aux OLD' : 'Hors zone OLD connue',
          details: (hit ? { source: hit.properties.source, millesime: hit.properties.millesime, url: hit.properties.url, arrete: hit.properties.dat_ap_old } : null) as any,
          ...stamp,
        },
        ['addressId', 'hazardCode'],
      );
      return { items: hit ? 1 : 0 };
    });

    return Promise.all([report, profile, catnat, sites, old]);
  }

  async read(address: AddressEntity, radiusM = SITES_RADIUS_M) {
    const p: LatLon = { lat: address.latitude, lon: address.longitude };
    const commune = await this.geo.getCommune(address.inseeCode);
    const [assessments, profile, catnat, nearbySites, bio] = await Promise.all([
      this.assessments.find({ where: { addressId: address.id }, order: { category: 'ASC', hazardCode: 'ASC' } }),
      this.profiles.findOneBy({ inseeCode: address.inseeCode }),
      this.catnatOf(address.inseeCode),
      entitiesWithDistance(withinRadius(this.sites.createQueryBuilder('s'), 's', 'location', p, Math.max(radiusM, ICPE_RADIUS_M))),
      this.bio.find({
        where: [
          { scope: 'commune', areaCode: address.inseeCode },
          { scope: 'department', areaCode: commune.departmentCode },
        ],
        order: { year: 'DESC' },
      }),
    ]);

    const sitesByType = (type: string, max: number) => nearbySites.filter((s) => s.siteType === type && s.distanceM <= max);
    return {
      atAddress: assessments.filter((a) => a.present),
      notPresent: assessments.filter((a) => !a.present).map((a) => a.hazardCode),
      commune: profile,
      catnat: {
        total: catnat.length,
        byHazard: catnat.reduce<Record<string, number>>((acc, c) => ((acc[c.hazardLabel] = (acc[c.hazardLabel] ?? 0) + 1), acc), {}),
        latest: catnat.slice(0, 10),
      },
      sites: {
        seveso: nearbySites.filter((s) => s.siteType === 'icpe' && s.sevesoStatus && !/non/i.test(s.sevesoStatus)),
        icpe: sitesByType('icpe', ICPE_RADIUS_M).slice(0, 50),
        pollutedSoils: [...sitesByType('casias', radiusM), ...sitesByType('ssp', radiusM)],
        cavities: sitesByType('cavity', radiusM),
        groundMovements: sitesByType('ground_movement', radiusM),
      },
      biological: bio,
    };
  }

  catnatOf(insee: string) {
    return this.catnats.find({ where: { inseeCode: insee }, order: { eventStart: 'DESC' } });
  }

  // --------------------------------------------- Risques biologiques (saisie manuelle)

  upsertBioRisks(items: Array<Partial<BioRiskEntity>>) {
    const stamp = this.collector.stamp('manual');
    return this.bio.upsert(items.map((i) => ({ ...i, ...stamp })), ['scope', 'areaCode', 'species', 'year']);
  }

  listBioRisks(filter: { areaCode?: string; species?: string }) {
    const where: any = {};
    if (filter.areaCode) where.areaCode = filter.areaCode;
    if (filter.species) where.species = In(filter.species.split(','));
    return this.bio.find({ where, order: { areaCode: 'ASC', species: 'ASC', year: 'DESC' } });
  }
}
