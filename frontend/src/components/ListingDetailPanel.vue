<script setup>
import { computed, nextTick, ref, watch } from 'vue'
import { describeListing, formatAddress, formatPrice } from '@/utils/listing'

const props = defineProps({
  listing: { type: Object, default: null }, // résumé (liste) : affiché pendant le chargement de la fiche
  detail: { type: Object, default: null }, // fiche complète (AnnonceDetailDto)
  loading: Boolean,
  slow: Boolean,
  error: { type: String, default: null },
  // Offres au même endroit que celle affichée (elle comprise), pour passer de l'une à l'autre
  siblings: { type: Array, default: () => [] },
})
const emit = defineEmits(['close', 'refresh', 'select'])

const siblingIndex = computed(() => props.siblings.findIndex((s) => s.id === (props.listing?.id ?? props.detail?.annonce_id)))
const siblingsList = ref(null)

function showSibling(step) {
  const n = props.siblings.length
  if (n < 2) return
  emit('select', props.siblings[(siblingIndex.value + step + n) % n].id)
}

// La mini-carte de l'offre affichée reste visible dans la bande défilante.
watch(siblingIndex, async (index) => {
  await nextTick()
  siblingsList.value?.children[index]?.scrollIntoView({ block: 'nearest', inline: 'nearest', behavior: 'smooth' })
})

const ENERGY_COLORS = ['#009c6d', '#52b153', '#a5cc74', '#f4e70f', '#f0b40f', '#eb8235', '#d7221f']
const GES_COLORS = ['#f6edfd', '#e4c7fa', '#d5aaf6', '#c68dee', '#b06fe2', '#9149cf', '#6e2fa8']
const RATINGS = ['A', 'B', 'C', 'D', 'E', 'F', 'G']

const dateFormat = new Intl.DateTimeFormat('fr-FR', { dateStyle: 'long' })
const decimal = new Intl.NumberFormat('fr-FR', { maximumFractionDigits: 2 })

const imageIndex = ref(0)
const descriptionOpen = ref(false)

watch(
  () => props.detail,
  () => {
    imageIndex.value = 0
    descriptionOpen.value = false
  },
)

const images = computed(() => props.detail?.images ?? [])
const currentImage = computed(() => images.value[imageIndex.value])
const sourceLabel = computed(() => props.detail?.source_label ?? props.listing?.source_label)
const url = computed(() => props.detail?.url ?? props.listing?.url)

const priceText = computed(() => {
  if (props.detail?.price_label) return props.detail.price_label
  return props.listing ? formatPrice(props.listing) : null
})
const keyFacts = computed(() =>
  props.detail?.key_facts?.length ? props.detail.key_facts : props.listing ? [describeListing(props.listing)] : [],
)
const place = computed(() => {
  const d = props.detail
  if (!d) return props.listing ? formatAddress(props.listing) : null
  const locality = [d.city, d.postal_code && `(${d.postal_code})`].filter(Boolean).join(' ')
  return [d.district, locality].filter(Boolean).join(', ')
})

/** Position (en %) du prix au m² de l'annonce entre le plus bas et le plus haut du secteur. */
const comparison = computed(() => {
  const c = props.detail?.price_comparison
  if (!c || c.low == null || c.high == null || c.price_per_m2 == null || c.high <= c.low) return null
  const position = ((c.price_per_m2 - c.low) / (c.high - c.low)) * 100
  return { ...c, position: Math.min(100, Math.max(0, position)) }
})

function energyColor(scale) {
  const index = RATINGS.indexOf(scale.rating)
  if (index < 0) return '#9ca3af'
  return (/GES|gaz/i.test(scale.name) ? GES_COLORS : ENERGY_COLORS)[index]
}

function formatDate(value) {
  return value ? dateFormat.format(new Date(value)) : null
}

function move(step) {
  const n = images.value.length
  if (n) imageIndex.value = (imageIndex.value + step + n) % n
}
</script>

