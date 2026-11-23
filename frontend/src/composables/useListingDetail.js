import { ref, shallowRef, watch } from 'vue'
import { annoncesService } from '@/services/annonces'

// Au-delà, l'API est sans doute en train de lire la page de l'annonce sur le site : on le signale.
const SLOW_MS = 2000

/**
 * Fiche complète de l'annonce choisie, rechargée quand le choix change.
 * Les fiches déjà affichées restent en mémoire pour la session.
 *
 * @param annonceId ref de l'identifiant de l'annonce choisie (ou null)
 */
export function useListingDetail(annonceId) {
  const detail = shallowRef(null)
  const loading = ref(false)
  const slow = ref(false)
  const error = ref(null)

  const cache = new Map()
  let controller = null
  let slowTimer = null

  watch(annonceId, (id) => load(id), { immediate: true })

  async function load(id, { refresh = false } = {}) {
    controller?.abort()
    clearTimeout(slowTimer)
    error.value = null

    if (id == null) {
      detail.value = null
      loading.value = slow.value = false
      return
    }
    if (!refresh && cache.has(id)) {
      detail.value = cache.get(id)
      loading.value = slow.value = false
      return
    }

    controller = new AbortController()
    const { signal } = controller
    detail.value = null
    loading.value = true
    slow.value = false
    slowTimer = setTimeout(() => (slow.value = true), SLOW_MS)
    try {
      const result = await annoncesService.getDetails(id, { refresh, signal })
      cache.set(id, result)
      detail.value = result
    } catch (e) {
      if (signal.aborted) return
      error.value = e.message
    } finally {
      if (!signal.aborted) {
        clearTimeout(slowTimer)
        loading.value = slow.value = false
      }
    }
  }

  return { detail, loading, slow, error, refresh: () => load(annonceId.value, { refresh: true }) }
}
