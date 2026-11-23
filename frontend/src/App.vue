<script setup>
import { computed, ref, shallowRef, watch } from 'vue'
import TopBar from '@/components/TopBar.vue'
import FilterPanel from '@/components/FilterPanel.vue'
import ListingsPanel from '@/components/ListingsPanel.vue'
import ListingDetailPanel from '@/components/ListingDetailPanel.vue'
import MapView from '@/components/MapView.vue'
import { useListings } from '@/composables/useListings'
import { useListingDetail } from '@/composables/useListingDetail'
import { positionKey } from '@/utils/listing'

// Résultat choisi dans la barre de recherche, sur lequel la carte zoome.
const focus = shallowRef(null)

// Vue courante de la carte : { level, bbox, department }
const view = shallowRef(null)
const transactionType = ref('location')
const propertyType = ref('')
const selectedListingId = ref(null)
// Commune dont on affiche les annonces (clic sur la carte ou recherche) : { code, name }
const selectedCommune = shallowRef(null)

const { listings, truncated, sync, loading, error } = useListings(view, selectedCommune, {
  transactionType,
  propertyType,
})

// Fiche complète de l'annonce choisie, affichée à droite.
const detailState = useListingDetail(selectedListingId)
// Résumé de l'annonce choisie, gardé même si elle sort de la liste (déplacement de la carte).
const selectedListing = shallowRef(null)
watch([selectedListingId, listings], ([id, items]) => {
  if (id == null) selectedListing.value = null
  else selectedListing.value = items.find((l) => l.id === id) ?? (selectedListing.value?.id === id ? selectedListing.value : null)
})

// Offres au même endroit que l'offre choisie (même marqueur sur la carte), pour naviguer de l'une à l'autre.
const siblings = computed(() => {
  const key = positionKey(selectedListing.value)
  return key ? listings.value.filter((l) => positionKey(l) === key) : []
})

function onSearchSelect(result) {
  focus.value = result
  selectedCommune.value = result?.kind === 'commune' ? { code: result.code, name: result.name } : null
}
</script>

<template>
  <div class="layout" :class="{ 'layout--detail': selectedListingId != null }">
    <TopBar class="layout__top" @select="onSearchSelect" />
    <aside class="layout__side">
      <FilterPanel v-model:transaction-type="transactionType" v-model:property-type="propertyType" />
      <ListingsPanel
        class="layout__listings"
        :listings="listings"
        :view="view"
        :commune="selectedCommune"
        :loading="loading"
        :error="error"
        :sync="sync"
        :truncated="truncated"
        :selected-id="selectedListingId"
        @select="selectedListingId = $event"
        @clear-commune="selectedCommune = null"
      />
    </aside>
    <MapView
      class="layout__map"
      :focus="focus"
      :listings="listings"
      :selected-listing-id="selectedListingId"
      :selected-commune="selectedCommune"
      @view-change="view = $event"
      @select-listing="selectedListingId = $event"
      @select-commune="selectedCommune = $event"
    />
    <ListingDetailPanel
      v-if="selectedListingId != null"
      class="layout__detail"
      :listing="selectedListing"
      :detail="detailState.detail.value"
      :loading="detailState.loading.value"
      :slow="detailState.slow.value"
      :error="detailState.error.value"
      :siblings="siblings"
      @select="selectedListingId = $event"
      @close="selectedListingId = null"
      @refresh="detailState.refresh()"
    />
  </div>
</template>

<style scoped>
.layout {
  display: grid;
  grid-template-columns: 320px 1fr;
  grid-template-rows: 56px 1fr;
  grid-template-areas:
    'top top'
    'side map';
  height: 100%;
}

/* Fiche d'une annonce ouverte : troisième colonne à droite de la carte. */
.layout--detail {
  grid-template-columns: 320px 1fr 400px;
  grid-template-areas:
    'top top top'
    'side map detail';
}

.layout__top {
  grid-area: top;
}

.layout__side {
  grid-area: side;
  display: flex;
  flex-direction: column;
  min-height: 0;
  background: #fff;
  border-right: 1px solid #e5e7eb;
}

.layout__listings {
  flex: 1;
}

.layout__map {
  grid-area: map;
}

.layout__detail {
  grid-area: detail;
}
</style>
