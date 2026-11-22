<script setup>
// TODO: liste des filtres
</script>

<template>
  <aside class="filters">
    <h2 class="filters__title">Filtres</h2>
    <ul class="filters__list">
      <!-- Les filtres viendront ici -->
    </ul>
  </aside>
</template>

<style scoped>
.filters {
  padding: 16px;
  background: #fff;
  border-right: 1px solid #e5e7eb;
  overflow-y: auto;
}

.filters__title {
  margin: 0 0 12px;
  font-size: 1rem;
}

.filters__list {
  list-style: none;
  margin: 0;
  padding: 0;
}
</style>
