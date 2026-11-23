<script setup>
import { computed, onBeforeUnmount, onMounted, ref, shallowRef, watch } from 'vue'
import L from 'leaflet'
import { geoDataService, toFeatureCollection } from '@/services/geoData'
import { describeDetails, describeListing, formatAddress, formatPrice, positionKey } from '@/utils/listing'

const props = defineProps({
  // Résultat de recherche à afficher : { kind, code, name, bbox: [lon_min, lat_min, lon_max, lat_max] }
  focus: { type: Object, default: null },
  // Annonces à placer sur la carte (AnnonceDto avec latitude / longitude)
  listings: { type: Array, default: () => [] },
  selectedListingId: { type: Number, default: null },
  // Commune dont on affiche les annonces : { code, name }, mise en évidence sur la carte
  selectedCommune: { type: Object, default: null },
})

const emit = defineEmits([
  // { level, bbox: [ouest, sud, est, nord], department: { code, name } | null } après chaque déplacement
  'view-change',
  'select-listing',
  // { code, name } de la commune cliquée, ou null quand on reclique la commune déjà choisie
  'select-commune',
])

const FRANCE_VIEW = { center: [46.6, 2.4], zoom: 6 }
const ADDRESS_ZOOM = 16

// Niveau de zoom à partir duquel chaque échelon s'affiche automatiquement.
const DEPARTMENTS_ZOOM = 7
const COMMUNES_ZOOM = 10

const STYLES = {
  active: { color: '#1d4ed8', weight: 1.5, fillColor: '#3b82f6', fillOpacity: 0.2 },
  hover: { weight: 3, fillOpacity: 0.4 },
  // Échelon supérieur laissé en fond quand un échelon plus fin est affiché.
  background: { color: '#6b7280', weight: 1, fillColor: '#9ca3af', fillOpacity: 0.05 },
  // Entité trouvée par la recherche.
  highlight: { color: '#ea580c', weight: 3, fillColor: '#f97316', fillOpacity: 0.25 },
}

const container = ref(null)
const zoom = ref(FRANCE_VIEW.zoom)
const pending = ref(0)
const error = ref(null)
const regionsLoaded = ref(false)
const currentRegion = shallowRef(null)
const currentDepartment = shallowRef(null)
const hovered = shallowRef(null) // { kind, name } de l'entité sous la souris

let map = null
let regionsLayer = null
const departmentLayers = new Map() // code région -> couche de ses départements
const communeLayers = new Map() // code département -> couche de ses communes
let updateId = 0
let highlighted = null // { kind, code } de l'entité trouvée par la recherche
let addressMarker = null

const level = computed(() =>
  zoom.value >= COMMUNES_ZOOM ? 'communes' : zoom.value >= DEPARTMENTS_ZOOM ? 'departments' : 'regions',
)
const levelLabel = computed(
  () => ({ regions: 'Régions', departments: 'Départements', communes: 'Communes' })[level.value],
)
const breadcrumb = computed(() =>
  [currentRegion.value?.name, currentDepartment.value?.name].filter(Boolean),
)

// ------------------------------------------------------------------ //
// Couches
// ------------------------------------------------------------------ //

const KIND_LABELS = { region: 'Région', department: 'Département', commune: 'Commune' }

/**
 * `kind` : region | department | commune (affiché au survol).
 * `zoomOnClick` : zoom minimal appliqué quand on clique une entité. Sans lui, cliquer une commune
 * la choisit (ses annonces s'affichent) ; la recliquer annule ce choix.
 */
function makeLayer(items, kind, zoomOnClick) {
  const layer = L.geoJSON(toFeatureCollection(items), {
    style: styleFn(kind, STYLES.active),
    onEachFeature: (feature, featureLayer) => {
      featureLayer.on({
        mouseover: () => {
          featureLayer.setStyle(STYLES.hover)
          hovered.value = {
            kind: KIND_LABELS[kind],
            name: feature.properties.name,
            hint: kind === 'commune' ? 'Cliquer pour voir ses annonces' : null,
          }
        },
        mouseout: () => {
          layer.resetStyle(featureLayer)
          if (hovered.value?.name === feature.properties.name) hovered.value = null
        },
        click: () => {
          if (zoomOnClick) zoomTo(featureLayer.getBounds(), zoomOnClick)
          else if (kind === 'commune') {
            const { code, name } = feature.properties
            emit('select-commune', props.selectedCommune?.code === code ? null : { code, name })
          }
        },
      })
    },
  })
  layer.kind = kind
  return layer
}

