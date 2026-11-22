<script setup>
import { ref } from 'vue'

const query = ref('')

function onSearch() {
  // TODO: brancher la recherche
}
</script>

<template>
  <header class="topbar">
    <div class="topbar__brand">
      <img src="/logo.svg" alt="" class="topbar__logo" />
      <span class="topbar__name">HomePedia</span>
    </div>

    <form class="topbar__search" @submit.prevent="onSearch">
      <input v-model="query" type="search" placeholder="Rechercher une commune, une adresse…" />
    </form>
  </header>
</template>

<style scoped>
.topbar {
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

.topbar__search {
  flex: 1;
  max-width: 480px;
}

.topbar__search input {
  width: 100%;
  padding: 8px 12px;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  font: inherit;
}
</style>
