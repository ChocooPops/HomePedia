import { ref, shallowRef, watch } from 'vue'
import { annoncesService } from '@/services/annonces'

const DEBOUNCE_MS = 400
// Un site d'annonces est en cours d'interrogation par l'API : on redemande la zone à ce rythme.
const POLL_MS = 4000

/**
 * Annonces à afficher, rechargées quand la vue, la commune choisie ou les filtres changent :
 * - une commune choisie : toutes ses annonces, où que soit la carte ;
 * - sinon : les annonces de l'emprise affichée (à partir du niveau départements).
 *
 * L'API répond tout de suite avec les annonces en base. Si un site doit être interrogé (département encore
 * vide), elle le fait en tâche de fond (`sync.status = pending`) : la zone est redemandée toutes les
 * quelques secondes, sans effacer la liste, jusqu'à l'arrivée des nouvelles annonces.
 *
 * @param view    ref de { level, bbox, department } émis par la carte
 * @param commune ref de la commune choisie { code, name } ou null
 * @param filters { transactionType, propertyType } (refs)
 */
export function useListings(view, commune, { transactionType, propertyType }) {
  const listings = shallowRef([])
  const truncated = ref(false)
  const sync = ref([]) // ce que l'API a fait pour le département concerné (base, scraping en cours…)
  const loading = ref(false)
  const error = ref(null)

  let timer = null
  let pollTimer = null
  let controller = null
  let lastKey = null // requête déjà envoyée : inutile de la refaire (déplacement avec une commune choisie)

  watch([view, commune, transactionType, propertyType], () => {
    clearTimeout(timer)
    timer = setTimeout(load, DEBOUNCE_MS)
  })

  function query() {
    const filters = { transactionType: transactionType.value, propertyType: propertyType.value }
    if (commune.value) return { ...filters, communeCode: commune.value.code }
    const current = view.value
    if (!current || current.level === 'regions') return null
    return { ...filters, bbox: current.bbox, departmentCode: current.department?.code }
  }

  function reset() {
    listings.value = []
    truncated.value = false
    sync.value = []
  }

  /** `poll` : nouvelle demande de la même zone pendant un scraping, sans indicateur de chargement. */
  async function load({ force = false, poll = false } = {}) {
    const params = query()
    const key = JSON.stringify(params)
    if (key === lastKey && !error.value && !force) return
    lastKey = key

    controller?.abort() // une réponse pour une ancienne vue ne doit pas écraser la nouvelle
    clearTimeout(pollTimer)
    error.value = null

    if (!params) {
      reset()
      loading.value = false
      return
    }

    controller = new AbortController()
    const { signal } = controller
    if (!poll) loading.value = true
    try {
      const result = await annoncesService.getOnMap(params, { signal })
      listings.value = result.annonces
      truncated.value = result.truncated
      sync.value = result.sync
      if (result.sync.some((s) => s.status === 'pending')) {
        pollTimer = setTimeout(() => load({ force: true, poll: true }), POLL_MS)
      }
    } catch (e) {
      if (signal.aborted) return
      if (!poll) reset()
      error.value = e.message
    } finally {
      if (!signal.aborted) loading.value = false
    }
  }

  return { listings, truncated, sync, loading, error, reload: () => load({ force: true }) }
}
