"""Multi-channel alerting: Telegram + Gmail.

Credentials come from .env — never hardcoded.
Every channel is independent: one failing does not block the other.

Public function:
    send_alert(subject, body) -> {"telegram": bool, "email": bool}
"""

import os
import smtplib
from email.message import EmailMessage

import requests
from dotenv import load_dotenv

from worker.utils.logger import get_logger

load_dotenv()
log = get_logger("alerts")


def send_telegram(text: str) -> bool:
    """Send a message via the Telegram bot API."""
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        log.warning("telegram_not_configured")
        return False

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    try:
        r = requests.post(
            url,
            json={"chat_id": chat_id, "text": text, "disable_web_page_preview": True},
            timeout=10,
        )
        r.raise_for_status()
        log.info("telegram_sent")
        return True
    except Exception as e:
        log.error("telegram_send_failed", extra={"extra": {"error": str(e)}})
        return False


def send_email(subject: str, body: str) -> bool:
    """Send an email via Gmail SMTP. Supports port 587 (STARTTLS) and 465 (SSL)."""
    host = os.getenv("SMTP_HOST", "smtp.gmail.com")
    port = int(os.getenv("SMTP_PORT", "587"))
    user = os.getenv("SMTP_USER")
    password = os.getenv("SMTP_PASS")
    to_email = os.getenv("ALERT_EMAIL_TO") or user

    if not all([user, password, to_email]):
        log.warning("email_not_configured")
        return False

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = user
    msg["To"] = to_email
    msg.set_content(body)

    try:
        if port == 465:
            with smtplib.SMTP_SSL(host, port, timeout=15) as server:
                server.login(user, password)
                server.send_message(msg)
        else:
            with smtplib.SMTP(host, port, timeout=15) as server:
                server.starttls()
                server.login(user, password)
                server.send_message(msg)
        log.info("email_sent", extra={"extra": {"to": to_email}})
        return True
    except Exception as e:
        log.error("email_send_failed", extra={"extra": {"error": str(e)}})
        return False


def send_alert(subject: str, body: str) -> dict:
    """Send to every configured channel. Returns per-channel success."""
    results = {
        "telegram": send_telegram(body),
        "email": send_email(subject, body),
    }
    log.info("alert_dispatched", extra={"extra": results})
    return results