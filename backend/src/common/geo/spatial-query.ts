import { ObjectLiteral, SelectQueryBuilder } from 'typeorm';
import { bboxAround, bboxPolygonWkt, LatLon, pointWkt } from './geo.utils';

/**
 * Filtre « dans un rayon » utilisant l'index spatial :
 *  1. MBRContains sur une boîte englobante -> parcours de l'index R-tree ;
 *  2. ST_Distance_Sphere pour la distance exacte (mètres).
 * Ajoute la colonne calculée `distance_m` (récupérable via getRawAndEntities).
 */
export function withinRadius<T extends ObjectLiteral>(
  qb: SelectQueryBuilder<T>,
  alias: string,
  column: string,
  center: LatLon,
  radiusM: number,
): SelectQueryBuilder<T> {
  const bbox = bboxPolygonWkt(bboxAround(center, radiusM));
  const centerExpr = 'ST_GeomFromText(:__center, 4326)';
  return qb
    .addSelect(`ROUND(ST_Distance_Sphere(${alias}.${column}, ${centerExpr}))`, 'distance_m')
    .andWhere(`MBRContains(ST_GeomFromText(:__bbox, 4326), ${alias}.${column})`)
    .andWhere(`ST_Distance_Sphere(${alias}.${column}, ${centerExpr}) <= :__radius`)
    .setParameters({ __center: pointWkt(center.lon, center.lat), __bbox: bbox, __radius: radiusM })
    .orderBy('distance_m', 'ASC');
}

/** Géométries dont l'emprise intersecte la zone (lignes, polygones). Distance à calculer côté JS. */
export function intersectsArea<T extends ObjectLiteral>(
  qb: SelectQueryBuilder<T>,
  alias: string,
  column: string,
  center: LatLon,
  radiusM: number,
): SelectQueryBuilder<T> {
  return qb
    .andWhere(`MBRIntersects(ST_GeomFromText(:__area, 4326), ${alias}.${column})`)
    .setParameter('__area', bboxPolygonWkt(bboxAround(center, radiusM)));
}

/** Associe à chaque entité sa distance (colonne `distance_m` produite par withinRadius). */
export async function entitiesWithDistance<T extends ObjectLiteral>(
  qb: SelectQueryBuilder<T>,
): Promise<Array<T & { distanceM: number }>> {
  const { entities, raw } = await qb.getRawAndEntities();
  return entities.map((e, i) => Object.assign(e, { distanceM: Number(raw[i]?.distance_m ?? NaN) }));
}