<template>
  <aside class="detail" aria-label="Fiche de l'annonce">
    <header class="detail__header">
      <span v-if="sourceLabel" class="source-badge">{{ sourceLabel }}</span>
      <a v-if="url" :href="url" target="_blank" rel="noopener noreferrer" class="detail__external">
        Voir sur {{ sourceLabel }} ↗
      </a>
      <button type="button" class="detail__close" title="Fermer" @click="emit('close')">✕</button>
    </header>

    <!-- Plusieurs offres au même endroit : navigation de l'une à l'autre -->
    <nav v-if="siblings.length > 1" class="siblings" aria-label="Offres au même endroit">
      <div class="siblings__bar">
        <button type="button" class="siblings__arrow" title="Offre précédente" @click="showSibling(-1)">‹</button>
        <span class="siblings__count">
          Offre <strong>{{ siblingIndex + 1 }}</strong> / {{ siblings.length }} à cet endroit
        </span>
        <button type="button" class="siblings__arrow" title="Offre suivante" @click="showSibling(1)">›</button>
      </div>
      <ul ref="siblingsList" class="siblings__list">
        <li v-for="(sibling, index) in siblings" :key="sibling.id">
          <button
            type="button"
            class="siblings__card"
            :class="{ active: index === siblingIndex }"
            :aria-current="index === siblingIndex"
            @click="emit('select', sibling.id)"
          >
            <strong>{{ formatPrice(sibling) }}</strong>
            <span>{{ describeListing(sibling) }}</span>
          </button>
        </li>
      </ul>
    </nav>

    <div class="detail__body">
      <!-- Galerie -->
      <div v-if="images.length" class="gallery">
        <img
          :key="currentImage.url"
          :src="currentImage.url"
          :alt="currentImage.description ?? 'Photo du bien'"
          class="gallery__image"
          referrerpolicy="no-referrer"
        />
        <template v-if="images.length > 1">
          <button type="button" class="gallery__nav gallery__nav--prev" title="Photo précédente" @click="move(-1)">‹</button>
          <button type="button" class="gallery__nav gallery__nav--next" title="Photo suivante" @click="move(1)">›</button>
        </template>
        <span class="gallery__counter">{{ imageIndex + 1 }} / {{ images.length }}</span>
      </div>
      <div v-if="images.length > 1" class="thumbnails">
        <button
          v-for="(image, index) in images"
          :key="image.url"
          type="button"
          class="thumbnails__item"
          :class="{ active: index === imageIndex }"
          @click="imageIndex = index"
        >
          <img :src="image.url" alt="" loading="lazy" referrerpolicy="no-referrer" />
        </button>
      </div>
      <div v-else-if="loading" class="gallery gallery--placeholder"></div>

      <section class="detail__section">
        <div class="detail__price">
          <strong>{{ priceText }}</strong>
          <span v-if="detail?.price_note" class="detail__muted">{{ detail.price_note }}</span>
        </div>
        <h2 class="detail__title">{{ detail?.headline ?? detail?.title ?? 'Annonce' }}</h2>
        <div v-if="detail?.title && detail?.headline" class="detail__muted">{{ detail.title }}</div>
        <div v-if="place" class="detail__place">{{ place }}</div>
        <ul v-if="keyFacts.length" class="chips">
          <li v-for="fact in keyFacts" :key="fact">{{ fact }}</li>
        </ul>
        <ul v-if="detail?.tags?.length" class="chips chips--tags">
          <li v-for="tag in detail.tags" :key="tag">{{ tag }}</li>
        </ul>
        <a
          v-for="tour in detail?.virtual_tours ?? []"
          :key="tour"
          :href="tour"
          target="_blank"
          rel="noopener noreferrer"
          class="detail__link"
        >
          Visite virtuelle ↗
        </a>
      </section>

      <p v-if="loading" class="detail__status">
        <span class="spinner" aria-hidden="true"></span>
        {{ slow ? `Lecture de l'annonce sur ${sourceLabel ?? 'le site'}… jusqu'à une minute` : 'Chargement de la fiche…' }}
      </p>
      <p v-if="error" class="detail__status detail__status--error">{{ error }}</p>

      <template v-if="detail">
        <section v-if="detail.description" class="detail__section">
          <h3>Description</h3>
          <p class="detail__description" :class="{ open: descriptionOpen }">{{ detail.description }}</p>
          <button type="button" class="detail__more" @click="descriptionOpen = !descriptionOpen">
            {{ descriptionOpen ? 'Voir moins' : 'Voir plus' }}
          </button>
        </section>

        <section v-if="detail.features.length" class="detail__section">
          <h3>Caractéristiques</h3>
          <div v-for="group in detail.features" :key="group.title" class="features">
            <h4>{{ group.title }}</h4>
            <ul>
              <li v-for="item in group.items" :key="item">{{ item }}</li>
            </ul>
          </div>
        </section>

        <section v-if="detail.energy.length || detail.energy_features.length" class="detail__section">
          <h3>Performance énergétique</h3>
          <div v-for="scale in detail.energy" :key="scale.name" class="energy">
            <span class="energy__rating" :style="{ background: energyColor(scale) }">{{ scale.rating ?? '?' }}</span>
            <div>
              <div class="energy__name">{{ scale.name }}</div>
              <div v-for="value in scale.values" :key="value.label" class="detail__muted">
                {{ value.label }} : {{ value.value }}
              </div>
            </div>
          </div>
          <dl class="rows">
            <template v-for="item in detail.energy_features" :key="item.label">
              <dt>{{ item.label }}</dt>
              <dd>{{ item.value }}</dd>
            </template>
          </dl>
        </section>

        <section v-if="detail.costs.length" class="detail__section">
          <h3>Coûts</h3>
          <dl class="rows">
            <template v-for="cost in detail.costs" :key="cost.label">
              <dt :class="{ sub: cost.label.startsWith('dont ') }">{{ cost.label }}</dt>
              <dd>{{ cost.value }}</dd>
            </template>
          </dl>
        </section>

        <section v-if="comparison" class="detail__section">
          <h3>Prix au m² dans le secteur</h3>
          <div class="comparison">
            <div class="comparison__bar">
              <span class="comparison__marker" :style="{ left: `${comparison.position}%` }"></span>
            </div>
            <div class="comparison__labels">
              <span>{{ decimal.format(comparison.low) }} €</span>
              <strong>{{ decimal.format(comparison.price_per_m2) }} €/m²</strong>
              <span>{{ decimal.format(comparison.high) }} €</span>
            </div>
            <div v-if="comparison.average != null" class="detail__muted">
              Moyenne du secteur : {{ decimal.format(comparison.average) }} €/m²
            </div>
          </div>
        </section>

        <section v-if="detail.schools.length" class="detail__section">
          <h3>Écoles à proximité</h3>
          <ul class="schools">
            <li v-for="school in detail.schools" :key="school.name">
              <span>{{ school.name }}</span>
              <span class="detail__muted">
                {{ [school.level, school.public ? 'public' : 'privé', school.distance].filter(Boolean).join(' · ') }}
              </span>
            </li>
          </ul>
        </section>

        <footer class="detail__footer">
          <div v-if="detail.publisher_type">Proposée par : {{ detail.publisher_type }}</div>
          <div v-if="detail.published_at">Publiée le {{ formatDate(detail.published_at) }}</div>
          <div v-if="detail.updated_at">Mise à jour le {{ formatDate(detail.updated_at) }}</div>
          <div>
            Fiche lue le {{ formatDate(detail.scraped_at) }}
            <button type="button" class="detail__more" :disabled="loading" @click="emit('refresh')">
              Actualiser (1 crédit)
            </button>
          </div>
        </footer>
      </template>
    </div>
  </aside>
