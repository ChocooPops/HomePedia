import { Injectable, Logger } from '@nestjs/common';
import { ConfigService } from '@nestjs/config';
import axios, { AxiosInstance, AxiosRequestConfig, AxiosResponse } from 'axios';
import { ExternalApiError } from './external-api.error';
import { RateLimiter } from './rate-limiter';
import { DEFAULT_RATE_LIMIT, RATE_LIMITS } from './rate-limits';

export interface ExternalRequest extends AxiosRequestConfig {
  /** Code de la source (data_source.code) : sert au rate limiting et aux erreurs. */
  source: string;
  /** Clé de rate limiting si différente de la source (ex. « tabular », partagé par plusieurs sources). */
  limiterKey?: string;
  /** Statuts HTTP considérés comme « pas de donnée » plutôt que comme une erreur. */
  allowStatuses?: number[];
}

const RETRYABLE_STATUSES = new Set([408, 425, 429, 500, 502, 503, 504]);

/**
 * Client HTTP commun à toutes les sources externes :
 * timeout, retries avec backoff exponentiel + jitter (respect de Retry-After),
 * limitation de débit par source, erreurs normalisées.
 */
@Injectable()
export class HttpClientService {
  private readonly logger = new Logger(HttpClientService.name);
  private readonly axios: AxiosInstance;
  private readonly limiters = new Map<string, RateLimiter>();
  private readonly maxRetries: number;

  constructor(config: ConfigService) {
    this.maxRetries = config.get<number>('http.maxRetries', 3);
    this.axios = axios.create({
      timeout: config.get<number>('http.timeoutMs', 20000),
      headers: { 'User-Agent': config.get<string>('http.userAgent'), Accept: 'application/json' },
      maxContentLength: 200 * 1024 * 1024,
      maxRedirects: 5,
      validateStatus: () => true,
    });
  }

  async get<T = any>(url: string, req: ExternalRequest): Promise<T> {
    return (await this.request<T>({ ...req, url, method: 'GET' })).data;
  }

  async post<T = any>(url: string, body: unknown, req: ExternalRequest): Promise<T> {
    return (await this.request<T>({ ...req, url, method: 'POST', data: body })).data;
  }

  async request<T = any>(req: ExternalRequest): Promise<AxiosResponse<T>> {
    const limiter = this.limiterFor(req.limiterKey ?? req.source);
    for (let attempt = 1; ; attempt++) {
      let res: AxiosResponse<T> | undefined;
      let networkError: any;
      try {
        res = await limiter.schedule(() => this.axios.request<T>(req));
      } catch (err) {
        networkError = err;
      }

      if (res && (res.status < 400 || req.allowStatuses?.includes(res.status))) return res;

      const status = res?.status;
      const retryable = networkError ? true : RETRYABLE_STATUSES.has(status!);
      if (!retryable || attempt > this.maxRetries) {
        throw new ExternalApiError(req.source, this.describe(req, res, networkError), status, retryable);
      }
      const delay = this.backoff(attempt, res);
      this.logger.warn(
        `[${req.source}] ${status ?? networkError?.code} sur ${req.url} - tentative ${attempt}/${this.maxRetries}, nouvel essai dans ${delay} ms`,
      );
      await new Promise((r) => setTimeout(r, delay));
    }
  }

  private limiterFor(key: string): RateLimiter {
    let limiter = this.limiters.get(key);
    if (!limiter) {
      limiter = new RateLimiter(RATE_LIMITS[key] ?? DEFAULT_RATE_LIMIT);
      this.limiters.set(key, limiter);
    }
    return limiter;
  }

  private backoff(attempt: number, res?: AxiosResponse): number {
    const retryAfter = res?.headers?.['retry-after'];
    if (retryAfter) {
      const seconds = Number(retryAfter);
      if (!Number.isNaN(seconds)) return Math.min(seconds * 1000, 60000);
    }
    // Quota « par minute » sans Retry-After (ex. Open-Meteo) : attendre la fenêtre suivante.
    if (res?.status === 429) return Math.min(20000 * attempt, 61000);
    const base = 500 * 2 ** (attempt - 1);
    return Math.min(base + Math.floor(Math.random() * 250), 15000);
  }

  private describe(req: ExternalRequest, res?: AxiosResponse, err?: any): string {
    if (err) {
      if (err.code === 'ECONNABORTED' || err.code === 'ETIMEDOUT') return `Timeout sur ${req.url}`;
      return `Erreur réseau sur ${req.url} : ${err.code ?? err.message}`;
    }
    const body = typeof res?.data === 'string' ? res.data : JSON.stringify(res?.data ?? '');
    return `HTTP ${res?.status} sur ${req.url} : ${body.slice(0, 300)}`;
  }
}
