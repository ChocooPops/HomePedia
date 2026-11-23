"""Registre des sites d'annonces disponibles."""

from app.modules.annonces.sources.base import InvalidCriteria, ParseError, ScraperSource
from app.modules.annonces.sources.seloger import SeLogerSource

SOURCES: dict[str, ScraperSource] = {source.name: source for source in [SeLogerSource()]}

__all__ = ["SOURCES", "InvalidCriteria", "ParseError", "ScraperSource"]
