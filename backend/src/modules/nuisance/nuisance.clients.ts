import { Injectable } from '@nestjs/common';
import { OverpassClient, OverpassElement } from '../../common/clients/open-data.clients';
import { bboxAround, LatLon } from '../../common/geo/geo.utils';
import { HttpClientService } from '../../common/http/http-client.service';

/**
 * Catégorisation des objets OSM « source de nuisance ».
 * L'ordre compte : la première règle qui correspond l'emporte.
 */
export const POI_RULES: Array<{ category: string; match: (t: Record<string, string>) => boolean }> = [
  { category: 'nightlife', match: (t) => /^(bar|pub|nightclub)$/.test(t.amenity ?? '') },
  { category: 'concert_venue', match: (t) => /^(music_venue|theatre|events_venue|arts_centre)$/.test(t.amenity ?? '') },
  { category: 'stadium', match: (t) => t.leisure === 'stadium' || t.building === 'stadium' },
  { category: 'marketplace', match: (t) => t.amenity === 'marketplace' },
  { category: 'place_of_worship', match: (t) => t.amenity === 'place_of_worship' },
  { category: 'wastewater_plant', match: (t) => t.man_made === 'wastewater_plant' },
  { category: 'grain_silo', match: (t) => t.man_made === 'silo' },
  { category: 'farm', match: (t) => t.landuse === 'farmyard' },
  { category: 'landfill', match: (t) => t.landuse === 'landfill' || t.amenity === 'waste_transfer_station' },
  { category: 'industrial', match: (t) => t.landuse === 'industrial' },
  { category: 'wind_turbine', match: (t) => t['generator:source'] === 'wind' },
  { category: 'airport', match: (t) => t.aeroway === 'aerodrome' },
];

export const LINE_RULES: Array<{ category: string; match: (t: Record<string, string>) => boolean }> = [
  { category: 'power_line', match: (t) => t.power === 'line' },
  { category: 'railway', match: (t) => t.railway === 'rail' },
  { category: 'major_road', match: (t) => /^(motorway|trunk)$/.test(t.highway ?? '') },
];

@Injectable()
export class NuisanceOverpassClient {
  constructor(private readonly overpass: OverpassClient) {}

  async around(p: LatLon, radiusM: number, wideRadiusM: number): Promise<{ pois: OverpassElement[]; lines: OverpassElement[] }> {
    const a = `around:${radiusM},${p.lat},${p.lon}`;
    const w = `around:${wideRadiusM},${p.lat},${p.lon}`;
    const ql = `[out:json][timeout:60];
(
  nwr(${a})[amenity~"^(bar|pub|nightclub|music_venue|theatre|events_venue|arts_centre|marketplace|place_of_worship|waste_transfer_station)$"];
  nwr(${a})[leisure=stadium];
  nwr(${a})[man_made~"^(wastewater_plant|silo)$"];
  nwr(${a})[landuse~"^(farmyard|industrial|landfill)$"];
  nwr(${w})["generator:source"=wind];
  nwr(${w})[aeroway=aerodrome];
)->.pois;
.pois out center tags;
(
  way(${w})[power=line];
  way(${a})[railway=rail];
  way(${a})[highway~"^(motorway|trunk)$"];
)->.lines;
.lines out geom tags;`;
    const elements = await this.overpass.query(ql);
    return {
      pois: elements.filter((e) => !e.geometry),
      lines: elements.filter((e) => e.type === 'way' && e.geometry),
    };
  }
}

@Injectable()
export class OpenSkyClient {
  constructor(private readonly http: HttpClientService) {}

  /** Instantané des aéronefs dans une boîte autour du point (accès anonyme, quota limité). */
  async states(p: LatLon, radiusM: number): Promise<{ time: number; states: any[][] }> {
    const b = bboxAround(p, radiusM);
    const res: any = await this.http.get('https://opensky-network.org/api/states/all', {
      source: 'opensky',
      params: { lamin: b.minLat, lomin: b.minLon, lamax: b.maxLat, lomax: b.maxLon },
    });
    return { time: res.time, states: res.states ?? [] };
  }
}
