import { Injectable } from '@nestjs/common';
import { InjectRepository } from '@nestjs/typeorm';
import { Between, Repository } from 'typeorm';
import { bboxAround, haversineMeters, LatLon } from '../../common/geo/geo.utils';
import { chunk } from '../../common/utils/parse';
import { CollectOutcome, CollectorService } from '../../sources/collector.service';
import { AddressEntity } from '../geo/geo.entities';
import { GeoService } from '../geo/geo.service';
import { BdnbClient, DpeClient, DvfClient, RnbClient, RnicClient } from './building.clients';
import { BuildingEntity, CondominiumEntity, DpeCertificateEntity, DvfMutationEntity, PriceIndexEntity } from './building.entities';
import {
  buildingPresumptions,
  computePriceIndex,
  normalizeBdnb,
  normalizeDpe,
  normalizeDvfRow,
  normalizeRnb,
  normalizeRnic,
} from './building.normalizers';

const DPE_RADIUS_M = 30;

@Injectable()
export class BuildingService {
  constructor(
    private readonly collector: CollectorService,
    private readonly geo: GeoService,
    private readonly rnb: RnbClient,
    private readonly bdnb: BdnbClient,
    private readonly dpe: DpeClient,
    private readonly dvf: DvfClient,
    private readonly rnic: RnicClient,
    @InjectRepository(BuildingEntity) private readonly buildings: Repository<BuildingEntity>,
    @InjectRepository(DpeCertificateEntity) private readonly dpes: Repository<DpeCertificateEntity>,
    @InjectRepository(DvfMutationEntity) private readonly mutations: Repository<DvfMutationEntity>,
    @InjectRepository(PriceIndexEntity) private readonly prices: Repository<PriceIndexEntity>,
    @InjectRepository(CondominiumEntity) private readonly condos: Repository<CondominiumEntity>,
  ) {}

  // ------------------------------------------------------------- Collecte

  async collect(address: AddressEntity, force = false): Promise<CollectOutcome[]> {
    const p: LatLon = { lat: address.latitude, lon: address.longitude };
    const target = `address:${address.id}`;
    const outcomes: CollectOutcome[] = [];

    outcomes.push(
      await this.collector.run('rnb', target, { force }, async (stamp) => {
        const candidates = await this.rnb.closest(p, 30);
        // On privilégie le bâtiment qui porte l'adresse BAN, sinon le plus proche.
        const chosen = candidates.find((b) => b.addresses?.some((a: any) => a.id === address.banId)) ?? candidates[0];
        if (!chosen) return { items: 0, raw: candidates };
        await this.buildings.upsert(normalizeRnb(chosen, address.inseeCode, stamp), ['rnbId']);
        await this.geo.linkBuilding(address.id, chosen.rnb_id);
        address.rnbId = chosen.rnb_id;
        return { items: 1, raw: chosen };
      }),
    );

    if (address.rnbId) {
      const rnbId = address.rnbId;
      outcomes.push(
        await this.collector.run('bdnb', `rnb:${rnbId}`, { force }, async () => {
          const groupId = await this.bdnb.groupIdForRnb(rnbId);
          if (!groupId) return { items: 0 };
          const group = await this.bdnb.group(groupId);
          if (!group) return { items: 0 };
          await this.buildings.update({ rnbId }, normalizeBdnb(group));
          return { items: 1, raw: group };
        }),
      );
    }

    outcomes.push(
      await this.collector.run('ademe_dpe', target, { force }, async (stamp) => {
        const raw = await this.dpe.near(p, DPE_RADIUS_M);
        const rows = raw.filter((d) => d.numero_dpe).map((d) => normalizeDpe(d, stamp));
        for (const c of chunk(rows, 200)) await this.dpes.upsert(c, ['numeroDpe']);
        return { items: rows.length };
      }),
    );

    const building = address.rnbId ? await this.buildings.findOneBy({ rnbId: address.rnbId }) : null;
    outcomes.push(
      await this.collector.run('rnic', target, { force }, async (stamp) => {
        let raw: any[] = [];
        if (building?.condoRegistration) raw = await this.rnic.byRegistration(building.condoRegistration);
        if (raw.length === 0 && address.parcelIdu) raw = await this.rnic.byParcel(address.parcelIdu);
        const rows = raw.filter((r) => r.numero_d_immatriculation).map((r) => normalizeRnic(r, stamp));
        if (rows.length) await this.condos.upsert(rows, ['registrationNumber']);
        return { items: rows.length };
      }),
    );

    outcomes.push(...(await this.collectDvf(address.inseeCode, undefined, force)));
    return outcomes;
  }