function isHighlighted(kind, feature) {
  const code = feature.properties.code
  return (
    (highlighted?.kind === kind && highlighted.code === code) ||
    (kind === 'commune' && props.selectedCommune?.code === code)
  )
}

/** Style d'une couche : `base` pour toutes les entités, sauf l'entité recherchée mise en évidence. */
function styleFn(kind, base) {
  return (feature) => (isHighlighted(kind, feature) ? { ...base, ...STYLES.highlight } : base)
}

// options.style est relu par resetStyle() au survol : on le garde aligné sur le style visible.
function setLayerStyle(layer, base) {
  layer.options.style = styleFn(layer.kind, base)
  layer.setStyle(layer.options.style)
}

function zoomTo(bounds, minZoom) {
  map.setView(bounds.getCenter(), Math.max(map.getBoundsZoom(bounds), minZoom))
}

/** Codes des entités de `layer` dont l'emprise croise la vue courante. */
function visibleCodes(layer) {
  const view = map.getBounds()
  return layer
    .getLayers()
    .filter((l) => view.intersects(l.getBounds()))
    .map((l) => l.feature.properties.code)
}

/** Affiche les couches de `layers` listées dans `wanted` et retire les autres. */
function syncLayers(layers, wanted) {
  for (const [code, layer] of layers) {
    if (wanted.includes(code)) layer.addTo(map)
    else layer.remove()
  }
}

// ------------------------------------------------------------------ //
// Chargement
// ------------------------------------------------------------------ //

async function track(promise) {
  pending.value++
  try {
    return await promise
  } catch (e) {
    error.value = e.message
    return null
  } finally {
    pending.value--
  }
}

/** Charge (une seule fois) la couche de chaque code manquant dans `layers`. */
async function ensureLayers(layers, codes, fetcher, kind, zoomOnClick) {
  await Promise.all(
    codes
      .filter((code) => !layers.has(code))
      .map(async (code) => {
        const items = await track(fetcher(code))
        if (items && !layers.has(code)) layers.set(code, makeLayer(items, kind, zoomOnClick))
      }),
  )
}

async function loadRegions() {
  error.value = null
  const items = await track(geoDataService.getRegions())
  if (!items) return
  regionsLayer = makeLayer(items, 'region', DEPARTMENTS_ZOOM).addTo(map)
  regionsLoaded.value = true
  update()
}

/** Recalcule ce qui doit être affiché pour le zoom et la zone visibles. */
async function update() {
  if (!regionsLayer) return
  const id = ++updateId
  const isStale = () => id !== updateId
  error.value = null

  // Départements des régions visibles
  const regionCodes = level.value === 'regions' ? [] : visibleCodes(regionsLayer)
  await ensureLayers(departmentLayers, regionCodes, geoDataService.getDepartmentsByRegion, 'department', COMMUNES_ZOOM)
  if (isStale()) return
  syncLayers(departmentLayers, regionCodes)
  render()

  // Le département sous le centre de la carte détermine les annonces à chercher…
  const centerDepartment = level.value === 'regions' ? null : departmentAtCenter(regionCodes)
  emitView(centerDepartment)

  // … et, au niveau communes, les seules communes affichées.
  const departmentCodes = level.value === 'communes' && centerDepartment ? [centerDepartment.code] : []
  await ensureLayers(communeLayers, departmentCodes, geoDataService.getCommunesByDepartment, 'commune')
  if (isStale()) return
  syncLayers(communeLayers, departmentCodes)
  render()
}

/** Styles et ordre d'affichage : l'échelon le plus fin au-dessus et en couleur. */
function render() {
  if (!regionsLayer) return
  setLayerStyle(regionsLayer, level.value === 'regions' ? STYLES.active : STYLES.background)
  for (const layer of departmentLayers.values()) {
    setLayerStyle(layer, level.value === 'departments' ? STYLES.active : STYLES.background)
    if (map.hasLayer(layer)) layer.bringToFront()
  }
  for (const layer of communeLayers.values()) {
    setLayerStyle(layer, STYLES.active)
    if (map.hasLayer(layer)) layer.bringToFront()
  }
  bringHighlightToFront()
  updateBreadcrumb()
}

