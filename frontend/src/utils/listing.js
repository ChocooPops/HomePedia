// Mise en forme d'une annonce (AnnonceDto), partagée par la liste et les popups de la carte.

const PROPERTY_LABELS = { appartement: 'Appartement', maison: 'Maison', autre: 'Bien' }

const euros = new Intl.NumberFormat('fr-FR', { style: 'currency', currency: 'EUR', maximumFractionDigits: 0 })
const decimal = new Intl.NumberFormat('fr-FR', { maximumFractionDigits: 1 })

export function formatPrice(listing) {
  if (listing.price == null) return 'Prix non communiqué'
  return listing.transaction_type === 'location' ? `${euros.format(listing.price)} / mois` : euros.format(listing.price)
}

/** « Appartement · 3 pièces · 2 ch. · 66 m² » */
export function describeListing(listing) {
  return [
    PROPERTY_LABELS[listing.property_type] ?? listing.property_type,
    listing.rooms != null && `${listing.rooms} pièce${listing.rooms > 1 ? 's' : ''}`,
    listing.bedrooms != null && `${listing.bedrooms} ch.`,
    listing.surface_m2 != null && `${decimal.format(listing.surface_m2)} m²`,
  ]
    .filter(Boolean)
    .join(' · ')
}

/** « 2ème étage · DPE C » */
export function describeDetails(listing) {
  return [listing.floor_label, listing.energy_class && `DPE ${listing.energy_class}`].filter(Boolean).join(' · ')
}

/** « 49 Rue Joliot Curie, 69005 Lyon 5ème arrondissement » */
export function formatAddress(listing) {
  const street = [listing.street_number, listing.street].filter(Boolean).join(' ')
  const locality = [listing.postal_code, listing.city].filter(Boolean).join(' ')
  return [street, locality].filter(Boolean).join(', ')
}

/** Clé de position : les annonces géocodées au même endroit partagent un marqueur sur la carte. */
export function positionKey(listing) {
  if (listing?.latitude == null || listing?.longitude == null) return null
  return `${listing.latitude.toFixed(5)},${listing.longitude.toFixed(5)}`
}
