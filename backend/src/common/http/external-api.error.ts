import { HttpException, HttpStatus } from '@nestjs/common';

/** Erreur normalisée d'un appel à une API externe. */
export class ExternalApiError extends HttpException {
  constructor(
    public readonly sourceCode: string,
    message: string,
    public readonly upstreamStatus?: number,
    public readonly retryable = false,
  ) {
    super(
      { error: 'ExternalApiError', source: sourceCode, upstreamStatus: upstreamStatus ?? null, message },
      HttpStatus.BAD_GATEWAY,
    );
  }
}

export class MissingApiKeyError extends HttpException {
  constructor(
    public readonly sourceCode: string,
    envVar: string,
  ) {
    super(
      { error: 'MissingApiKey', source: sourceCode, message: `Clé API absente : renseigner ${envVar} dans .env` },
      HttpStatus.SERVICE_UNAVAILABLE,
    );
  }
}
