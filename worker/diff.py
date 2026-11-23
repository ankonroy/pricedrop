"""Change detection: compare new scrape vs previous price.

Pure functions only — no DB, no I/O, no alerts.
That makes this module trivially testable.

Public functions:
    detect_change(prev, new) -> dict              — typed change event
    format_alert(change, product_name, url)       — (subject, body) or None
"""

from typing import Optional


def detect_change(prev: Optional[dict], new: dict) -> dict:
    """Compare previous price record to new scrape result.

    Args:
        prev: {"price", "currency", "in_stock"} or None (first ever scrape)
        new:  {"price", "currency", "in_stock"} (current scrape)

    Returns:
        A change dict with a "kind" field — see module docstring for kinds.
    """
    if prev is None:
        return {"kind": "first_seen"}

    # Currency change makes price comparison meaningless — handle first
    if prev["currency"] != new["currency"]:
        return {
            "kind": "currency_change",
            "old_currency": prev["currency"],
            "new_currency": new["currency"],
            "old_price": prev["price"],
            "new_price": new["price"],
        }

    # Stock transitions
    if prev["in_stock"] and not new["in_stock"]:
        return {"kind": "out_of_stock", "old_price": prev["price"]}
    if not prev["in_stock"] and new["in_stock"]:
        return {"kind": "back_in_stock", "new_price": new["price"]}

    # Price changes (only reached if stock state unchanged)
    if new["price"] < prev["price"]:
        pct = ((new["price"] - prev["price"]) / prev["price"]) * 100
        return {
            "kind": "price_drop",
            "old": prev["price"],
            "new": new["price"],
            "pct": pct,   # negative number, e.g. -37.5
        }
    if new["price"] > prev["price"]:
        pct = ((new["price"] - prev["price"]) / prev["price"]) * 100
        return {
            "kind": "price_rise",
            "old": prev["price"],
            "new": new["price"],
            "pct": pct,   # positive number, e.g. +60.0
        }

    return {"kind": "no_change"}


def format_alert(change: dict, product_name: str, url: str) -> Optional[tuple]:
    """Turn a change event into (subject, body), or None if no alert needed.

    Returning None means "don't alert" — the caller skips sending.
    """
    kind = change["kind"]

    if kind in ("first_seen", "no_change"):
        return None

    if kind == "price_drop":
        subject = f"[Pricedrop] {product_name}: {change['pct']:+.1f}% price drop"
        body = (
            f"Price Drop\n\n"
            f"{product_name}\n"
            f"  {change['old']:.2f} -> {change['new']:.2f} "
            f"({change['pct']:+.1f}%)\n\n"
            f"{url}"
        )
        return subject, body

    if kind == "price_rise":
        subject = f"[Pricedrop] {product_name}: {change['pct']:+.1f}% price rise"
        body = (
            f"Price Rise\n\n"
            f"{product_name}\n"
            f"  {change['old']:.2f} -> {change['new']:.2f} "
            f"({change['pct']:+.1f}%)\n\n"
            f"{url}"
        )
        return subject, body

    if kind == "out_of_stock":
        subject = f"[Pricedrop] {product_name}: out of stock"
        body = (
            f"Out of Stock\n\n"
            f"{product_name}\n"
            f"  Last price: {change['old_price']:.2f}\n\n"
            f"{url}"
        )
        return subject, body

    if kind == "back_in_stock":
        subject = f"[Pricedrop] {product_name}: back in stock"
        body = (
            f"Back in Stock\n\n"
            f"{product_name}\n"
            f"  Current price: {change['new_price']:.2f}\n\n"
            f"{url}"
        )
        return subject, body

    if kind == "currency_change":
        subject = f"[Pricedrop] {product_name}: currency changed"
        body = (
            f"Currency Change\n\n"
            f"{product_name}\n"
            f"  {change['old_currency']}{change['old_price']:.2f} -> "
            f"{change['new_currency']}{change['new_price']:.2f}\n\n"
            f"{url}"
        )
        return subject, body

    return None   # unknown kind — don't alert, caller logs it


def should_alert(change: dict) -> bool:
    """True if the change is worth notifying about."""
    return change["kind"] not in ("first_seen", "no_change")