import { BadRequestException, Injectable, NotFoundException, UnprocessableEntityException } from '@nestjs/common';
import { InjectRepository } from '@nestjs/typeorm';
import { Repository } from 'typeorm';
import { LatLon, wktToGeoJson } from '../../common/geo/geo.utils';
import { CollectOutcome, CollectorService, Stamp } from '../../sources/collector.service';
import { BanClient, BanFeature, CadastreClient, GeoApiClient } from './geo.clients';
import { AddressEntity, AddressIndicatorEntity, CommuneEntity, ParcelEntity } from './geo.entities';
import { normalizeBanFeature, normalizeCommune, normalizeParcel, pickParcel } from './geo.normalizers';

export interface AddressIndicatorInput {
  indicator: string;
  valueNum?: number | null;
  valueText?: string | null;
  unit?: string | null;
  details?: unknown;
}

/** Score BAN minimal pour accepter un géocodage sans ambiguïté. */
const MIN_GEOCODE_SCORE = 0.5;

@Injectable()
export class GeoService {
  constructor(
    private readonly collector: CollectorService,
    private readonly ban: BanClient,
    private readonly geoApi: GeoApiClient,
    private readonly cadastre: CadastreClient,
    @InjectRepository(AddressEntity) private readonly addresses: Repository<AddressEntity>,
    @InjectRepository(CommuneEntity) private readonly communes: Repository<CommuneEntity>,
    @InjectRepository(ParcelEntity) private readonly parcels: Repository<ParcelEntity>,
    @InjectRepository(AddressIndicatorEntity) private readonly indicators: Repository<AddressIndicatorEntity>,
  ) {}

  // ------------------------------------------------------------------ BAN

  /** Autocomplétion / recherche sans persistance. */
  async search(q: string, limit = 5) {
    const features = await this.ban.search(q, { limit });
    return features.map((f) => ({
      label: f.properties.label,
      score: f.properties.score,
      type: f.properties.type,
      banId: f.properties.id,
      inseeCode: f.properties.citycode,
      latitude: f.geometry.coordinates[1],
      longitude: f.geometry.coordinates[0],
    }));
  }

  /** Géocode une adresse texte et l'enregistre (commune + parcelle rattachées). */
  async geocodeAndSave(q: string, force = false): Promise<{ address: AddressEntity; outcomes: CollectOutcome[] }> {
    const features = await this.ban.search(q, { limit: 1 });
    const best = features[0];
    if (!best) throw new NotFoundException(`Adresse introuvable : « ${q} »`);
    if (best.properties.score < MIN_GEOCODE_SCORE) {
      throw new UnprocessableEntityException({
        message: `Géocodage peu fiable (score ${best.properties.score.toFixed(2)}) : précisez l'adresse`,
        candidate: best.properties.label,
      });
    }
    return this.saveFeature(best, force);
  }

  /** Géocodage inverse d'un point puis enregistrement. */
  async reverseAndSave(p: LatLon, force = false) {
    const [best] = await this.ban.reverse(p);
    if (!best) throw new NotFoundException(`Aucune adresse BAN à proximité de ${p.lat},${p.lon}`);
    return this.saveFeature(best, force);
  }

  private async saveFeature(f: BanFeature, force: boolean) {
    const outcomes: CollectOutcome[] = [];
    outcomes.push(await this.ensureCommune(f.properties.citycode, force));

    const stamp = this.collector.stamp('ban');
    const values = normalizeBanFeature(f, stamp);
    await this.addresses.upsert(values, { conflictPaths: ['banId'], skipUpdateIfNoValuesChanged: false });
    const address = await this.addresses.findOneByOrFail({ banId: values.banId! });
    outcomes.unshift({ source: 'ban', target: `address:${address.id}`, status: 'success', items: 1, fetchedAt: stamp.fetchedAt, expiresAt: stamp.expiresAt });

    outcomes.push(await this.collectParcel(address, force));
    return { address: await this.getAddress(address.id), outcomes };
  }

  // ------------------------------------------------------------- Communes

  async ensureCommune(insee: string, force = false): Promise<CollectOutcome> {
    if (!force && (await this.communes.existsBy({ inseeCode: insee }))) {
      const fresh = await this.collector.freshLog('geo_api', `commune:${insee}`);
      if (fresh) return { source: 'geo_api', target: `commune:${insee}`, status: 'cached', items: 1, fetchedAt: fresh.fetchedAt, expiresAt: fresh.expiresAt };
    }
    const outcome = await this.collector.run('geo_api', `commune:${insee}`, { force: true }, async (stamp) => {
      const raw = await this.geoApi.commune(insee);
      if (!raw) throw new NotFoundException(`Commune INSEE inconnue : ${insee}`);
      await this.communes.upsert(normalizeCommune(raw, stamp), ['inseeCode']);
      return { items: 1, raw };
    });
    if (outcome.status === 'error' && !(await this.communes.existsBy({ inseeCode: insee }))) {
      throw new BadRequestException(`Impossible de récupérer la commune ${insee} : ${outcome.error}`);
    }
    return outcome;
  }

  /** Importe toutes les communes d'un département (utile avant un import DVF ou SSMSI). */
  async collectDepartmentCommunes(dep: string, force = false): Promise<CollectOutcome> {
    return this.collector.run('geo_api', `department:${dep}`, { force }, async (stamp) => {
      const raw = await this.geoApi.communesOfDepartment(dep);
      const rows = raw.filter((c) => c.centre).map((c) => normalizeCommune(c, stamp));
      for (let i = 0; i < rows.length; i += 200) await this.communes.upsert(rows.slice(i, i + 200), ['inseeCode']);
      return { items: rows.length };
    });
  }

