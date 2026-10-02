import { bboxAround, distanceToGeometryMeters, geoJsonToWkt, haversineMeters, parseWktPoint, pointInGeometry, pointWkt } from './geo.utils';

describe('geo.utils', () => {
  const amiens = { lat: 49.892808, lon: 2.297087 };
  const square = {
    type: 'Polygon',
    coordinates: [[[2.29, 49.89], [2.30, 49.89], [2.30, 49.90], [2.29, 49.90], [2.29, 49.89]]],
  };

  it('écrit et relit un point WKT en ordre lon/lat', () => {
    expect(pointWkt(2.297087, 49.892808)).toBe('POINT(2.297087 49.892808)');
    expect(parseWktPoint('POINT(2.297087 49.892808)')).toEqual({ lon: 2.297087, lat: 49.892808 });
  });

  it('calcule une distance haversine réaliste (Amiens -> Paris ≈ 115 km)', () => {
    const d = haversineMeters(amiens, { lat: 48.8566, lon: 2.3522 });
    expect(d).toBeGreaterThan(110000);
    expect(d).toBeLessThan(120000);
  });

  it('teste l’appartenance à un polygone, trous compris', () => {
    expect(pointInGeometry(amiens, square)).toBe(true);
    expect(pointInGeometry({ lat: 49.95, lon: 2.297 }, square)).toBe(false);
    const withHole = { ...square, coordinates: [...square.coordinates, [[2.296, 49.892], [2.298, 49.892], [2.298, 49.894], [2.296, 49.894], [2.296, 49.892]]] };
    expect(pointInGeometry(amiens, withHole)).toBe(false);
  });

  it('mesure la distance point -> ligne', () => {
    const line = { type: 'LineString', coordinates: [[2.29, 49.9], [2.31, 49.9]] };
    const d = distanceToGeometryMeters(amiens, line);
    expect(d).toBeGreaterThan(750);
    expect(d).toBeLessThan(850);
    expect(distanceToGeometryMeters(amiens, square)).toBe(0);
  });

  it('construit une boîte englobante symétrique', () => {
    const b = bboxAround(amiens, 1000);
    expect(haversineMeters(amiens, { lat: b.maxLat, lon: amiens.lon })).toBeCloseTo(1000, -1);
    expect(haversineMeters(amiens, { lat: amiens.lat, lon: b.maxLon })).toBeCloseTo(1000, -1);
  });

  it('convertit du GeoJSON en WKT en ignorant le CRS embarqué', () => {
    expect(geoJsonToWkt({ type: 'Point', coordinates: [2.3, 49.9], crs: { type: 'name' } })).toBe('POINT(2.3 49.9)');
  });
});