</template>

<style scoped>
.detail {
  display: flex;
  flex-direction: column;
  min-height: 0;
  background: #fff;
  border-left: 1px solid #e5e7eb;
}

.detail__header {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  border-bottom: 1px solid #e5e7eb;
}

.detail__external {
  color: #1d4ed8;
  font-size: 0.85rem;
  text-decoration: none;
}

.detail__close {
  margin-left: auto;
  padding: 2px 8px;
  border: 0;
  border-radius: 4px;
  background: transparent;
  font-size: 1rem;
  cursor: pointer;
}

.detail__close:hover {
  background: #f3f4f6;
}

.siblings {
  padding: 8px 12px;
  border-bottom: 1px solid #e5e7eb;
  background: #fff7ed;
}

.siblings__bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  font-size: 0.85rem;
}

.siblings__arrow {
  width: 28px;
  height: 28px;
  border: 1px solid #fed7aa;
  border-radius: 50%;
  background: #fff;
  font-size: 1.1rem;
  line-height: 1;
  cursor: pointer;
}

.siblings__arrow:hover {
  border-color: #ea580c;
}

.siblings__list {
  display: flex;
  gap: 6px;
  margin: 8px 0 0;
  padding: 0 0 4px;
  overflow-x: auto;
  list-style: none;
}

.siblings__card {
  display: flex;
  flex-direction: column;
  gap: 2px;
  width: 150px;
  padding: 6px 8px;
  border: 1px solid #fed7aa;
  border-radius: 6px;
  background: #fff;
  font: inherit;
  font-size: 0.75rem;
  text-align: left;
  cursor: pointer;
}

.siblings__card span {
  overflow: hidden;
  color: #6b7280;
  white-space: nowrap;
  text-overflow: ellipsis;
}

.siblings__card.active {
  border-color: #ea580c;
  box-shadow: 0 0 0 1px #ea580c;
}

.detail__body {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
}

.gallery {
  position: relative;
  aspect-ratio: 4 / 3;
  background: #f3f4f6;
}

