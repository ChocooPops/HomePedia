<script setup>
import { computed, nextTick, reactive, ref, watch } from 'vue'
import { describeDetails, describeListing, formatAddress, formatPrice } from '@/utils/listing'

const props = defineProps({
  listings: { type: Array, required: true },
  view: { type: Object, default: null }, // { level, department }
  commune: { type: Object, default: null }, // commune choisie { code, name }
  loading: Boolean,
  error: { type: String, default: null },
  sync: { type: Array, default: () => [] },
  truncated: Boolean,
  selectedId: { type: Number, default: null },
})
const emit = defineEmits(['select', 'clear-commune'])

const list = ref(null)
// Photos qui n'ont pas pu être chargées (retirées du site) : une icône les remplace.
const brokenImages = reactive(new Set())

const zoomedOut = computed(() => !props.commune && (!props.view || props.view.level === 'regions'))
// Lieu concerné par les messages : la commune choisie, sinon le département au centre de la carte
const placeName = computed(() => props.commune?.name ?? props.view?.department?.name)

const count = computed(() => {
  const n = props.listings.length
  const where = props.commune ? `à ${props.commune.name}` : 'dans la zone'
  if (!n) return `Aucune annonce ${where}`
  return `${n}${props.truncated ? '+' : ''} annonce${n > 1 ? 's' : ''} ${where}`
})

/** Messages sur ce que l'API a fait pour le département au centre de la carte. */
const syncMessages = computed(() =>
  props.sync
    .map((s) => {
      const where = props.view?.department?.name && !props.commune ? ` (${props.view.department.name})` : ''
      switch (s.status) {
        case 'scraped':
          return { text: `${s.found} annonce${s.found > 1 ? 's' : ''} récupérée${s.found > 1 ? 's' : ''} sur ${s.source_label}${where}` }
        case 'pending':
          return {
            text: `Recherche de nouvelles annonces sur ${s.source_label}${where}… elles s'afficheront automatiquement`,
            pending: true,
          }
        case 'recently_scraped':
          return props.listings.length ? null : { text: `${s.source_label} déjà consulté récemment${where}, sans annonce géolocalisée` }
        case 'unsupported':
          return { text: `${s.source_label} : département non pris en charge${where}` }
        case 'error':
          return { text: `${s.source_label} indisponible : ${s.detail}`, error: true }
        default:
          return null // annonces déjà en base
      }
    })
    .filter(Boolean),
)

// Annonce choisie sur la carte : on la fait défiler jusqu'à elle.
watch(
  () => props.selectedId,
  async (id) => {
    await nextTick()
    list.value?.querySelector(`[data-id="${id}"]`)?.scrollIntoView({ block: 'nearest', behavior: 'smooth' })
  },
)
</script>

