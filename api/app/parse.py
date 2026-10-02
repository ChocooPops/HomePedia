"""Helpers de normalisation des valeurs hétérogènes renvoyées par les API."""

import math
import re
import unicodedata
from datetime import UTC, datetime

_FLOAT_PREFIX = re.compile(r"^[+-]?(\d+\.?\d*(?:[eE][+-]?\d+)?|\.\d+(?:[eE][+-]?\d+)?)")


def utcnow() -> datetime:
    """Date courante en UTC, sans fuseau (convention de la base), à la milliseconde."""
    now = datetime.now(UTC).replace(tzinfo=None)
    return now.replace(microsecond=now.microsecond // 1000 * 1000)


def js_round(x: float) -> int:
    """Arrondi « au demi supérieur » (Python arrondit au pair le plus proche)."""
    return math.floor(x + 0.5)


def round_to(n: float, digits: int = 6) -> float:
    f = 10**digits
    return js_round(n * f) / f


def num(v) -> float | None:
    """Nombre tolérant : « 1 234,5 » -> 1234.5, « 12 m² » -> 12, vide -> None."""
    if v is None or v == "" or isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        n = float(v)
    else:
        m = _FLOAT_PREFIX.match(re.sub(r"\s", "", str(v).replace(",", ".", 1)))
        if not m:
            return None
        n = float(m.group(0))
    if not math.isfinite(n):
        return None
    return int(n) if n.is_integer() else n


def int_(v) -> int | None:
    n = num(v)
    return None if n is None else js_round(n)


def str_(v, max_length: int | None = None) -> str | None:
    if v is None:
        return None
    s = (("true" if v else "false") if isinstance(v, bool) else str(v)).strip()
    if s == "" or s.lower() == "non connu":
        return None
    return s[:max_length] if max_length else s


def iso_date(v) -> str | None:
    """« 01/09/2000 » ou « 2000-09-01 » ou ISO -> « 2000-09-01 »."""
    s = str_(v)
    if not s:
        return None
    fr = re.match(r"^(\d{2})/(\d{2})/(\d{4})", s)
    if fr:
        return f"{fr[3]}-{fr[2]}-{fr[1]}"
    iso = re.match(r"^(\d{4})-(\d{2})-(\d{2})", s)
    return f"{iso[1]}-{iso[2]}-{iso[3]}" if iso else None


def parse_datetime(v) -> datetime | None:
    """Date ISO 8601 (avec ou sans fuseau) -> datetime UTC sans fuseau."""
    if isinstance(v, datetime):
        d = v
    elif isinstance(v, str) and v.strip():
        try:
            d = datetime.fromisoformat(v.strip().replace("Z", "+00:00"))
        except ValueError:
            return None
    else:
        return None
    return d.astimezone(UTC).replace(tzinfo=None) if d.tzinfo else d


def bool_from_flag(v) -> bool | None:
    if v is None or v == "":
        return None
    if isinstance(v, bool):
        return v
    s = str(v).lower()
    if s in ("1", "true", "oui", "yes", "o"):
        return True
    if s in ("0", "false", "non", "no", "n"):
        return False
    return None


def normalize_label(s: str) -> str:
    """Majuscules sans accents, pour comparer des libellés d'adresse."""
    s = "".join(c for c in unicodedata.normalize("NFD", s) if not 0x300 <= ord(c) <= 0x36F).upper()
    return re.sub(r"\s+", " ", re.sub(r"[^A-Z0-9 ]", " ", s)).strip()


def chunk(items: list, size: int) -> list[list]:
    return [items[i : i + size] for i in range(0, len(items), size)]


def quantile(sorted_values: list[float], q: float) -> float | None:
    if not sorted_values:
        return None
    pos = (len(sorted_values) - 1) * q
    lo, hi = math.floor(pos), math.ceil(pos)
    return sorted_values[lo] + (sorted_values[hi] - sorted_values[lo]) * (pos - lo)
