import { Column } from 'typeorm';

/**
 * Colonnes de traçabilité communes à toutes les tables métier :
 * quelle source a produit la ligne, quand, et jusqu'à quand elle est valide.
 */
export abstract class SourcedEntity {
  @Column({ name: 'source_code', type: 'varchar', length: 48 })
  sourceCode: string;

  @Column({ name: 'fetched_at', type: 'datetime', precision: 3 })
  fetchedAt: Date;

  @Column({ name: 'expires_at', type: 'datetime', precision: 3 })
  expiresAt: Date;
}

/** Transformer DECIMAL -> number (mysql2 renvoie les DECIMAL en chaîne). */
export const decimal = {
  to: (v?: number | null) => v,
  from: (v?: string | null) => (v === null || v === undefined ? null : parseFloat(v)),
};

/** Transformer JSON stocké en LONGTEXT (MariaDB : JSON est un alias de LONGTEXT). */
export const json = {
  to: (v: unknown) => (v === undefined || v === null ? null : JSON.stringify(v)),
  from: (v: string | null) => {
    if (v === null || v === undefined) return null;
    try {
      return typeof v === 'string' ? JSON.parse(v) : v;
    } catch {
      return v;
    }
  },
};

/** TINYINT(1) -> boolean. */
export const bool = {
  to: (v?: boolean | null) => (v === undefined || v === null ? null : v ? 1 : 0),
  from: (v?: number | null) => (v === undefined || v === null ? null : Boolean(v)),
};