  /** Import DVF d'une commune (toutes les années publiées par défaut) puis recalcul de l'indice de prix. */
  async collectDvf(insee: string, years?: number[], force = false): Promise<CollectOutcome[]> {
    await this.geo.ensureCommune(insee);
    const targetYears = years?.length ? years : await this.dvf.availableYears();
    const outcomes: CollectOutcome[] = [];
    for (const year of targetYears) {
      outcomes.push(
        await this.collector.run('dvf', `commune:${insee}:${year}`, { force }, async (stamp) => {
          const raw = await this.dvf.communeYear(insee, year);
          const rows = raw.map((r) => normalizeDvfRow(r, stamp)).filter((r): r is Partial<DvfMutationEntity> => r !== null);
          for (const c of chunk(rows, 500)) await this.mutations.upsert(c, ['rowHash']);
          return { items: rows.length };
        }),
      );
    }
    if (outcomes.some((o) => o.status === 'success')) await this.computePriceIndex(insee);
    return outcomes;
  }

  async computePriceIndex(insee: string): Promise<PriceIndexEntity[]> {
    const rows = await this.mutations.findBy({ inseeCode: insee, nature: 'Vente' });
    const index = computePriceIndex(rows);
    await this.prices.delete({ inseeCode: insee });
    if (index.length) await this.prices.save(index);
    return index.sort((a, b) => a.year - b.year || a.propertyType.localeCompare(b.propertyType));
  }

  // -------------------------------------------------------------- Lecture

  async read(address: AddressEntity) {
    const building = address.rnbId ? await this.buildings.findOneBy({ rnbId: address.rnbId }) : null;

    const p: LatLon = { lat: address.latitude, lon: address.longitude };
    const b = bboxAround(p, DPE_RADIUS_M);
    const candidates = await this.dpes.find({
      where: [
        ...(address.banId ? [{ banId: address.banId }] : []),
        ...(address.rnbId ? [{ rnbId: address.rnbId }] : []),
        { latitude: Between(b.minLat, b.maxLat), longitude: Between(b.minLon, b.maxLon) },
      ],
      order: { issuedAt: 'DESC' },
      take: 200,
    });
    const dpes = candidates.map((d) => ({
      ...d,
      sameAddress: d.banId === address.banId,
      distanceM: d.latitude !== null && d.longitude !== null ? Math.round(haversineMeters(p, { lat: d.latitude, lon: d.longitude })) : null,
    }));
    const reference = dpes.find((d) => d.sameAddress) ?? dpes[0] ?? null;

    const condo = building?.condoRegistration
      ? await this.condos.findOneBy({ registrationNumber: building.condoRegistration })
      : address.parcelIdu
        ? await this.condos.createQueryBuilder('c').where('JSON_CONTAINS(c.cadastral_refs, :ref)', { ref: JSON.stringify(address.parcelIdu) }).getOne()
        : null;

    const year = building?.constructionYear ?? reference?.constructionYear ?? null;
    return {
      building,
      dpe: { reference, all: dpes },
      condominium: condo,
      ceilingHeightM: reference?.ceilingHeightM ?? null,
      presumptions: buildingPresumptions(year, reference?.energyClass ?? null),
    };
  }

  priceIndex(insee: string) {
    return this.prices.find({ where: { inseeCode: insee }, order: { year: 'ASC', propertyType: 'ASC' } });
  }

  async listMutations(insee: string, filter: { year?: number; type?: string }, page: number, limit: number) {
    const qb = this.mutations.createQueryBuilder('m').where('m.insee_code = :insee', { insee }).orderBy('m.mutation_date', 'DESC');
    if (filter.year) qb.andWhere('m.mutation_date BETWEEN :from AND :to', { from: `${filter.year}-01-01`, to: `${filter.year}-12-31` });
    if (filter.type) qb.andWhere('m.property_type = :type', { type: filter.type });
    const [items, total] = await qb.skip((page - 1) * limit).take(limit).getManyAndCount();
    return { total, page, limit, items };
  }

  /** Ventes autour d'une adresse (rayon en mètres). */
  async mutationsAround(address: AddressEntity, radiusM: number) {
    const p: LatLon = { lat: address.latitude, lon: address.longitude };
    const b = bboxAround(p, radiusM);
    const rows = await this.mutations.find({
      where: { latitude: Between(b.minLat, b.maxLat), longitude: Between(b.minLon, b.maxLon) },
      order: { mutationDate: 'DESC' },
      take: 1000,
    });
    return rows
      .map((r) => ({
        ...r,
        priceM2: r.priceEur && r.builtAreaM2 ? Math.round(r.priceEur / r.builtAreaM2) : null,
        distanceM: Math.round(haversineMeters(p, { lat: r.latitude!, lon: r.longitude! })),
      }))
      .filter((r) => r.distanceM <= radiusM);
  }
}
