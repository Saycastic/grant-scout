"""
Admin Report — отправляет статистику прогона администратору.
"""

import os
from datetime import datetime, date
from pathlib import Path
from typing import Optional

import httpx

from src.database.db import get_conn

# Load .env
_env_path = Path(__file__).parent.parent.parent / ".env"
if _env_path.exists():
    for _line in _env_path.read_text().splitlines():
        _line = _line.strip()
        if _line and not _line.startswith("#") and "=" in _line:
            _k, _, _v = _line.partition("=")
            os.environ.setdefault(_k.strip(), _v.strip())


def _send(text: str):
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    chat_id = os.environ.get("TELEGRAM_ADMIN_CHAT_ID") or os.environ.get("TELEGRAM_CHAT_ID", "")
    if not token or not chat_id:
        print(text)
        return
    try:
        httpx.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat_id, "text": text, "parse_mode": "HTML"},
            timeout=10,
        )
    except Exception as e:
        print(f"[admin] Failed to send report: {e}")


def send_run_report(crawl_results: list[dict], extractor_stats: dict, llm_stats: dict):
    """
    Отправляет отчёт после каждого полного прогона.
    crawl_results: список результатов от runner
    extractor_stats: {new, skipped, errors}
    llm_stats: от cost_guard.get_today_stats()
    """
    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    today = date.today().isoformat()

    # Источники
    total_sources = len(crawl_results)
    ok_sources = sum(1 for r in crawl_results if r.get("ok"))
    failed_sources = total_sources - ok_sources
    new_pages = sum(1 for r in crawl_results if r.get("is_new_content") or r.get("new", 0) > 0)

    # Сбои
    failures = [r for r in crawl_results if not r.get("ok")]

    # Opportunities в БД за сегодня
    conn = get_conn()
    new_today = conn.execute(
        "SELECT COUNT(*) FROM opportunities WHERE first_seen_at >= ?", (today,)
    ).fetchone()[0]
    total_opps = conn.execute("SELECT COUNT(*) FROM opportunities").fetchone()[0]
    pending_send = conn.execute(
        "SELECT COUNT(*) FROM opportunities WHERE sent_at IS NULL AND opportunity_quality != 'reject'"
    ).fetchone()[0]
    conn.close()

    lines = [
        f"🛠 <b>Grant Scout Report</b> · {now}",
        "",
        f"📡 Sources: {ok_sources}/{total_sources} OK · {new_pages} new pages",
        f"🤖 LLM calls: {llm_stats.get('calls', 0)} · chars: {llm_stats.get('total_chars', 0):,}",
        f"✅ Extracted: {extractor_stats.get('new', 0)} new · {extractor_stats.get('skipped', 0)} skipped",
        f"📦 DB total: {total_opps} opps · {new_today} today · {pending_send} pending send",
    ]

    if failed_sources:
        lines.append("")
        lines.append(f"❌ <b>Failed ({failed_sources}):</b>")
        for r in failures[:5]:
            sid = r.get("source_id", "?")
            err = str(r.get("error", "unknown"))[:60]
            lines.append(f"  • {sid}: {err}")

    _send("\n".join(lines))
    print(f"[admin] Report sent")
