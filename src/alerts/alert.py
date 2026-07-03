"""
Alert module — отправляет алерты в Telegram при ошибках краулера.
"""

import os
import httpx
from datetime import datetime


def _get_config():
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "")
    return token, chat_id


def send_telegram(text: str):
    token, chat_id = _get_config()
    if not token or not chat_id:
        print(f"[alert] No Telegram config. Message:\n{text}")
        return

    try:
        httpx.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat_id, "text": text, "parse_mode": "Markdown"},
            timeout=10,
        )
    except Exception as e:
        print(f"[alert] Failed to send Telegram alert: {e}")


def send_alert(errors: list[dict]):
    if not errors:
        return

    lines = [f"*Grant Scout — ошибки краулера* ({datetime.utcnow().strftime('%Y-%m-%d %H:%M')} UTC)\n"]
    for err in errors:
        lines.append(f"• `{err['source_id']}` — {err['error']}")
        lines.append(f"  {err.get('url', '')[:60]}")

    text = "\n".join(lines)
    send_telegram(text)
    print(f"[alert] Sent alert for {len(errors)} errors")
