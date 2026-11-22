import { request } from './api'

// Les contours ne changent pas : on garde chaque réponse en mémoire pour la session.
const cache = new Map()

function cached(path) {
  if (!cache.has(path)) {
    cache.set(
      path,
      request(path).catch((error) => {
        cache.delete(path)
        throw error
      }),
    )
  }
  return cache.get(path)
}

export const geoDataService = {
  getRegions() {
    return cached('/geodata/regions')
  },

  getDepartmentsByRegion(regionCode) {
    return cached(`/geodata/regions/${encodeURIComponent(regionCode)}/departments`)
  },

  getCommunesByDepartment(departmentCode) {
    return cached(`/geodata/departments/${encodeURIComponent(departmentCode)}/communes`)
  },
}

/** Convertit une liste de DTO (code, name, coordinates) en FeatureCollection GeoJSON. */
export function toFeatureCollection(items) {
  return {
    type: 'FeatureCollection',
    features: items.map(({ coordinates, ...properties }) => ({
      type: 'Feature',
      properties,
      geometry: { type: 'MultiPolygon', coordinates },
    })),
  }
}
