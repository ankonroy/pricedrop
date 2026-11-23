from worker.diff import detect_change, format_alert, should_alert

PREV_IN_STOCK = {"price": 15.99, "currency": "$", "in_stock": True}

cases = [
    ("first_seen",    None,                                              {"price": 9.99, "currency": "$", "in_stock": True}),
    ("no_change",     PREV_IN_STOCK,                                     {"price": 15.99, "currency": "$", "in_stock": True}),
    ("price_drop",    PREV_IN_STOCK,                                     {"price": 9.99, "currency": "$", "in_stock": True}),
    ("price_rise",    PREV_IN_STOCK,                                     {"price": 19.99, "currency": "$", "in_stock": True}),
    ("out_of_stock",  PREV_IN_STOCK,                                     {"price": 15.99, "currency": "$", "in_stock": False}),
    ("back_in_stock", {"price": 15.99, "currency": "$", "in_stock": False},{"price": 15.99, "currency": "$", "in_stock": True}),
    ("currency_change", PREV_IN_STOCK,                                   {"price": 1200, "currency": "৳", "in_stock": True}),
]

for expected_kind, prev, new in cases:
    change = detect_change(prev, new)
    status = "✅" if change["kind"] == expected_kind else "❌"
    alert = format_alert(change, "Box of Chocolate Candy", "https://example.com/p/1")
    alert_str = "no alert" if alert is None else f"ALERT: {alert[0]}"
    print(f"{status} {expected_kind:16s} -> kind={change['kind']:16s} | {alert_str}")