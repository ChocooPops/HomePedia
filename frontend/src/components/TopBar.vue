<script setup>
import { computed, ref, watch } from 'vue'
import { geoDataService } from '@/services/geoData'

const emit = defineEmits(['select'])

const MIN_LENGTH = 2
const DEBOUNCE_MS = 300
const KIND_LABELS = { region: 'Région', department: 'Département', commune: 'Commune', address: 'Adresse' }

const query = ref('')
const results = ref([])
const open = ref(false)
const active = ref(-1) // index du résultat sélectionné au clavier
const loading = ref(false)
const error = ref(null)

let timer = null
let requestId = 0
let skipNextSearch = false // la saisie remplie par une sélection ne relance pas de recherche

const showEmpty = computed(
  () => !loading.value && !error.value && query.value.trim().length >= MIN_LENGTH && !results.value.length,
)

watch(query, (value) => {
  clearTimeout(timer)
  if (skipNextSearch) {
    skipNextSearch = false
    return
  }
  const q = value.trim()
  requestId++
  error.value = null
  if (q.length < MIN_LENGTH) {
    results.value = []
    loading.value = false
    if (!q) emit('select', null) // recherche effacée : la carte retire la mise en évidence
    return
  }
  loading.value = true
  open.value = true
  timer = setTimeout(() => search(q), DEBOUNCE_MS)
})

async function search(q) {
  const id = requestId
  try {
    const items = await geoDataService.search(q)
    if (id !== requestId) return
    results.value = items
    active.value = items.length ? 0 : -1
  } catch (e) {
    if (id !== requestId) return
    results.value = []
    error.value = e.message
  } finally {
    if (id === requestId) loading.value = false
  }
}

function select(result) {
  if (!result) return
  skipNextSearch = true
  query.value = result.name
  open.value = false
  emit('select', { ...result })
}

function move(step) {
  if (!results.value.length) return
  open.value = true
  active.value = (active.value + step + results.value.length) % results.value.length
}

function onEnter() {
  if (open.value && results.value.length) select(results.value[Math.max(active.value, 0)])
}
</script>

<template>
  <header class="topbar">
    <div class="topbar__brand">
      <img src="/logo.svg" alt="" class="topbar__logo" />
      <span class="topbar__name">HomePedia</span>
    </div>

    <div class="search">
      <input
        v-model="query"
        type="search"
        class="search__input"
        placeholder="Rechercher une région, un département, une commune, une adresse…"
        autocomplete="off"
        role="combobox"
        aria-autocomplete="list"
        aria-controls="search-results"
        :aria-expanded="open"
        @focus="open = results.length > 0"
        @blur="open = false"
        @keydown.down.prevent="move(1)"
        @keydown.up.prevent="move(-1)"
        @keydown.enter.prevent="onEnter"
        @keydown.esc="open = false"
      />

      <ul v-if="open" id="search-results" class="search__results" role="listbox">
        <li v-if="loading && !results.length" class="search__status">Recherche…</li>
        <li v-else-if="error" class="search__status search__status--error">{{ error }}</li>
        <li v-else-if="showEmpty" class="search__status">Aucun résultat</li>
        <li
          v-for="(result, index) in results"
          :key="`${result.kind}-${result.code ?? result.name}-${index}`"
          class="search__result"
          :class="{ 'search__result--active': index === active }"
          role="option"
          :aria-selected="index === active"
          @mousedown.prevent="select(result)"
          @mouseenter="active = index"
        >
          <span class="search__kind" :class="`search__kind--${result.kind}`">{{ KIND_LABELS[result.kind] }}</span>
          <span class="search__text">
            <span class="search__name">{{ result.name }}</span>
            <span v-if="result.context" class="search__context">{{ result.context }}</span>
          </span>
        </li>
      </ul>
    </div>
  </header>
</template>

<style scoped>
.topbar {
  position: relative;
  z-index: 1100; /* la liste des résultats passe au-dessus de la carte Leaflet */
  display: flex;
  align-items: center;
  gap: 24px;
  padding: 0 16px;
  background: #fff;
  border-bottom: 1px solid #e5e7eb;
}

.topbar__brand {
  display: flex;
  align-items: center;
  gap: 8px;
}

.topbar__logo {
  width: 28px;
  height: 28px;
}

.topbar__name {
  font-weight: 600;
  font-size: 1.1rem;
}

.search {
  position: relative;
  flex: 1;
  max-width: 520px;
}

.search__input {
  width: 100%;
  padding: 8px 12px;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  font: inherit;
}

.search__results {
  position: absolute;
  top: calc(100% + 4px);
  left: 0;
  right: 0;
  max-height: 420px;
  margin: 0;
  padding: 4px 0;
  overflow-y: auto;
  list-style: none;
  background: #fff;
  border: 1px solid #e5e7eb;
  border-radius: 6px;
  box-shadow: 0 4px 12px rgb(0 0 0 / 0.15);
}

.search__status {
  padding: 8px 12px;
  color: #6b7280;
  font-size: 0.9rem;
}

.search__status--error {
  color: #b91c1c;
}

.search__result {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 6px 12px;
  cursor: pointer;
}

.search__result--active {
  background: #eff6ff;
}

.search__kind {
  flex: none;
  width: 92px;
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 0.72rem;
  font-weight: 600;
  text-align: center;
  text-transform: uppercase;
  letter-spacing: 0.03em;
  background: #f3f4f6;
  color: #4b5563;
}

.search__kind--address {
  background: #ffedd5;
  color: #9a3412;
}

.search__text {
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.search__name,
.search__context {
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
}

.search__context {
  color: #6b7280;
  font-size: 0.8rem;
}
</style>