<template>
  <section class="listings">
    <header class="listings__header">
      <h2 class="listings__title">Logements</h2>
      <span v-if="!zoomedOut && !loading" class="listings__count">{{ count }}</span>
    </header>

    <div v-if="commune" class="listings__commune">
      <span>Commune : <strong>{{ commune.name }}</strong></span>
      <button type="button" title="Revenir aux annonces de la zone affichée" @click="emit('clear-commune')">✕</button>
    </div>

    <p v-if="zoomedOut" class="listings__status">
      Zoomez sur un département, ou cliquez une commune, pour voir les logements disponibles.
    </p>
    <template v-else>
      <p v-if="loading" class="listings__status">
        <span class="listings__spinner" aria-hidden="true"></span>
        Chargement…
      </p>
      <p v-if="error" class="listings__status listings__status--error">{{ error }}</p>
      <p
        v-for="message in syncMessages"
        :key="message.text"
        class="listings__status"
        :class="{ 'listings__status--error': message.error }"
      >
        <span v-if="message.pending" class="listings__spinner" aria-hidden="true"></span>
        {{ message.text }}
      </p>
    </template>

    <ul ref="list" class="listings__list">
      <li
        v-for="listing in listings"
        :key="listing.id"
        :data-id="listing.id"
        class="listing"
        :class="{ 'listing--selected': listing.id === selectedId }"
        @click="emit('select', listing.id)"
      >
        <div class="listing__photo">
          <img
            v-if="listing.image_url && !brokenImages.has(listing.id)"
            :src="listing.image_url"
            alt=""
            loading="lazy"
            referrerpolicy="no-referrer"
            @error="brokenImages.add(listing.id)"
          />
          <!-- Pas de photo (annonce enregistrée avant leur stockage) ou photo retirée par le site -->
          <svg v-else viewBox="0 0 24 24" aria-hidden="true" class="listing__placeholder">
            <path d="M3 11.5 12 4l9 7.5M5.5 9.5V20h13V9.5M10 20v-5h4v5" />
          </svg>
        </div>
        <div class="listing__info">
          <div class="listing__top">
            <strong class="listing__price">{{ formatPrice(listing) }}</strong>
            <span class="source-badge">{{ listing.source_label }}</span>
          </div>
          <div class="listing__facts">{{ describeListing(listing) }}</div>
          <div v-if="describeDetails(listing)" class="listing__details">{{ describeDetails(listing) }}</div>
          <div class="listing__address">{{ formatAddress(listing) }}</div>
          <a class="listing__link" :href="listing.url" target="_blank" rel="noopener noreferrer" @click.stop>
            Voir sur {{ listing.source_label }} ↗
          </a>
        </div>
      </li>
    </ul>
  </section>
</template>

<style scoped>
.listings {
  display: flex;
  flex-direction: column;
  min-height: 0;
}

.listings__header {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 8px;
  padding: 16px 16px 8px;
}

.listings__title {
  margin: 0;
  font-size: 1rem;
}

.listings__count {
  color: #6b7280;
  font-size: 0.8rem;
}

.listings__commune {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  margin: 0 16px 8px;
  padding: 4px 4px 4px 10px;
  border-radius: 6px;
  background: #ffedd5;
  color: #9a3412;
  font-size: 0.85rem;
}

.listings__commune button {
  padding: 2px 8px;
  border: 0;
  border-radius: 4px;
  background: transparent;
  color: inherit;
  font: inherit;
  cursor: pointer;
}

.listings__commune button:hover {
  background: #fed7aa;
}

.listings__status {
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 0 16px 8px;
  color: #6b7280;
  font-size: 0.85rem;
}

.listings__status--error {
  color: #b91c1c;
}

.listings__spinner {
  flex: none;
  width: 12px;
  height: 12px;
  border: 2px solid #d1d5db;
  border-top-color: #1d4ed8;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

.listings__list {
  flex: 1;
  min-height: 0;
  margin: 0;
  padding: 0 8px 8px;
  overflow-y: auto;
  list-style: none;
}

.listing {
  display: flex;
  gap: 10px;
  margin-bottom: 6px;
  padding: 8px;
  border: 1px solid #e5e7eb;
  border-radius: 6px;
  font-size: 0.85rem;
  cursor: pointer;
}

.listing:hover {
  border-color: #93c5fd;
}

.listing--selected {
  border-color: #ea580c;
  box-shadow: 0 0 0 1px #ea580c;
}

.listing__photo {
  flex: none;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 96px;
  height: 84px;
  overflow: hidden;
  border-radius: 4px;
  background: #f3f4f6;
}

.listing__photo img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.listing__placeholder {
  width: 32px;
  height: 32px;
  fill: none;
  stroke: #9ca3af;
  stroke-width: 1.5;
  stroke-linecap: round;
  stroke-linejoin: round;
}

.listing__info {
  display: flex;
  flex-direction: column;
  gap: 2px;
  flex: 1;
  min-width: 0;
}

.listing__facts,
.listing__details,
.listing__address {
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
}

.listing__top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.listing__price {
  font-size: 0.95rem;
}

.listing__details,
.listing__address {
  color: #6b7280;
}

.listing__link {
  margin-top: 4px;
  color: #1d4ed8;
  font-size: 0.8rem;
  text-decoration: none;
}

.listing__link:hover {
  text-decoration: underline;
}
</style>
