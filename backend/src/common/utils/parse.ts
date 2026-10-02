/** Helpers de normalisation des valeurs hétérogènes renvoyées par les API. */

export function num(v: unknown): number | null {
  if (v === null || v === undefined || v === '') return null;
  const n = typeof v === 'number' ? v : parseFloat(String(v).replace(',', '.').replace(/\s/g, ''));
  return Number.isFinite(n) ? n : null;
}

export function int(v: unknown): number | null {
  const n = num(v);
  return n === null ? null : Math.round(n);
}

export function str(v: unknown, maxLength?: number): string | null {
  if (v === null || v === undefined) return null;
  const s = String(v).trim();
  if (s === '' || s.toLowerCase() === 'non connu') return null;
  return maxLength ? s.slice(0, maxLength) : s;
}

/** « 01/09/2000 » ou « 2000-09-01 » ou ISO -> « 2000-09-01 ». */
export function isoDate(v: unknown): string | null {
  const s = str(v);
  if (!s) return null;
  const fr = s.match(/^(\d{2})\/(\d{2})\/(\d{4})/);
  if (fr) return `${fr[3]}-${fr[2]}-${fr[1]}`;
  const iso = s.match(/^(\d{4})-(\d{2})-(\d{2})/);
  return iso ? `${iso[1]}-${iso[2]}-${iso[3]}` : null;
}

export function boolFromFlag(v: unknown): boolean | null {
  if (v === null || v === undefined || v === '') return null;
  if (typeof v === 'boolean') return v;
  const s = String(v).toLowerCase();
  if (['1', 'true', 'oui', 'yes', 'o'].includes(s)) return true;
  if (['0', 'false', 'non', 'no', 'n'].includes(s)) return false;
  return null;
}

/** Majuscules sans accents, pour comparer des libellés d'adresse. */
export function normalizeLabel(s: string): string {
  return s
    .normalize('NFD')
    .replace(/[̀-ͯ]/g, '')
    .toUpperCase()
    .replace(/[^A-Z0-9 ]/g, ' ')
    .replace(/\s+/g, ' ')
    .trim();
}

export function chunk<T>(items: T[], size: number): T[][] {
  const out: T[][] = [];
  for (let i = 0; i < items.length; i += size) out.push(items.slice(i, i + size));
  return out;
}

export function quantile(sorted: number[], q: number): number | null {
  if (sorted.length === 0) return null;
  const pos = (sorted.length - 1) * q;
  const lo = Math.floor(pos);
  const hi = Math.ceil(pos);
  return sorted[lo] + (sorted[hi] - sorted[lo]) * (pos - lo);
}
