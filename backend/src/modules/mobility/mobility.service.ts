import { Injectable } from '@nestjs/common';
import { InjectRepository } from '@nestjs/typeorm';
import { Repository } from 'typeorm';
import { OverpassClient, TabularClient } from '../../common/clients/open-data.clients';
import { distanceToGeometryMeters, haversineMeters, LatLon, pointWkt } from '../../common/geo/geo.utils';
import { entitiesWithDistance, withinRadius } from '../../common/geo/spatial-query';
import { HttpClientService } from '../../common/http/http-client.service';
import { boolFromFlag, chunk, int, num, str } from '../../common/utils/parse';
import { CollectOutcome, CollectorService } from '../../sources/collector.service';
import { AddressEntity, CommuneEntity } from '../geo/geo.entities';
import { GeoService } from '../geo/geo.service';
import { ChargingStationEntity, ParkingFacilityEntity, TransitFeedEntity, TransitStopEntity } from './mobility.entities';

/** Base nationale IRVE consolidée (ressource « dernière version du schéma »). */
const IRVE_RESOURCE_ID = 'eb76d20a-8501-400e-b336-d85724de5435';
/** Base nationale des lieux de stationnement (hors voirie, non exhaustive). */
const BNLS_RESOURCE_ID = 'e32f7675-913b-4e01-b8c8-0a29733e4407';

const STOPS_RADIUS_M = 800;
const CYCLE_RADIUS_M = 1000;

function stopMode(t: Record<string, string>): string | null {
  if (t.railway === 'station' || t.railway === 'halt') return t.station === 'subway' ? 'metro' : 'train';
  if (t.railway === 'tram_stop') return 'tram';
  if (t.highway === 'bus_stop' || t.amenity === 'bus_station') return 'bus';
  return null;
}

@Injectable()
export class MobilityService {
  /** Catalogue transport.data.gouv mis en cache mémoire (~1 Mo, rafraîchi toutes les 24 h). */
  private catalog: { at: number; data: any[] } | null = null;

  constructor(
    private readonly collector: CollectorService,
    private readonly geo: GeoService,
    private readonly http: HttpClientService,
    private readonly tabular: TabularClient,
    private readonly overpass: OverpassClient,
    @InjectRepository(ChargingStationEntity) private readonly chargers: Repository<ChargingStationEntity>,
    @InjectRepository(ParkingFacilityEntity) private readonly parkings: Repository<ParkingFacilityEntity>,
    @InjectRepository(TransitStopEntity) private readonly stops: Repository<TransitStopEntity>,
    @InjectRepository(TransitFeedEntity) private readonly feeds: Repository<TransitFeedEntity>,
  ) {}

