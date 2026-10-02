import { Injectable } from '@nestjs/common';
import { InjectRepository } from '@nestjs/typeorm';
import { Repository } from 'typeorm';
import { OverpassElement, WfsClient } from '../../common/clients/open-data.clients';
import { bboxAround, distanceToGeometryMeters, geoJsonToWkt, haversineMeters, LatLon, pointWkt, wktToGeoJson } from '../../common/geo/geo.utils';
import { entitiesWithDistance, intersectsArea, withinRadius } from '../../common/geo/spatial-query';
import { chunk, num, str } from '../../common/utils/parse';
import { CollectOutcome, CollectorService, Stamp } from '../../sources/collector.service';
import { ConnectivityService } from '../connectivity/connectivity.service';
import { AddressEntity } from '../geo/geo.entities';
import { LINE_RULES, NuisanceOverpassClient, OpenSkyClient, POI_RULES } from './nuisance.clients';
import { FlightObservationEntity, NuisanceLineEntity, NuisancePoiEntity } from './nuisance.entities';

const DEFAULT_RADIUS_M = 1000;
const WIDE_RADIUS_M = 3000;
const FLIGHT_RADIUS_M = 15000;
const PEB_RADIUS_M = 30000;

const KEPT_TAGS = ['name', 'amenity', 'leisure', 'man_made', 'landuse', 'opening_hours', 'voltage', 'operator', 'religion', 'bells', 'highway', 'railway', 'aeroway'];
const pickTags = (t: Record<string, string> = {}) => Object.fromEntries(Object.entries(t).filter(([k]) => KEPT_TAGS.includes(k)));

function normalizePoi(e: OverpassElement, stamp: Stamp): Partial<NuisancePoiEntity> | null {
  const t = e.tags ?? {};
  const rule = POI_RULES.find((r) => r.match(t));
  const lat = e.lat ?? e.center?.lat;
  const lon = e.lon ?? e.center?.lon;
  if (!rule || lat === undefined || lon === undefined) return null;
  return {
    externalId: `osm:${e.type}/${e.id}`,
    category: rule.category,
    subcategory: str(t.amenity ?? t.leisure ?? t.man_made ?? t.landuse ?? t.aeroway, 80),
    name: str(t.name, 255),
    tags: pickTags(t),
    latitude: lat,
    longitude: lon,
    location: pointWkt(lon, lat),
    ...stamp,
  };
}

function normalizeLine(e: OverpassElement, stamp: Stamp): Partial<NuisanceLineEntity> | null {
  const t = e.tags ?? {};
  const rule = LINE_RULES.find((r) => r.match(t));
  if (!rule || !e.geometry || e.geometry.length < 2) return null;
  return {
    externalId: `osm:way/${e.id}`,
    category: rule.category,
    subcategory: str(t.voltage ? `${Math.round(Number(t.voltage.split(';')[0]) / 1000)} kV` : (t.highway ?? t.railway), 80),
    name: str(t.name ?? t.ref, 255),
    tags: pickTags(t),
    geom: geoJsonToWkt({ type: 'LineString', coordinates: e.geometry.map((g) => [g.lon, g.lat]) }),
    ...stamp,
  };
}

@Injectable()
export class NuisanceService {
  constructor(
    private readonly collector: CollectorService,
    private readonly overpass: NuisanceOverpassClient,
    private readonly opensky: OpenSkyClient,
    private readonly wfs: WfsClient,
    private readonly connectivity: ConnectivityService,
    @InjectRepository(NuisancePoiEntity) private readonly pois: Repository<NuisancePoiEntity>,
    @InjectRepository(NuisanceLineEntity) private readonly lines: Repository<NuisanceLineEntity>,
    @InjectRepository(FlightObservationEntity) private readonly flights: Repository<FlightObservationEntity>,
  ) {}

