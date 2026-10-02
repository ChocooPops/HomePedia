import * as wkx from 'wkx';

export interface LatLon {
  lat: number;
  lon: number;
}

export interface BBox {
  minLat: number;
  minLon: number;
  maxLat: number;
  maxLon: number;
}

const EARTH_RADIUS_M = 6371008.8;
const toRad = (d: number) => (d * Math.PI) / 180;

/** WKT d'un point, ordre « lon lat » (convention MariaDB / GeoJSON). */
export function pointWkt(lon: number, lat: number): string {
  return `POINT(${round(lon, 7)} ${round(lat, 7)})`;
}

export function parseWktPoint(wkt: string | null | undefined): LatLon | null {
  const m = wkt?.match(/POINT\s*\(\s*(-?[\d.]+)\s+(-?[\d.]+)\s*\)/i);
  return m ? { lon: parseFloat(m[1]), lat: parseFloat(m[2]) } : null;
}

/** GeoJSON (Point, LineString, Polygon, Multi*) -> WKT. Ignore les éventuels CRS embarqués. */
export function geoJsonToWkt(geometry: any): string {
  const { crs, ...clean } = geometry ?? {};
  return wkx.Geometry.parseGeoJSON(clean).toWkt();
}

export function haversineMeters(a: LatLon, b: LatLon): number {
  const dLat = toRad(b.lat - a.lat);
  const dLon = toRad(b.lon - a.lon);
  const h = Math.sin(dLat / 2) ** 2 + Math.cos(toRad(a.lat)) * Math.cos(toRad(b.lat)) * Math.sin(dLon / 2) ** 2;
  return 2 * EARTH_RADIUS_M * Math.asin(Math.sqrt(h));
}

export function bboxAround(center: LatLon, radiusM: number): BBox {
  const dLat = (radiusM / EARTH_RADIUS_M) * (180 / Math.PI);
  const dLon = dLat / Math.cos(toRad(center.lat));
  return { minLat: center.lat - dLat, maxLat: center.lat + dLat, minLon: center.lon - dLon, maxLon: center.lon + dLon };
}

export function bboxPolygonWkt(b: BBox): string {
  return `POLYGON((${b.minLon} ${b.minLat},${b.maxLon} ${b.minLat},${b.maxLon} ${b.maxLat},${b.minLon} ${b.maxLat},${b.minLon} ${b.minLat}))`;
}

/** Carré GeoJSON centré sur un point (sert aux API qui n'acceptent pas les points). */
export function squareGeoJson(center: LatLon, halfSideM: number) {
  const b = bboxAround(center, halfSideM);
  return {
    type: 'Polygon',
    coordinates: [[[b.minLon, b.minLat], [b.maxLon, b.minLat], [b.maxLon, b.maxLat], [b.minLon, b.maxLat], [b.minLon, b.minLat]]],
  };
}

/** Test point dans (Multi)Polygon GeoJSON, par lancer de rayon. */
export function pointInGeometry(p: LatLon, geometry: any): boolean {
  if (!geometry) return false;
  const polygons: number[][][][] =
    geometry.type === 'Polygon' ? [geometry.coordinates] : geometry.type === 'MultiPolygon' ? geometry.coordinates : [];
  return polygons.some((rings) => {
    if (!ringContains(rings[0], p)) return false;
    return !rings.slice(1).some((hole) => ringContains(hole, p));
  });
}

function ringContains(ring: number[][], p: LatLon): boolean {
  let inside = false;
  for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) {
    const [xi, yi] = ring[i];
    const [xj, yj] = ring[j];
    if (yi > p.lat !== yj > p.lat && p.lon < ((xj - xi) * (p.lat - yi)) / (yj - yi) + xi) inside = !inside;
  }
  return inside;
}

/**
 * Distance minimale (m) entre un point et une géométrie linéaire ou surfacique GeoJSON.
 * Projection équirectangulaire locale : précision métrique suffisante sous ~50 km.
 */
export function distanceToGeometryMeters(p: LatLon, geometry: any): number {
  if (!geometry) return Infinity;
  if (geometry.type === 'Point') return haversineMeters(p, { lon: geometry.coordinates[0], lat: geometry.coordinates[1] });
  if ((geometry.type === 'Polygon' || geometry.type === 'MultiPolygon') && pointInGeometry(p, geometry)) return 0;
  const lines: number[][][] =
    geometry.type === 'LineString'
      ? [geometry.coordinates]
      : geometry.type === 'MultiLineString' || geometry.type === 'Polygon'
        ? geometry.coordinates
        : geometry.type === 'MultiPolygon'
          ? geometry.coordinates.flat()
          : [];
  const kx = Math.cos(toRad(p.lat)) * 111320;
  const ky = 110540;
  let best = Infinity;
  for (const line of lines) {
    for (let i = 0; i < line.length - 1; i++) {
      const ax = (line[i][0] - p.lon) * kx;
      const ay = (line[i][1] - p.lat) * ky;
      const bx = (line[i + 1][0] - p.lon) * kx;
      const by = (line[i + 1][1] - p.lat) * ky;
      const dx = bx - ax;
      const dy = by - ay;
      const len2 = dx * dx + dy * dy;
      const t = len2 === 0 ? 0 : Math.max(0, Math.min(1, -(ax * dx + ay * dy) / len2));
      best = Math.min(best, Math.hypot(ax + t * dx, ay + t * dy));
    }
  }
  return best;
}

/** WKT -> GeoJSON (pour les géométries lues en base). */
export function wktToGeoJson(wkt: string | null | undefined): any {
  return wkt ? wkx.Geometry.parse(wkt).toGeoJSON() : null;
}

export function round(n: number, digits = 6): number {
  const f = 10 ** digits;
  return Math.round(n * f) / f;
}