  async collect(address: AddressEntity, force = false): Promise<CollectOutcome[]> {
    const p: LatLon = { lat: address.latitude, lon: address.longitude };
    const insee = address.inseeCode;
    const target = `address:${address.id}`;
    const commune = await this.geo.getCommune(insee);

    const irve = this.collector.run('irve', `commune:${insee}`, { force }, async (stamp) => {
      const raw = await this.tabular.query('irve', IRVE_RESOURCE_ID, { code_insee_commune: insee }, { maxRows: 2000 });
      const rows = raw
        .map((r) => {
          const lon = num(r.consolidated_longitude);
          const lat = num(r.consolidated_latitude);
          if (!r.id_pdc_itinerance || lat === null || lon === null) return null;
          const connectors = ['prise_type_ef', 'prise_type_2', 'prise_type_combo_ccs', 'prise_type_chademo', 'prise_type_autre']
            .filter((k) => boolFromFlag(r[k]))
            .map((k) => k.replace('prise_type_', ''));
          return {
            pdcId: String(r.id_pdc_itinerance).slice(0, 64),
            stationName: str(r.nom_station, 255),
            operatorName: str(r.nom_operateur ?? r.nom_amenageur, 160),
            inseeCode: insee,
            powerKw: num(r.puissance_nominale),
            connectors,
            isFree: boolFromFlag(r.gratuit),
            accessCondition: str(r.condition_acces, 80),
            openingHours: str(r.horaires, 255),
            latitude: lat,
            longitude: lon,
            location: pointWkt(lon, lat),
            ...stamp,
          };
        })
        .filter((r): r is NonNullable<typeof r> => r !== null);
      for (const c of chunk(rows, 300)) await this.chargers.upsert(c, ['pdcId']);
      return { items: rows.length };
    });

    const parking = this.collector.run('bnls', `commune:${insee}`, { force }, async (stamp) => {
      const raw = await this.tabular.query('bnls', BNLS_RESOURCE_ID, { insee }, { maxRows: 500 });
      const rows = raw
        .filter((r) => r.id && num(r.Ylat) !== null && num(r.Xlong) !== null)
        .map((r) => ({
          externalId: String(r.id).slice(0, 64),
          name: str(r.nom, 255),
          inseeCode: insee,
          places: int(r.nb_places),
          pmrPlaces: int(r.nb_pmr),
          evPlaces: int(r.nb_voitures_electriques),
          isFree: boolFromFlag(r.gratuit),
          hourlyRateEur: num(r.tarif_1h),
          residentSubscriptionEur: num(r.abo_resident),
          latitude: num(r.Ylat)!,
          longitude: num(r.Xlong)!,
          location: pointWkt(num(r.Xlong)!, num(r.Ylat)!),
          ...stamp,
        }));
      if (rows.length) await this.parkings.upsert(rows, ['externalId']);
      return { items: rows.length };
    });

    const osm = this.collector.run('overpass', `${target}:mobility`, { force }, async (stamp) => {
      const elements = await this.overpass.query(`[out:json][timeout:60];
(
  nwr(around:${STOPS_RADIUS_M},${p.lat},${p.lon})[highway=bus_stop];
  nwr(around:${STOPS_RADIUS_M},${p.lat},${p.lon})[railway~"^(station|halt|tram_stop)$"];
)->.stops;
.stops out center tags;
way(around:${CYCLE_RADIUS_M},${p.lat},${p.lon})[highway=cycleway]->.cw;
way(around:${CYCLE_RADIUS_M},${p.lat},${p.lon})[~"^cycleway(:both|:left|:right)?$"~"^(lane|track)$"]->.lanes;
(.cw; .lanes;);
out geom tags;`);

      const stopRows = elements
        .filter((e) => !e.geometry)
        .map((e) => {
          const t = e.tags ?? {};
          const mode = stopMode(t);
          const lat = e.lat ?? e.center?.lat;
          const lon = e.lon ?? e.center?.lon;
          if (!mode || lat === undefined || lon === undefined) return null;
          return { externalId: `osm:${e.type}/${e.id}`, name: str(t.name, 255), mode, network: str(t.network ?? t.operator, 160), latitude: lat, longitude: lon, location: pointWkt(lon, lat), ...stamp };
        })
        .filter((r): r is NonNullable<typeof r> => r !== null);
      for (const c of chunk(stopRows, 200)) await this.stops.upsert(c, ['externalId']);

      // Longueur d'aménagements cyclables dans le rayon (portions de voies à moins de 1 km).
      let cycleMeters = 0;
      for (const way of elements.filter((e) => e.geometry)) {
        const pts = way.geometry!;
        for (let i = 0; i < pts.length - 1; i++) {
          const mid = { lat: (pts[i].lat + pts[i + 1].lat) / 2, lon: (pts[i].lon + pts[i + 1].lon) / 2 };
          if (haversineMeters(p, mid) <= CYCLE_RADIUS_M) cycleMeters += haversineMeters(pts[i], pts[i + 1]);
        }
      }
      const nearestCycle = Math.min(
        ...elements.filter((e) => e.geometry).map((e) => distanceToGeometryMeters(p, { type: 'LineString', coordinates: e.geometry!.map((g) => [g.lon, g.lat]) })),
      );
      await this.geo.upsertIndicators(address.id, 'mobility', [
        { indicator: 'cycle_infrastructure_within_1km', valueNum: Math.round(cycleMeters), unit: 'm' },
        { indicator: 'nearest_cycle_infrastructure', valueNum: Number.isFinite(nearestCycle) ? Math.round(nearestCycle) : null, unit: 'm' },
      ], stamp);
      return { items: stopRows.length };
    });

    const gtfs = this.collector.run('transport_gouv', `commune:${insee}`, { force }, async (stamp) => {
      const datasets = await this.transportCatalog();
      const matches = datasets
        .filter((d) => d.type === 'public-transit')
        .map((d) => ({ d, level: this.coverageLevel(d.covered_area ?? [], commune) }))
        .filter((m) => m.level !== null);
      const rows = matches.map(({ d, level }) => {
        const gtfs = (d.resources ?? []).find((r: any) => r.format === 'GTFS' && r.type === 'main') ?? (d.resources ?? []).find((r: any) => r.format === 'GTFS');
        return {
          datasetId: String(d.id),
          inseeCode: insee,
          title: String(d.title).slice(0, 255),
          publisher: str(d.publisher?.name, 160),
          gtfsUrl: str(gtfs?.url, 500),
          isAvailable: gtfs?.is_available ?? null,
          coverageLevel: level,
          updatedAt: gtfs?.updated ? new Date(gtfs.updated) : null,
          ...stamp,
        };
      });
      await this.feeds.delete({ inseeCode: insee });
      if (rows.length) await this.feeds.upsert(rows, ['datasetId', 'inseeCode']);
      return { items: rows.length };
    });

    return Promise.all([irve, parking, osm, gtfs]);
  }

