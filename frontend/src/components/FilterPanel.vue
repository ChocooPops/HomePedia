<script setup>
const transactionType = defineModel('transactionType', { type: String, required: true })
const propertyType = defineModel('propertyType', { type: String, default: '' })

const TRANSACTIONS = [
  { value: 'location', label: 'Louer' },
  { value: 'vente', label: 'Acheter' },
]
const PROPERTY_TYPES = [
  { value: '', label: 'Tous' },
  { value: 'appartement', label: 'Appartement' },
  { value: 'maison', label: 'Maison' },
]
</script>

<template>
  <section class="filters">
    <h2 class="filters__title">Filtres</h2>

    <fieldset class="filters__group">
      <legend>Projet</legend>
      <div class="filters__segmented">
        <label v-for="option in TRANSACTIONS" :key="option.value" :class="{ active: transactionType === option.value }">
          <input v-model="transactionType" type="radio" name="transaction" :value="option.value" />
          {{ option.label }}
        </label>
      </div>
    </fieldset>

    <fieldset class="filters__group">
      <legend>Type de bien</legend>
      <div class="filters__segmented">
        <label v-for="option in PROPERTY_TYPES" :key="option.value" :class="{ active: propertyType === option.value }">
          <input v-model="propertyType" type="radio" name="property-type" :value="option.value" />
          {{ option.label }}
        </label>
      </div>
    </fieldset>
  </section>
</template>

<style scoped>
.filters {
  padding: 16px;
  border-bottom: 1px solid #e5e7eb;
}

.filters__title {
  margin: 0 0 12px;
  font-size: 1rem;
}

.filters__group {
  margin: 0 0 12px;
  padding: 0;
  border: 0;
}

.filters__group:last-child {
  margin-bottom: 0;
}

.filters__group legend {
  margin-bottom: 6px;
  color: #6b7280;
  font-size: 0.8rem;
}

.filters__segmented {
  display: flex;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  overflow: hidden;
}

.filters__segmented label {
  flex: 1;
  padding: 6px 4px;
  font-size: 0.85rem;
  text-align: center;
  cursor: pointer;
  user-select: none;
}

.filters__segmented label + label {
  border-left: 1px solid #d1d5db;
}

.filters__segmented label.active {
  background: #1d4ed8;
  color: #fff;
}

.filters__segmented label:has(input:focus-visible) {
  outline: 2px solid #1d4ed8;
  outline-offset: -2px;
}

.filters__segmented input {
  position: absolute;
  opacity: 0;
  pointer-events: none;
}
</style>