  async getCommune(insee: string): Promise<CommuneEntity> {
    let commune = await this.communes.findOneBy({ inseeCode: insee });
    if (!commune) {
      await this.ensureCommune(insee);
      commune = await this.communes.findOneByOrFail({ inseeCode: insee });
    }
    return commune;
  }

  listCommunes(filter: { department?: string; region?: string }, page: number, limit: number) {
    const where: any = {};
    if (filter.department) where.departmentCode = filter.department;
    if (filter.region) where.regionCode = filter.region;
    return this.communes.findAndCount({ where, order: { inseeCode: 'ASC' }, skip: (page - 1) * limit, take: limit });
  }

  // ------------------------------------------------------------- Parcelle

  async collectParcel(address: AddressEntity, force = false): Promise<CollectOutcome> {
    return this.collector.run('apicarto_cadastre', `address:${address.id}`, { force }, async (stamp) => {
      const p = { lat: address.latitude, lon: address.longitude };
      const features = await this.cadastre.parcelsAround(p);
      const chosen = pickParcel(features, p);
      if (!chosen) return { items: 0, raw: features };
      const parcel = normalizeParcel(chosen, stamp);
      if (parcel.inseeCode !== address.inseeCode) await this.ensureCommune(parcel.inseeCode!);
      await this.parcels.upsert(parcel, ['idu']);
      await this.addresses.update(address.id, { parcelIdu: chosen.properties.idu });
      return { items: 1, raw: chosen };
    });
  }

  async getParcel(idu: string, force = false) {
    let parcel = await this.parcels.findOneBy({ idu });
    if (!parcel || force) {
      const outcome = await this.collector.run('apicarto_cadastre', `parcel:${idu}`, { force: true }, async (stamp) => {
        const f = await this.cadastre.parcelByIdu(idu);
        if (!f) throw new NotFoundException(`Parcelle introuvable : ${idu}`);
        await this.communes.existsBy({ inseeCode: f.properties.code_insee }).then((ok) => (ok ? null : this.ensureCommune(f.properties.code_insee)));
        await this.parcels.upsert(normalizeParcel(f, stamp), ['idu']);
        return { items: 1, raw: f };
      });
      if (outcome.status !== 'success') throw new NotFoundException(outcome.error ?? `Parcelle introuvable : ${idu}`);
      parcel = await this.parcels.findOneByOrFail({ idu });
    }
    const geojson = await this.geometryAsGeoJson('parcel', 'idu', idu, 'geom');
    return { ...parcel, geometry: geojson };
  }

  // -------------------------------------------------------------- Adresses

  async getAddress(id: number): Promise<AddressEntity> {
    const address = await this.addresses.findOneBy({ id });
    if (!address) throw new NotFoundException(`Adresse ${id} inconnue`);
    return address;
  }

  async getAddressDetails(id: number) {
    const address = await this.getAddress(id);
    const [commune, parcel] = await Promise.all([
      this.communes.findOneBy({ inseeCode: address.inseeCode }),
      address.parcelIdu ? this.parcels.findOneBy({ idu: address.parcelIdu }) : null,
    ]);
    const parcelGeometry = parcel ? await this.geometryAsGeoJson('parcel', 'idu', parcel.idu, 'geom') : null;
    return { ...address, commune, parcel: parcel ? { ...parcel, geometry: parcelGeometry } : null };
  }

  listAddresses(filter: { insee?: string }, page: number, limit: number) {
    return this.addresses.findAndCount({
      where: filter.insee ? { inseeCode: filter.insee } : {},
      order: { id: 'DESC' },
      skip: (page - 1) * limit,
      take: limit,
    });
  }

  async linkBuilding(addressId: number, rnbId: string) {
    await this.addresses.update(addressId, { rnbId });
  }

  async deleteAddress(id: number) {
    const res = await this.addresses.delete({ id });
    if (!res.affected) throw new NotFoundException(`Adresse ${id} inconnue`);
  }

  // ------------------------------------------------- Indicateurs d'adresse

  async upsertIndicators(addressId: number, domain: string, items: AddressIndicatorInput[], stamp: Stamp) {
    if (items.length === 0) return;
    await this.indicators.upsert(
      items.map((i) => ({
        addressId,
        domain,
        indicator: i.indicator,
        valueNum: i.valueNum ?? null,
        valueText: i.valueText ?? null,
        unit: i.unit ?? null,
        details: (i.details ?? null) as any,
        ...stamp,
      })),
      ['addressId', 'domain', 'indicator'],
    );
  }

  indicatorsOf(addressId: number, domain?: string) {
    return this.indicators.find({ where: domain ? { addressId, domain } : { addressId }, order: { domain: 'ASC', indicator: 'ASC' } });
  }

  // ------------------------------------------------------------- Utilitaire

  async geometryAsGeoJson(table: string, keyColumn: string, key: string | number, column: string) {
    const rows = await this.addresses.query(`SELECT ST_AsText(\`${column}\`) AS wkt FROM \`${table}\` WHERE \`${keyColumn}\` = ?`, [key]);
    return rows[0] ? wktToGeoJson(rows[0].wkt) : null;
  }
}