.gallery__image {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}

.gallery__nav {
  position: absolute;
  top: 50%;
  transform: translateY(-50%);
  width: 32px;
  height: 32px;
  border: 0;
  border-radius: 50%;
  background: rgb(255 255 255 / 0.85);
  font-size: 1.3rem;
  line-height: 1;
  cursor: pointer;
}

.gallery__nav--prev {
  left: 8px;
}

.gallery__nav--next {
  right: 8px;
}

.gallery__counter {
  position: absolute;
  right: 8px;
  bottom: 8px;
  padding: 2px 8px;
  border-radius: 10px;
  background: rgb(0 0 0 / 0.6);
  color: #fff;
  font-size: 0.75rem;
}

.thumbnails {
  display: flex;
  gap: 4px;
  padding: 6px;
  overflow-x: auto;
}

.thumbnails__item {
  flex: none;
  width: 56px;
  height: 42px;
  padding: 0;
  border: 2px solid transparent;
  border-radius: 4px;
  overflow: hidden;
  cursor: pointer;
}

.thumbnails__item.active {
  border-color: #ea580c;
}

.thumbnails__item img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.detail__section {
  padding: 12px 16px;
  border-bottom: 1px solid #f3f4f6;
  font-size: 0.875rem;
}

.detail__section h3 {
  margin: 0 0 8px;
  font-size: 0.95rem;
}

.detail__price strong {
  font-size: 1.25rem;
}

.detail__price {
  display: flex;
  align-items: baseline;
  gap: 8px;
}

.detail__title {
  margin: 4px 0 2px;
  font-size: 1rem;
}

.detail__place {
  margin-top: 4px;
}

.detail__muted {
  color: #6b7280;
  font-size: 0.8rem;
}

.chips {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  margin: 8px 0 0;
  padding: 0;
  list-style: none;
}

.chips li {
  padding: 2px 8px;
  border-radius: 10px;
  background: #f3f4f6;
  font-size: 0.8rem;
}

.chips--tags li {
  background: #dbeafe;
  color: #1e40af;
}

.detail__link {
  display: inline-block;
  margin-top: 8px;
  color: #1d4ed8;
  text-decoration: none;
}

.detail__status {
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 12px 16px;
  color: #6b7280;
  font-size: 0.85rem;
}

.detail__status--error {
  color: #b91c1c;
}

.spinner {
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

.detail__description {
  margin: 0;
  white-space: pre-line;
  display: -webkit-box;
  -webkit-line-clamp: 6;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.detail__description.open {
  display: block;
}

.detail__more {
  margin-top: 4px;
  padding: 0;
  border: 0;
  background: none;
  color: #1d4ed8;
  font: inherit;
  font-size: 0.8rem;
  cursor: pointer;
}

.detail__more:disabled {
  color: #9ca3af;
  cursor: default;
}

.features h4 {
  margin: 8px 0 2px;
  color: #6b7280;
  font-size: 0.8rem;
  font-weight: 600;
}

.features ul {
  margin: 0;
  padding-left: 18px;
}

.energy {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  margin-bottom: 8px;
}

.energy__rating {
  flex: none;
  width: 32px;
  height: 32px;
  border-radius: 6px;
  color: #fff;
  font-weight: 700;
  line-height: 32px;
  text-align: center;
  text-shadow: 0 0 2px rgb(0 0 0 / 0.5);
}

.energy__name {
  font-weight: 600;
  font-size: 0.8rem;
}

.rows {
  display: grid;
  grid-template-columns: 1fr auto;
  gap: 4px 12px;
  margin: 0;
}

.rows dt {
  color: #374151;
}

.rows dt.sub {
  padding-left: 12px;
  color: #6b7280;
}

.rows dd {
  margin: 0;
  text-align: right;
  font-weight: 600;
}

.comparison__bar {
  position: relative;
  height: 8px;
  border-radius: 4px;
  background: linear-gradient(to right, #86efac, #fde047, #fca5a5);
}

.comparison__marker {
  position: absolute;
  top: -4px;
  width: 4px;
  height: 16px;
  margin-left: -2px;
  border-radius: 2px;
  background: #111827;
}

.comparison__labels {
  display: flex;
  justify-content: space-between;
  margin: 6px 0 4px;
  font-size: 0.8rem;
}

.schools {
  margin: 0;
  padding: 0;
  list-style: none;
}

.schools li {
  display: flex;
  flex-direction: column;
  padding: 4px 0;
}

.detail__footer {
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding: 12px 16px 16px;
  color: #6b7280;
  font-size: 0.8rem;
}
</style>
