"""Scrape every tracked product in the database.

Run:
    python3 -m worker.run_checks

Used by:
    - Manual CLI runs
    - GitHub Actions scheduled workflow (.github/workflows/scrape.yml)

One product failing does NOT stop the batch. Every product gets its own
try/except, and the final summary shows successes vs failures.

After the batch, a summary notification is ALWAYS sent (default behavior).
This is a "heartbeat" — it tells you the tool ran, even when nothing changed.
Set NOTIFY_ALWAYS=false in .env to disable.
"""

import os
import sys

from backend.database import init_db, list_products
from worker.alerts import send_alert
from worker.scraper import scrape_and_save
from worker.sites.base import ScrapeFailed
from worker.utils.logger import get_logger

log = get_logger("run_checks")


def send_batch_summary(
    total: int,
    ok: int,
    failed: int,
    changes: dict[str, int],
    product_results: list[dict],
) -> None:
    """Send a single summary notification after the batch.

    Always fires by default. Set NOTIFY_ALWAYS=false in .env to disable.
    """
    notify_always = os.getenv("NOTIFY_ALWAYS", "true").lower() not in ("false", "0", "no")
    if not notify_always:
        log.info("summary_notification_disabled")
        return

    # Separate real changes from no_change
    real_changes = {k: v for k, v in changes.items() if k != "no_change"}

    lines = ["📊 Pricedrop batch check", ""]
    lines.append(f"Total: {total} products")
    lines.append(f"✅ Scraped OK: {ok}")
    lines.append(f"❌ Failed: {failed}")
    lines.append("")

    if not real_changes:
        lines.append("🔍 Changes: none detected (all products unchanged)")
    else:
        lines.append("🔍 Changes detected:")
        for kind, count in sorted(real_changes.items()):
            lines.append(f"  • {kind}: {count}")

    if product_results:
        lines.append("")
        lines.append("Products:")
        for r in product_results:
            if r["status"] == "ok":
                currency = r.get("currency") or ""
                price = r.get("price")
                price_str = f"{currency}{price}" if price is not None else "n/a"
                lines.append(f"  • {r['name']} — {price_str} ({r['change']})")
            else:
                lines.append(f"  • {r['name']} — ❌ {r['error']}")

    body = "\n".join(lines)

    if failed > 0:
        subject = f"[Pricedrop] ⚠️ Batch: {ok}/{total} OK, {failed} FAILED"
    elif real_changes:
        subject = f"[Pricedrop] 🔔 Batch: {ok}/{total} OK, {sum(real_changes.values())} changed"
    else:
        subject = f"[Pricedrop] ✅ Batch: {ok}/{total} OK, no changes"

    send_alert(subject, body)


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
    product_results: list[dict] = []

    for product in products:
        url = product["url"]
        product_id = product["id"]
        fallback_name = product.get("name") or url
        try:
            result = scrape_and_save(url)
            kind = result.get("change", "unknown")
            changes[kind] = changes.get(kind, 0) + 1
            ok += 1
            product_results.append({
                "status": "ok",
                "name": result.get("name") or fallback_name,
                "price": result.get("price"),
                "currency": result.get("currency"),
                "change": kind,
            })
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
            product_results.append({
                "status": "failed",
                "name": fallback_name,
                "error": str(e),
            })
            log.error(
                "batch_item_scrape_failed",
                extra={"extra": {"product_id": product_id, "url": url, "error": str(e)}},
            )
        except Exception as e:
            failed += 1
            product_results.append({
                "status": "failed",
                "name": fallback_name,
                "error": f"{type(e).__name__}: {e}",
            })
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

    send_batch_summary(len(products), ok, failed, changes, product_results)

    if failed == len(products) and len(products) > 0:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())