/**
 * Passe le contour recherché au-dessus de ses voisins, seulement s'il est à l'échelon affiché :
 * une région au premier plan masquerait sinon ses départements (survol, clics).
 */
function bringHighlightToFront() {
  const activeLayers = {
    regions: [regionsLayer],
    departments: [...departmentLayers.values()],
    communes: [...communeLayers.values()],
  }[level.value]
  for (const layer of activeLayers) {
    if (!map.hasLayer(layer)) continue
    layer.eachLayer((l) => isHighlighted(layer.kind, l.feature) && l.bringToFront())
  }
}

function emitView(department) {
  const bounds = map.getBounds()
  emit('view-change', {
    level: level.value,
    bbox: [bounds.getWest(), bounds.getSouth(), bounds.getEast(), bounds.getNorth()],
    department: department ? { code: department.code, name: department.name } : null,
  })
}

// ------------------------------------------------------------------ //
// Annonces
// ------------------------------------------------------------------ //

// Marqueurs HTML (divIcon) dans le pane des marqueurs : contrairement à un canvas superposé,
// ils ne captent pas le survol et les clics destinés aux contours.
let listingsLayer = null
const listingMarkers = new Map() // position "lat,lon" -> { marker, items }

/**
 * Les annonces géocodées à la même position (souvent le centre d'une commune) partagent un marqueur.
 * - une annonce : un clic l'ouvre dans la fiche de droite ;
 * - plusieurs : un clic ouvre la liste des offres de cet endroit, où l'on choisit celle à afficher.
 */
function drawListings() {
  if (!listingsLayer) return
  const openKey = [...listingMarkers].find(([, entry]) => entry.marker.isPopupOpen())?.[0]
  listingsLayer.clearLayers()
  listingMarkers.clear()

  const groups = new Map()
  for (const listing of props.listings) {
    const key = positionKey(listing)
    if (!key) continue
    if (!groups.has(key)) groups.set(key, [])
    groups.get(key).push(listing)
  }

  for (const [key, items] of groups) {
    const marker = L.marker([items[0].latitude, items[0].longitude], { icon: listingIcon(items), riseOnHover: true })
    if (items.length > 1) {
      marker.bindTooltip(`${items.length} offres à cet endroit · cliquer pour choisir`, {
        direction: 'top',
        offset: [0, -14],
      })
      marker.bindPopup(() => listingsPopup(items), {
        maxHeight: 340,
        minWidth: 260,
        autoPanPadding: [40, 40],
        className: 'listing-popup-container',
      })
      // La popup cache l'infobulle, inutile pendant le choix.
      marker.on('popupopen', () => marker.closeTooltip())
    } else {
      marker.bindTooltip(`${formatPrice(items[0])} · ${describeListing(items[0])}`, {
        direction: 'top',
        offset: [0, -10],
      })
      marker.on('click', () => emit('select-listing', items[0].id))
    }
    listingsLayer.addLayer(marker)
    listingMarkers.set(key, { marker, items })
  }
  // Après un rechargement (déplacement de la carte), la popup ouverte le reste.
  if (openKey) listingMarkers.get(openKey)?.marker.openPopup()
}

function listingIcon(items) {
  const selected = items.some((l) => l.id === props.selectedListingId)
  const size = items.length > 1 ? 26 : 16
  return L.divIcon({
    className: `listing-marker${selected ? ' listing-marker--selected' : ''}`,
    html: items.length > 1 ? `<span>${items.length > 99 ? '99+' : items.length}</span>` : '',
    iconSize: [size, size],
  })
}

/**
 * Liste des offres d'un même endroit : chaque ligne ouvre l'offre dans la fiche de droite.
 * Construite en DOM : les textes des annonces ne sont jamais interprétés comme du HTML.
 */
