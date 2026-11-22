<script setup>
import TopBar from '@/components/TopBar.vue'
import FilterPanel from '@/components/FilterPanel.vue'
import MapView from '@/components/MapView.vue'
</script>

<template>
  <div class="layout">
    <TopBar class="layout__top" />
    <FilterPanel class="layout__filters" />
    <MapView class="layout__map" />
  </div>
</template>

<style scoped>
.layout {
  display: grid;
  grid-template-columns: 300px 1fr;
  grid-template-rows: 56px 1fr;
  grid-template-areas:
    'top top'
    'filters map';
  height: 100%;
}

.layout__top {
  grid-area: top;
}

.layout__filters {
  grid-area: filters;
}

.layout__map {
  grid-area: map;
}
</style>
