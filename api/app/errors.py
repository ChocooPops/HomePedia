from http import HTTPStatus


class ApiError(Exception):
    """Erreur HTTP au format uniforme : { statusCode, error, message, ...détails }."""

    def __init__(self, status: int, message, error: str | None = None, **extra):
        super().__init__(message if isinstance(message, str) else str(message))
        self.status = status
        self.message = message
        self.error = error or HTTPStatus(status).phrase
        self.extra = extra

    def body(self) -> dict:
        return {"statusCode": self.status, "error": self.error, "message": self.message, **self.extra}


class BadRequest(ApiError):
    def __init__(self, message, **extra):
        super().__init__(400, message, **extra)


class Unauthorized(ApiError):
    def __init__(self, message, **extra):
        super().__init__(401, message, **extra)


class NotFound(ApiError):
    def __init__(self, message, **extra):
        super().__init__(404, message, **extra)


class Unprocessable(ApiError):
    def __init__(self, message, **extra):
        super().__init__(422, message, **extra)


class ExternalApiError(ApiError):
    """Erreur normalisée d'un appel à une API externe."""

    def __init__(self, source_code: str, message: str, upstream_status: int | None = None, retryable: bool = False):
        super().__init__(502, message, "ExternalApiError", source=source_code, upstreamStatus=upstream_status)
        self.source_code = source_code
        self.upstream_status = upstream_status
        self.retryable = retryable


class MissingApiKeyError(ApiError):
    def __init__(self, source_code: str, env_var: str):
        super().__init__(503, f"Clé API absente : renseigner {env_var} dans .env", "MissingApiKey", source=source_code)
        self.source_code = source_code
