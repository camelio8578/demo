from proceeds_navigator.scraper.counties.fresno import FresnoScraper
from proceeds_navigator.scraper.counties.san_diego import SanDiegoScraper
from proceeds_navigator.scraper.counties.sacramento import SacramentoScraper
from proceeds_navigator.scraper.counties.los_angeles import LosAngelesScraper

COUNTY_SCRAPERS: dict[str, type] = {
    "fresno": FresnoScraper,
    "san_diego": SanDiegoScraper,
    "sacramento": SacramentoScraper,
    "los_angeles": LosAngelesScraper,
}

__all__ = [
    "FresnoScraper",
    "SanDiegoScraper",
    "SacramentoScraper",
    "LosAngelesScraper",
    "COUNTY_SCRAPERS",
]
