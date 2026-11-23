from app.modules.annonces.models import ListingDetail, ParsedPage, SearchCriteria
from app.modules.annonces.sources.base import ScraperSource
from app.modules.annonces.sources.seloger import detail_parser, parser, url_builder


class SeLogerSource(ScraperSource):
    name = "seloger"
    label = "SeLoger"

    def build_search_url(self, criteria: SearchCriteria, page: int) -> str:
        return url_builder.build_search_url(criteria, page)

    def parse(self, html: str) -> ParsedPage:
        return parser.parse(html)

    def parse_detail(self, html: str) -> ListingDetail:
        return detail_parser.parse_detail(html)
