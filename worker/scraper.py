"""Main scraper entrypoint.

This file ties together:
  - the site parsers (worker/sites/*)
  - the Playwright browser
  - the retry wrapper
  - structured logging

Public function:
    scrape_product(url) -> {"name", "price", "currency", "in_stock"}
"""

from playwright.sync_api import sync_playwright

from worker.sites.base import SiteParser, ScrapeFailed
from worker.sites.web_scraping_dev import WebScrapingDevParser
from worker.utils.logger import get_logger
from worker.utils.retry import retry

log = get_logger("scraper")


# Register every parser here. Adding a new site = import it + add it to this list.
PARSERS: list[SiteParser] = [
    WebScrapingDevParser(),
]


def find_parser(url: str) -> SiteParser:
    """Return the parser whose domain matches the URL."""
    for parser in PARSERS:
        if parser.domain in url:
            return parser
    raise ScrapeFailed(f"No parser registered for URL: {url}")


@retry(times=3, backoff=2.0)
def scrape_product(url: str, timeout_ms: int = 30000) -> dict:
    """Scrape a product page and return structured data.

    Args:
        url: The product page URL.
        timeout_ms: Navigation timeout in milliseconds.

    Returns:
        {"name": str, "price": float, "currency": str, "in_stock": bool}

    Raises:
        ScrapeFailed: if no parser matches, or the parser cannot extract fields.
    """
    parser = find_parser(url)
    log.info(
        "scrape_start",
        extra={"extra": {"url": url, "parser": parser.__class__.__name__}},
    )

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        try:
            page = browser.new_page()
            page.goto(url, timeout=timeout_ms, wait_until="networkidle")
            result = parser.extract(page)
            log.info(
                "scrape_ok",
                extra={"extra": {
                    "url": url,
                    "name": result["name"],
                    "price": result["price"],
                }},
            )
            return result
        finally:
            # Always close the browser, even on failure — otherwise retries leak processes
            browser.close()


if __name__ == "__main__":
    # CLI: python3 -m worker.scraper <url>
    import sys

    url = sys.argv[1] if len(sys.argv) > 1 else "https://web-scraping.dev/product/1"
    print(scrape_product(url))