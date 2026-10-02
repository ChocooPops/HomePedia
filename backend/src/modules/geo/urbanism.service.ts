import { Injectable } from '@nestjs/common';
import { InjectRepository } from '@nestjs/typeorm';
import { Repository } from 'typeorm';
import { distanceToGeometryMeters, haversineMeters, LatLon, pointInGeometry, squareGeoJson, wktToGeoJson } from '../../common/geo/geo.utils';
import { intersectsArea } from '../../common/geo/spatial-query';
import { chunk } from '../../common/utils/parse';
import { CollectOutcome, CollectorService } from '../../sources/collector.service';
import { GpuClient, GpuLayer, MonumentsClient } from './geo.clients';
import { AddressEntity, MonumentEntity, PluPrescriptionEntity, PluZoneEntity, PublicEasementEntity } from './geo.entities';
import { normalizeEasement, normalizeMonument, normalizePluZone, normalizePrescription } from './geo.normalizers';

/** Codes de prescription PLU utiles à l'analyse (nomenclature CNIG). */
export const PRESCRIPTION_TYPES: Record<string, string> = {
  '01': 'Espace boisé classé',
  '05': 'Emplacement réservé',
  '07': 'Patrimoine bâti, paysager ou éléments de paysage à protéger',
  '18': 'Orientation d’aménagement et de programmation (OAP)',
  '25': 'Élément de continuité écologique et trame verte et bleue',
  '35': 'Terrain cultivé ou non bâti à protéger en zone urbaine',
};

/** Rayon (m) de collecte des zones et prescriptions voisines. */
const NEIGHBOURHOOD_HALF_SIDE_M = 250;

@Injectable()
export class UrbanismService {
  constructor(
    private readonly collector: CollectorService,
    private readonly gpu: GpuClient,
    private readonly monuments: MonumentsClient,
    @InjectRepository(PluZoneEntity) private readonly zones: Repository<PluZoneEntity>,
    @InjectRepository(PluPrescriptionEntity) private readonly prescriptions: Repository<PluPrescriptionEntity>,
    @InjectRepository(PublicEasementEntity) private readonly easements: Repository<PublicEasementEntity>,
    @InjectRepository(MonumentEntity) private readonly monumentRepo: Repository<MonumentEntity>,
  ) {}

  async collect(address: AddressEntity, force = false): Promise<CollectOutcome[]> {
    const p: LatLon = { lat: address.latitude, lon: address.longitude };
    const area = squareGeoJson(p, NEIGHBOURHOOD_HALF_SIDE_M);
    const target = `address:${address.id}`;

    const zones = await this.collector.run('apicarto_gpu', `${target}:zone-urba`, { force }, async (stamp) => {
      const features = await this.gpu.layer('zone-urba', area);
      const rows = features.filter((f) => f.geometry).map((f) => normalizePluZone(f, address.inseeCode, stamp));
      for (const c of chunk(rows, 50)) await this.zones.upsert(c, ['gpuId']);
      return { items: rows.length };
    });

    const prescriptions = await this.collector.run('apicarto_gpu', `${target}:prescriptions`, { force }, async (stamp) => {
      let count = 0;
      for (const layer of ['prescription-surf', 'prescription-lin', 'prescription-pct'] as GpuLayer[]) {
        const features = await this.gpu.layer(layer, area);
        const rows = features.filter((f) => f.geometry).map((f) => normalizePrescription(f, layer, address.inseeCode, stamp));
        for (const c of chunk(rows, 50)) await this.prescriptions.upsert(c, ['gpuId']);
        count += rows.length;
      }
      return { items: count };
    });

    const easements = await this.collector.run('apicarto_gpu', `${target}:sup`, { force }, async (stamp) => {
      const features = await this.gpu.layer('assiette-sup-s', { type: 'Point', coordinates: [p.lon, p.lat] });
      const rows = features.filter((f) => f.geometry).map((f) => normalizeEasement(f, stamp));
      for (const c of chunk(rows, 50)) await this.easements.upsert(c, ['gpuId']);
      return { items: rows.length };
    });

    const monuments = await this.collector.run('monuments', `commune:${address.inseeCode}`, { force }, async (stamp) => {
      const raw = await this.monuments.byCommune(address.inseeCode);
      const rows = raw.map((r) => normalizeMonument(r, stamp)).filter((r): r is Partial<MonumentEntity> => r !== null);
      for (const c of chunk(rows, 200)) await this.monumentRepo.upsert(c, ['reference']);
      return { items: rows.length };
    });

    return [zones, prescriptions, easements, monuments];
  }

