"""Client de l'API HomePedia. Les lectures sont mises en cache ; toute écriture vide le cache."""

import os

import httpx
import streamlit as st

API_URL = os.environ.get("HOMEPEDIA_API_URL", "http://localhost:8000/api").rstrip("/")
INGEST_TOKEN = os.environ.get("INGEST_TOKEN", "")


class ApiError(Exception):
    def __init__(self, status: int, message: str):
        super().__init__(message)
        self.status = status
        self.message = message


def _raise(res: httpx.Response):
    try:
        body = res.json()
        message = body.get("message", res.text)
    except ValueError:
        message = res.text
    if isinstance(message, list):
        message = " ; ".join(str(m) for m in message)
    raise ApiError(res.status_code, str(message))


@st.cache_data(ttl=120, show_spinner=False)
def _get(path: str, params: tuple) -> object:
    try:
        res = httpx.get(f"{API_URL}{path}", params=dict(params), timeout=60)
    except httpx.HTTPError as err:
        raise ApiError(0, f"API injoignable ({API_URL}) : {err}") from err
    if res.status_code >= 400:
        _raise(res)
    return res.json()


def get(path: str, **params):
    """Lecture (GET). Les paramètres à None sont ignorés."""
    return _get(path, tuple(sorted((k, v) for k, v in params.items() if v is not None)))


def try_get(path: str, default=None, **params):
    """Lecture qui renvoie `default` au lieu d'échouer (ressource pas encore collectée)."""
    try:
        return get(path, **params)
    except ApiError:
        return default


def post(path: str, body=None, timeout: float = 900, **params):
    """Écriture (POST) : collecte ou import. Peut durer plusieurs minutes."""
    headers = {"X-Ingest-Token": INGEST_TOKEN} if INGEST_TOKEN else {}
    try:
        res = httpx.post(
            f"{API_URL}{path}", json=body, params={k: v for k, v in params.items() if v is not None}, headers=headers, timeout=timeout
        )
    except httpx.HTTPError as err:
        raise ApiError(0, f"API injoignable ({API_URL}) : {err}") from err
    if res.status_code >= 400:
        _raise(res)
    st.cache_data.clear()
    return res.json()
