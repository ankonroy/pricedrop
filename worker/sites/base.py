"""Abstract base class for all site parsers.

Every site scraper (web_scraping_dev, daraz, amazon, ...) must inherit
from SiteParser and implement `extract`.
"""

from abc import ABC, abstractmethod


class ScrapeFailed(Exception):
    """Raised when a parser cannot extract required fields.

    The worker treats this as a hard failure — it logs the error, sends
    an alert, and skips the product (rather than silently succeeding
    with None fields, which is the #1 production bug in scrapers).
    """
    pass


class SiteParser(ABC):
    """Contract that every site parser must follow.

    Attributes:
        domain: A string used to match URLs to this parser.
                Example: "web-scraping.dev"

    Methods:
        extract(page) -> dict:
            Given a Playwright page (already loaded), extract and return
            {"name", "price", "currency", "in_stock"}.
            Raise ScrapeFailed if extraction fails.
    """

    domain: str = ""

    @abstractmethod
    def extract(self, page) -> dict:
        """Extract product data from a loaded Playwright page.

        Args:
            page: A playwright.sync_api.Page object, already navigated.

        Returns:
            dict with keys: name, price, currency, in_stock

        Raises:
            ScrapeFailed: if any required field cannot be extracted.
        """
        pass