  private async transportCatalog(): Promise<any[]> {
    if (!this.catalog || Date.now() - this.catalog.at > 86400000) {
      const data = await this.http.get<any[]>('https://transport.data.gouv.fr/api/datasets', { source: 'transport_gouv', timeout: 60000 });
      this.catalog = { at: Date.now(), data };
    }
    return this.catalog.data;
  }

  /** Le jeu couvre-t-il la commune (directement, via son EPCI, son département ou sa région) ? */
  private coverageLevel(areas: Array<{ type: string; insee: string }>, c: CommuneEntity): string | null {
    for (const a of areas) {
      if (a.type === 'commune' && a.insee === c.inseeCode) return 'commune';
      if (a.type === 'epci' && a.insee === c.epciCode) return 'epci';
      if (a.type === 'departement' && a.insee === c.departmentCode) return 'departement';
      if (a.type === 'region' && a.insee === c.regionCode) return 'region';
    }
    return null;
  }

  async read(address: AddressEntity) {
    const p: LatLon = { lat: address.latitude, lon: address.longitude };
    const [stops, chargers, parkings, feeds, indicators] = await Promise.all([
      entitiesWithDistance(withinRadius(this.stops.createQueryBuilder('t'), 't', 'location', p, STOPS_RADIUS_M)),
      entitiesWithDistance(withinRadius(this.chargers.createQueryBuilder('c'), 'c', 'location', p, 2000)),
      entitiesWithDistance(withinRadius(this.parkings.createQueryBuilder('k'), 'k', 'location', p, 2000)),
      this.feeds.find({ where: { inseeCode: address.inseeCode } }),
      this.geo.indicatorsOf(address.id, 'mobility'),
    ]);
    const modes = [...new Set(stops.map((s) => s.mode))];
    return {
      transit: {
        stopsWithin800m: stops.length,
        byMode: Object.fromEntries(modes.map((m) => [m, stops.filter((s) => s.mode === m).slice(0, 3)])),
        gtfsFeeds: feeds,
        note: 'Derniers départs du soir et service du dimanche : à calculer sur les GTFS (traitement batch, hors API)',
      },
      charging: { pointsWithin2km: chargers.length, fastChargers: chargers.filter((c) => (c.powerKw ?? 0) >= 50).length, nearest: chargers.slice(0, 5) },
      parking: parkings.slice(0, 5),
      cycling: Object.fromEntries(indicators.map((i) => [i.indicator, { value: i.valueNum, unit: i.unit }])),
      notCovered: ['Tarifs et zones de stationnement résident sur voirie'],
    };
  }
}
