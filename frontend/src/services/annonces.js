import { request } from './api'

const round = (value) => Math.round(value * 1e5) / 1e5

export const annoncesService = {
  /**
   * Annonces d'une commune (`communeCode`), sinon de l'emprise `bbox` ([ouest, sud, est, nord]).
   * Le département concerné (celui de la commune, sinon `departmentCode`) est scrapé par l'API s'il n'a
   * encore aucune annonce en base : la réponse peut alors prendre jusqu'à une minute.
   */
  getOnMap({ communeCode, bbox, departmentCode, transactionType, propertyType }, { signal } = {}) {
    const params = new URLSearchParams({ transaction_type: transactionType })
    if (communeCode) {
      params.set('commune_code', communeCode)
    } else {
      const [west, south, east, north] = bbox.map(round)
      Object.entries({ west, south, east, north }).forEach(([k, v]) => params.set(k, v))
      if (departmentCode) params.set('department_code', departmentCode)
    }
    if (propertyType) params.set('property_type', propertyType)
    return request(`/annonces/map?${params}`, { signal })
  },

  /**
   * Fiche complète d'une annonce. Lue en base si l'API l'a déjà ; sinon l'API récupère la page de
   * l'annonce (un crédit ScrapeUnblocker, jusqu'à une minute). `refresh` force une nouvelle lecture.
   */
  getDetails(annonceId, { refresh = false, signal } = {}) {
    const query = refresh ? '?refresh=true' : ''
    return request(`/annonces/${encodeURIComponent(annonceId)}/details${query}`, { signal })
  },
}