function listingsPopup(items) {
  const element = (tag, className, text) => {
    const node = document.createElement(tag)
    if (className) node.className = className
    if (text) node.textContent = text
    return node
  }
  const root = element('div', 'listing-popup')
  root.append(
    element('div', 'listing-popup__header', `${items.length} offres à cet endroit`),
    element('div', 'listing-popup__muted', formatAddress(items[0])),
  )
  const list = element('div', 'listing-popup__list')
  for (const listing of items) {
    const selected = listing.id === props.selectedListingId
    const row = element('button', `listing-popup__row${selected ? ' listing-popup__row--selected' : ''}`)
    row.type = 'button'
    row.setAttribute('aria-pressed', String(selected))
    const top = element('span', 'listing-popup__top')
    top.append(element('strong', null, formatPrice(listing)), element('span', 'source-badge', listing.source_label))
    row.append(top, element('span', 'listing-popup__facts', describeListing(listing)))
    const details = describeDetails(listing)
    if (details) row.append(element('span', 'listing-popup__muted', details))
    row.addEventListener('click', () => emit('select-listing', listing.id))
    list.append(row)
  }
  root.append(list)
  return root
}

/** Annonce choisie (liste, carte ou fiche) : marqueur mis en évidence et ramené dans la vue. */
function showSelectedListing() {
  for (const { marker, items } of listingMarkers.values()) {
    marker.setIcon(listingIcon(items))
    // Liste d'offres ouverte : la ligne de l'offre choisie suit la sélection.
    if (marker.isPopupOpen()) marker.setPopupContent(listingsPopup(items))
  }
  const entry = [...listingMarkers.values()].find(({ items }) => items.some((l) => l.id === props.selectedListingId))
  if (entry && !map.getBounds().contains(entry.marker.getLatLng())) map.panTo(entry.marker.getLatLng())
}

watch(() => props.listings, drawListings)
watch(() => props.selectedListingId, showSelectedListing)

// ------------------------------------------------------------------ //
// Résultat de recherche
// ------------------------------------------------------------------ //

const FOCUS_MIN_ZOOM = { region: DEPARTMENTS_ZOOM, department: COMMUNES_ZOOM, commune: COMMUNES_ZOOM }

function focusOn(target) {
  addressMarker?.remove()
  addressMarker = null
  highlighted = target && target.kind !== 'address' ? { kind: target.kind, code: target.code } : null

  if (target) {
    const [west, south, east, north] = target.bbox
    if (target.kind === 'address') {
      const icon = L.divIcon({ className: 'search-marker', iconSize: [16, 16] })
      addressMarker = L.marker([south, west], { icon, title: target.name }).addTo(map)
      addressMarker.bindTooltip(target.name, { direction: 'top', offset: [0, -10] })
      map.setView([south, west], ADDRESS_ZOOM)
    } else {
      zoomTo(L.latLngBounds([south, west], [north, east]), FOCUS_MIN_ZOOM[target.kind])
    }
  }
  render()
}

watch(() => props.focus, focusOn)
watch(() => props.selectedCommune, render)

// ------------------------------------------------------------------ //
// Fil d'Ariane : région / département sous le centre de la carte
// ------------------------------------------------------------------ //

function pointInRing([x, y], ring) {
  let inside = false
  for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) {
    const [xi, yi] = ring[i]
    const [xj, yj] = ring[j]
    if (yi > y !== yj > y && x < ((xj - xi) * (y - yi)) / (yj - yi) + xi) inside = !inside
  }
  return inside
}

function featureAt(layer, point) {
  const found = layer?.getLayers().find((l) =>
    l.feature.geometry.coordinates.some(
      ([outer, ...holes]) => pointInRing(point, outer) && !holes.some((h) => pointInRing(point, h)),
    ),
  )
  return found?.feature.properties ?? null
}

function centerPoint() {
  const { lng, lat } = map.getCenter()
  return [lng, lat]
}

/** Département sous le centre de la carte, parmi ceux des régions `regionCodes` déjà chargés. */
function departmentAtCenter(regionCodes) {
  const point = centerPoint()
  for (const code of regionCodes) {
    const department = featureAt(departmentLayers.get(code), point)
    if (department) return department
  }
  return null
}

function updateBreadcrumb() {
  const point = centerPoint()
  const region = level.value === 'regions' ? null : featureAt(regionsLayer, point)
  currentRegion.value = region
  currentDepartment.value =
    region && level.value === 'communes' ? featureAt(departmentLayers.get(region.code), point) : null
}

/** Remonte d'un échelon : des communes vers la région courante, sinon vers la France. */
function goBack() {
  const region =
    level.value === 'communes' &&
    regionsLayer.getLayers().find((l) => l.feature.properties.code === currentRegion.value?.code)
  if (region) {
    const bounds = region.getBounds()
    map.setView(bounds.getCenter(), Math.min(Math.max(map.getBoundsZoom(bounds), DEPARTMENTS_ZOOM), COMMUNES_ZOOM - 1))
  } else {
    map.setView(FRANCE_VIEW.center, FRANCE_VIEW.zoom)
  }
}

