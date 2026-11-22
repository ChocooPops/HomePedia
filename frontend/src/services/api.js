const BASE_URL = import.meta.env.VITE_API_URL ?? '/api'

export async function request(path, options = {}) {
  const response = await fetch(`${BASE_URL}${path}`, {
    headers: { 'Content-Type': 'application/json', ...options.headers },
    ...options,
  })
  if (!response.ok) {
    throw new Error(`API ${response.status} sur ${path}`)
  }
  return response.json()
}