  async collect(address: AddressEntity, force = false, radiusM = DEFAULT_RADIUS_M): Promise<CollectOutcome[]> {
    const p: LatLon = { lat: address.latitude, lon: address.longitude };
    const target = `address:${address.id}`;

    const osm = await this.collector.run('overpass', `${target}:r${radiusM}`, { force }, async (stamp) => {
      const { pois, lines } = await this.overpass.around(p, radiusM, Math.max(WIDE_RADIUS_M, radiusM));
      const poiRows = pois.map((e) => normalizePoi(e, stamp)).filter((r): r is Partial<NuisancePoiEntity> => r !== null);
      const lineRows = lines.map((e) => normalizeLine(e, stamp)).filter((r): r is Partial<NuisanceLineEntity> => r !== null);
      for (const c of chunk(poiRows, 200)) await this.pois.upsert(c, ['sourceCode', 'externalId']);
      for (const c of chunk(lineRows, 50)) await this.lines.upsert(c, ['sourceCode', 'externalId']);
      return { items: poiRows.length + lineRows.length };
    });

    const peb = await this.collector.run('geopf_wfs', `${target}:peb`, { force }, async (stamp) => {
      // La couche nationale DGAC ne publie que le point de l'aérodrome + l'arrêté PEB (pas les zones).
      const features = await this.wfs.features('dgac_peb_arrete_wfs:dgac_peb_arrete_wfs', bboxAround(p, PEB_RADIUS_M), 50);
      const rows = features
        .filter((f) => f.geometry?.type === 'Point')
        .map((f) => {
          const [lon, lat] = f.geometry.coordinates;
          return {
            externalId: `peb:${f.properties.oaci ?? f.id}`,
            category: 'airport_noise_plan',
            subcategory: str(f.properties.oaci, 80),
            name: str(f.properties.nom, 255),
            tags: { arrete: f.properties.arrete_peb },
            latitude: lat,
            longitude: lon,
            location: pointWkt(lon, lat),
            ...stamp,
          };
        });
      if (rows.length) await this.pois.upsert(rows, ['sourceCode', 'externalId']);
      return { items: rows.length };
    });

    const flights = await this.collector.run('opensky', target, { force }, async (stamp) => {
      const { time, states } = await this.opensky.states(p, FLIGHT_RADIUS_M);
      const observedAt = new Date(time * 1000);
      const rows = states
        .filter((s) => s[5] !== null && s[6] !== null)
        .map((s) => ({
          addressId: address.id,
          observedAt,
          icao24: String(s[0]),
          callsign: str(s[1], 12),
          originCountry: str(s[2], 64),
          altitudeM: num(s[7] ?? s[13]),
          onGround: Boolean(s[8]),
          velocityMs: num(s[9]),
          distanceM: Math.round(haversineMeters(p, { lat: s[6], lon: s[5] })),
          latitude: s[6],
          longitude: s[5],
          ...stamp,
        }));
      if (rows.length) await this.flights.upsert(rows, ['addressId', 'icao24', 'observedAt']);
      return { items: rows.length };
    });

    return [osm, peb, flights];
  }

  async read(address: AddressEntity, radiusM = DEFAULT_RADIUS_M) {
    const p: LatLon = { lat: address.latitude, lon: address.longitude };

    const nearby = await entitiesWithDistance(withinRadius(this.pois.createQueryBuilder('n'), 'n', 'location', p, Math.max(radiusM, WIDE_RADIUS_M)));
    const pebs = await entitiesWithDistance(
      withinRadius(this.pois.createQueryBuilder('n').where("n.category = 'airport_noise_plan'"), 'n', 'location', p, PEB_RADIUS_M),
    );

    const lineRows = await intersectsArea(this.lines.createQueryBuilder('l').addSelect('ST_AsText(l.geom)', 'wkt'), 'l', 'geom', p, WIDE_RADIUS_M).getRawAndEntities();
    const lines = lineRows.entities
      .map((l, i) => ({ ...l, distanceM: Math.round(distanceToGeometryMeters(p, wktToGeoJson(lineRows.raw[i].wkt))) }))
      .filter((l) => l.distanceM <= WIDE_RADIUS_M)
      .sort((a, b) => a.distanceM - b.distanceM);

    const byCategory: Record<string, { count: number; nearestM: number | null; nearest: unknown }> = {};
    for (const item of [...nearby.filter((n) => n.category !== 'airport_noise_plan'), ...lines]) {
      const limit = ['wind_turbine', 'airport', 'power_line'].includes(item.category) ? WIDE_RADIUS_M : radiusM;
      if (item.distanceM > limit) continue;
      const c = (byCategory[item.category] ??= { count: 0, nearestM: null, nearest: null });
      c.count++;
      if (c.nearestM === null || item.distanceM < c.nearestM) {
        c.nearestM = item.distanceM;
        c.nearest = { name: item.name, subcategory: item.subcategory, distanceM: item.distanceM };
      }
    }

    const lastObservation = await this.flights.findOne({ where: { addressId: address.id }, order: { observedAt: 'DESC' } });
    const flights = lastObservation
      ? await this.flights.find({ where: { addressId: address.id, observedAt: lastObservation.observedAt }, order: { distanceM: 'ASC' } })
      : [];
    const airborne = flights.filter((f) => !f.onGround && f.altitudeM !== null);

    return {
      radiusM,
      summary: byCategory,
      powerLines: lines.filter((l) => l.category === 'power_line').slice(0, 5),
      mobileAntennas: await this.connectivity.sitesAround(p, 500),
      airportNoisePlans: pebs.slice(0, 5),
      flights: {
        snapshotAt: lastObservation?.observedAt ?? null,
        aircraftWithin15km: airborne.length,
        lowestAltitudeM: airborne.length ? Math.min(...airborne.map((f) => f.altitudeM!)) : null,
        closest: airborne.slice(0, 5),
        note: 'Instantané OpenSky : à échantillonner dans le temps pour estimer un couloir aérien',
      },
      notCovered: ['Pollution lumineuse', 'Livraisons et fret de nuit', 'Odeurs d’épandage', 'Cartes de bruit stratégiques (WMS uniquement)'],
    };
  }
}
