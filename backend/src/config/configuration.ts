export interface AppConfig {
  port: number;
  db: { host: string; port: number; user: string; password: string; name: string; logging: boolean };
  http: { timeoutMs: number; maxRetries: number; userAgent: string };
  storeRawPayloads: boolean;
  keys: {
    meteoFrance?: string;
    atmoUsername?: string;
    atmoPassword?: string;
    sirene?: string;
    esante?: string;
    insee?: string;
    bdnb?: string;
  };
}

const bool = (v: string | undefined, def: boolean) => (v === undefined || v === '' ? def : ['1', 'true', 'yes'].includes(v.toLowerCase()));
const int = (v: string | undefined, def: number) => (v ? parseInt(v, 10) : def);
const opt = (v: string | undefined) => (v && v.trim() !== '' ? v.trim() : undefined);

export default (): AppConfig => ({
  port: int(process.env.PORT, 3000),
  db: {
    host: process.env.DB_HOST ?? 'localhost',
    port: int(process.env.DB_PORT, 3306),
    user: process.env.DB_USER ?? 'homepedia',
    password: process.env.DB_PASSWORD ?? 'homepedia',
    name: process.env.DB_NAME ?? 'homepedia',
    logging: bool(process.env.DB_LOGGING, false),
  },
  http: {
    timeoutMs: int(process.env.HTTP_TIMEOUT_MS, 20000),
    maxRetries: int(process.env.HTTP_MAX_RETRIES, 3),
    userAgent: process.env.HTTP_USER_AGENT ?? 'HomePedia/0.1 (projet etudiant Epitech)',
  },
  storeRawPayloads: bool(process.env.STORE_RAW_PAYLOADS, true),
  keys: {
    meteoFrance: opt(process.env.METEOFRANCE_API_KEY),
    atmoUsername: opt(process.env.ATMO_USERNAME),
    atmoPassword: opt(process.env.ATMO_PASSWORD),
    sirene: opt(process.env.INSEE_SIRENE_API_KEY),
    esante: opt(process.env.ESANTE_API_KEY),
    insee: opt(process.env.INSEE_API_KEY),
    bdnb: opt(process.env.BDNB_API_KEY),
  },
});
