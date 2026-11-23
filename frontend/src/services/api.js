const BASE_URL = import.meta.env.VITE_API_URL ?? '/api'

export async function request(path, options = {}) {
  const response = await fetch(`${BASE_URL}${path}`, {
    headers: { 'Content-Type': 'application/json', ...options.headers },
    ...options,
  })
  if (!response.ok) {
    // L'API explique l'erreur dans `detail` quand elle le peut (site indisponible, annonce introuvable…).
    let detail = null
    try {
      const body = await response.json()
      if (typeof body.detail === 'string') detail = body.detail
    } catch {
      // réponse sans JSON
    }
    throw new Error(detail ?? `API ${response.status} sur ${path}`)
  }
  return response.json()
}
