"""Scrape every tracked product in the database.

Run:
    python3 -m worker.run_checks

Used by:
    - Manual CLI runs
    - GitHub Actions scheduled workflow (.github/workflows/scrape.yml)

One product failing does NOT stop the batch. Every product gets its own
try/except, and the final summary shows successes vs failures.
"""

import sys
from backend.database import init_db, list_products
from worker.scraper import scrape_and_save
from worker.sites.base import ScrapeFailed
from worker.utils.logger import get_logger

log = get_logger("run_checks")


def main() -> int:
    """Run scrape_and_save for every product. Returns exit code."""
    init_db()

    products = list_products()
    if not products:
        log.info("no_products_tracked")
        return 0

    log.info("batch_start", extra={"extra": {"count": len(products)}})

    ok = 0
    failed = 0
    changes: dict[str, int] = {}

    for product in products:
        url = product["url"]
        product_id = product["id"]
        try:
            result = scrape_and_save(url)
            kind = result.get("change", "unknown")
            changes[kind] = changes.get(kind, 0) + 1
            ok += 1
            log.info(
                "batch_item_ok",
                extra={"extra": {
                    "product_id": product_id,
                    "url": url,
                    "price": result["price"],
                    "change": kind,
                }},
            )
        except ScrapeFailed as e:
            failed += 1
            log.error(
                "batch_item_scrape_failed",
                extra={"extra": {"product_id": product_id, "url": url, "error": str(e)}},
            )
        except Exception as e:
            failed += 1
            log.error(
                "batch_item_unexpected_failed",
                extra={"extra": {
                    "product_id": product_id,
                    "url": url,
                    "error": str(e),
                    "error_type": type(e).__name__,
                }},
            )

    log.info(
        "batch_complete",
        extra={"extra": {
            "total": len(products),
            "ok": ok,
            "failed": failed,
            "changes": changes,
        }},
    )

    # Exit non-zero only if EVERY product failed — indicates broken setup
    if failed == len(products) and len(products) > 0:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())