"""Parser for web-scraping.dev product pages.

Page structure (verified via DevTools):
  - Name:   h3 (first one)
  - Price:  .price > span
  - Stock:  (inspect the page — look for text like "In stock" or "Out of stock")
"""

from worker.sites.base import SiteParser, ScrapeFailed
from worker.utils.logger import get_logger

log = get_logger("web_scraping_dev")


class WebScrapingDevParser(SiteParser):
    domain = "web-scraping.dev"

    def extract(self, page) -> dict:
        # 1. Name
        name_loc = page.locator("h3").first
        if name_loc.count() == 0:
            raise ScrapeFailed("Name element (h3) not found")
        name = name_loc.inner_text().strip()

        # 2. Price (raw text like "$9.99")
        price_loc = page.locator(".price > span").first
        if price_loc.count() == 0:
            raise ScrapeFailed("Price element (.price > span) not found")
        price_raw = price_loc.inner_text().strip()

        # 3. Stock status — inspect the page to find the right selector.
        #    Common patterns: .availability, .stock, or text containing "stock".
        #    For now we default to True; replace with real extraction below.
        in_stock = True
        stock_loc = page.locator(".availability, .stock, .inventory")
        if stock_loc.count() > 0:
            stock_text = stock_loc.first.inner_text().strip().lower()
            in_stock = "out" not in stock_text and "unavailable" not in stock_text

        # 4. Clean the price: extract currency symbol + numeric value
        if not price_raw:
            raise ScrapeFailed("Price text is empty")
        currency = price_raw[0]          # "$"
        try:
            price = float(price_raw[1:].strip())
        except ValueError:
            raise ScrapeFailed(f"Could not parse price: {price_raw!r}")

        return {
            "name": name,
            "price": price,
            "currency": currency,
            "in_stock": in_stock,
        }