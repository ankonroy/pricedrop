from worker.alerts import send_alert

if __name__ == "__main__":
    results = send_alert(
        subject="[Pricedrop] Test alert",
        body="Test alert from Pricedrop.\n\nIf you see this on Telegram AND in your email, both channels are ready.",
    )
    print("Results:", results)