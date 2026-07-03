"""
Main Scheduler — запускает crawler → extractor → delivery по расписанию.
Запуск: PYTHONPATH=. .venv/bin/python3 src/main.py
"""

import os
import time
import schedule
from datetime import datetime

from src.crawler.runner import run_crawler
from src.extractor.pipeline import run_extractor
from src.delivery.telegram import send_digest


def run_pipeline(frequency: str):
    """Полный цикл: crawl → extract → (delivery вызывается отдельно по расписанию)."""
    print(f"\n[main] ═══ Pipeline START ({frequency}) — {datetime.utcnow().isoformat()} ═══")
    run_crawler(frequency=frequency)
    run_extractor()
    print(f"[main] ═══ Pipeline DONE ({frequency}) ═══\n")


def run_weekly_digest():
    print(f"[main] Sending weekly digest...")
    count = send_digest(digest_type="new")
    print(f"[main] Weekly digest sent: {count} opportunities")


def run_expiry_check():
    print(f"[main] Checking expiring deadlines...")
    count = send_digest(digest_type="expiring", days_window=14)
    print(f"[main] Expiry digest sent: {count} opportunities")


def main():
    digest_time = os.environ.get("DIGEST_TIME", "09:00")
    digest_day = os.environ.get("DIGEST_DAY", "monday")

    print(f"[main] Grant Scout starting...")
    print(f"[main] Digest: {digest_day} at {digest_time}")

    # Ежедневный краулинг (агрегаторы)
    schedule.every().day.at("06:00").do(run_pipeline, frequency="daily")

    # Еженедельный краулинг (фонды)
    schedule.every().monday.at("05:00").do(run_pipeline, frequency="weekly")

    # Ежемесячный краулинг (прямые сайты фондов)
    schedule.every(30).days.do(run_pipeline, frequency="monthly")

    # Дайджест
    getattr(schedule.every(), digest_day).at(digest_time).do(run_weekly_digest)

    # Алерт об истекающих дедлайнах — каждую пятницу
    schedule.every().friday.at("09:00").do(run_expiry_check)

    # Первый прогон сразу при старте
    print("[main] Running initial pipeline...")
    run_pipeline(frequency="daily")
    run_pipeline(frequency="weekly")
    run_pipeline(frequency="monthly")

    print("[main] Scheduler running. Ctrl+C to stop.")
    while True:
        schedule.run_pending()
        time.sleep(60)


if __name__ == "__main__":
    main()
