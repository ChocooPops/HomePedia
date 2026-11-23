from abc import ABC, abstractmethod

from app.modules.annonces.models import ListingDetail, ParsedPage, SearchCriteria


class InvalidCriteria(ValueError):
    """Critères que le site ne sait pas traduire (lieu manquant, type de bien non géré…)."""


class ParseError(ValueError):
    """Page sans annonces lisibles : blocage, page d'erreur ou format du site modifié."""


class ScraperSource(ABC):
    """Interface implémentée par chaque site d'annonces.

    Ajouter un site = une sous-classe qui sait construire l'URL de recherche et lire la page,
    puis son enregistrement dans sources/__init__.py. Le reste (téléchargement, normalisation,
    géocodage, enregistrement) est commun.
    """

    name: str  # identifiant enregistré dans annonces.source
    label: str  # nom affiché (« SeLoger »)

    @abstractmethod
    def build_search_url(self, criteria: SearchCriteria, page: int) -> str:
        """URL de la page `page` (à partir de 1) des résultats.

        Lève InvalidCriteria si impossible, par exemple pour une zone donnée par un code INSEE
        que le site ne sait pas traduire en son propre identifiant de lieu.
        """

    @abstractmethod
    def parse(self, html: str) -> ParsedPage:
        """Annonces d'une page de résultats. Lève ParseError si la page n'est pas exploitable."""

    def parse_detail(self, html: str) -> ListingDetail:
        """Fiche complète depuis la page d'une annonce (facultatif). Lève ParseError si illisible."""
        raise NotImplementedError(f"Fiche détaillée non gérée pour {self.name}")