// ------------------------------------------------------------------ //

onMounted(() => {
  map = L.map(container.value, { preferCanvas: true, zoomControl: false }).setView(
    FRANCE_VIEW.center,
    FRANCE_VIEW.zoom,
  )
  L.control.zoom({ position: 'bottomright', zoomInTitle: 'Zoomer', zoomOutTitle: 'Dézoomer' }).addTo(map)
  // Esri « Light Gray Canvas » : utilisable sans clé d'API.
  L.tileLayer(
    'https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Light_Gray_Base/MapServer/tile/{z}/{y}/{x}',
    {
      maxZoom: 16,
      attribution: 'Tiles &copy; Esri &mdash; Esri, DeLorme, NAVTEQ',
    },
  ).addTo(map)
  listingsLayer = L.layerGroup().addTo(map)
  drawListings()

  map.on('zoom', () => (zoom.value = map.getZoom()))
  // Une couche retirée pendant un zoom ne déclenche pas de mouseout : on efface le survol.
  map.on('movestart', () => (hovered.value = null))
  map.on('moveend', update)
  // La carte change de largeur quand la fiche d'une annonce s'ouvre ou se ferme : Leaflet doit le savoir.
  resizeObserver = new ResizeObserver(() => map?.invalidateSize())
  resizeObserver.observe(container.value)
  loadRegions()
})

let resizeObserver = null

onBeforeUnmount(() => {
  resizeObserver?.disconnect()
  updateId++
  map?.remove()
  map = null
  listingsLayer = null
})
</script>

<template>
  <div class="map-view">
    <div ref="container" class="map-view__map"></div>

    <div class="map-view__overlay map-view__overlay--top">
      <div v-if="hovered" class="map-view__box map-view__hovered">
        <span class="map-view__kind">{{ hovered.kind }}</span>
        <strong>{{ hovered.name }}</strong>
        <span v-if="hovered.hint" class="map-view__hint">{{ hovered.hint }}</span>
      </div>
      <div v-if="breadcrumb.length" class="map-view__box">
        <button type="button" @click="goBack">← Retour</button>
        <span>{{ breadcrumb.join(' › ') }}</span>
      </div>
      <div v-if="pending" class="map-view__box">Chargement…</div>
      <div v-if="error" class="map-view__box map-view__box--error">
        {{ error }}
        <button v-if="!regionsLoaded" type="button" @click="loadRegions">Réessayer</button>
      </div>
    </div>

    <div class="map-view__overlay map-view__overlay--bottom">
      <div class="map-view__box map-view__zoom">Zoom {{ zoom }} · {{ levelLabel }}</div>
    </div>
  </div>
</template>

<style scoped>
.map-view {
  position: relative;
}

.map-view__map {
  width: 100%;
  height: 100%;
}

.map-view__overlay {
  position: absolute;
  z-index: 1000; /* au-dessus des panes Leaflet */
  display: flex;
  flex-direction: column;
  gap: 8px;
  pointer-events: none;
}

.map-view__overlay--top {
  top: 12px;
  left: 12px;
}

/* À gauche des boutons de zoom Leaflet (bottomright), aligné sur leur bas. */
.map-view__overlay--bottom {
  right: 54px;
  bottom: 26px;
}

.map-view__overlay > * {
  pointer-events: auto;
}

.map-view__box {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 6px 10px;
  background: #fff;
  border-radius: 6px;
  box-shadow: 0 1px 4px rgb(0 0 0 / 0.2);
  font-size: 0.9rem;
}

.map-view__box--error {
  color: #b91c1c;
}

.map-view__kind {
  color: #6b7280;
  font-size: 0.8rem;
  text-transform: uppercase;
  letter-spacing: 0.04em;
}

.map-view__hint {
  color: #6b7280;
  font-size: 0.8rem;
}

.map-view__zoom {
  font-variant-numeric: tabular-nums;
}

.map-view button {
  padding: 4px 8px;
  border: 1px solid #d1d5db;
  border-radius: 4px;
  background: #f9fafb;
  font: inherit;
  cursor: pointer;
}
</style>