  /** Lecture : zone PLU au point, zones et prescriptions voisines, périmètres MH, monuments proches. */
  async read(address: AddressEntity, radiusM = 250) {
    const p: LatLon = { lat: address.latitude, lon: address.longitude };

    const zoneRows = await intersectsArea(
      this.zones.createQueryBuilder('z').addSelect('ST_AsText(z.geom)', 'wkt'),
      'z', 'geom', p, radiusM,
    ).getRawAndEntities();
    const zones = zoneRows.entities.map((z, i) => {
      const geom = wktToGeoJson(zoneRows.raw[i].wkt);
      return { ...z, containsAddress: pointInGeometry(p, geom), distanceM: Math.round(distanceToGeometryMeters(p, geom)) };
    }).filter((z) => z.distanceM <= radiusM).sort((a, b) => a.distanceM - b.distanceM);

    const prescRows = await intersectsArea(
      this.prescriptions.createQueryBuilder('pr').addSelect('ST_AsText(pr.geom)', 'wkt'),
      'pr', 'geom', p, radiusM,
    ).getRawAndEntities();
    const prescriptions = prescRows.entities.map((pr, i) => ({
      ...pr,
      typeLabel: PRESCRIPTION_TYPES[pr.typeCode ?? ''] ?? null,
      distanceM: Math.round(distanceToGeometryMeters(p, wktToGeoJson(prescRows.raw[i].wkt))),
    })).filter((pr) => pr.distanceM <= radiusM).sort((a, b) => a.distanceM - b.distanceM);

    const supRows = await intersectsArea(
      this.easements.createQueryBuilder('s').addSelect('ST_AsText(s.geom)', 'wkt'),
      's', 'geom', p, 1,
    ).getRawAndEntities();
    // Une même servitude est souvent publiée en plusieurs exemplaires (un par acte / document) : on dédoublonne.
    const seen = new Set<string>();
    const easements = supRows.entities
      .filter((_, i) => pointInGeometry(p, wktToGeoJson(supRows.raw[i].wkt)))
      .filter((e) => {
        const key = `${e.supType}|${e.generatorId ?? e.name}`;
        return seen.has(key) ? false : (seen.add(key), true);
      });

    const monuments = (await this.monumentRepo.findBy({ inseeCode: address.inseeCode }))
      .map((m) => ({ ...m, distanceM: m.latitude !== null && m.longitude !== null ? Math.round(haversineMeters(p, { lat: m.latitude, lon: m.longitude })) : null }))
      .sort((a, b) => (a.distanceM ?? Infinity) - (b.distanceM ?? Infinity));

    return {
      currentZone: zones.find((z) => z.containsAddress) ?? null,
      neighbouringZones: zones.filter((z) => !z.containsAddress),
      reservedLocations: prescriptions.filter((pr) => pr.typeCode === '05'),
      protectedLandscape: prescriptions.filter((pr) => ['01', '07', '25', '35'].includes(pr.typeCode ?? '')),
      otherPrescriptions: prescriptions.filter((pr) => !['01', '05', '07', '25', '35'].includes(pr.typeCode ?? '')),
      historicMonumentPerimeter: easements.filter((e) => e.supType === 'ac1'),
      otherEasements: easements.filter((e) => e.supType !== 'ac1'),
      monuments: monuments.slice(0, 20),
    };
  }
}
