"""
Crawler Runner — обходит все активные источники из Source Registry.
Запуск: python -m src.crawler.runner [--frequency daily|weekly|monthly] [--source source_id]
"""

import argparse
import time
from datetime import datetime

from src.database.db import get_conn
from src.crawler.html_fetcher import crawl_source
from src.crawler.js_fetcher import crawl_source_js
from src.crawler.listing_fetcher import crawl_listing, LISTING_CONFIGS
from src.crawler.artconnect_fetcher import crawl_artconnect
from src.alerts.alert import send_alert


def run_crawler(frequency: str = None, source_id: str = None) -> list[dict]:
    """
    Запускает краулер по всем активным источникам (или одному конкретному).
    frequency: 'daily' | 'weekly' | 'monthly' | None (все)
    source_id: конкретный источник или None (все подходящие)
    """
    conn = get_conn()

    query = "SELECT * FROM sources WHERE status = 'active'"
    params = []

    if source_id:
        query += " AND source_id = ?"
        params.append(source_id)
    elif frequency:
        query += " AND crawl_frequency = ?"
        params.append(frequency)

    sources = conn.execute(query, params).fetchall()
    conn.close()

    print(f"[runner] {datetime.utcnow().isoformat()} — Starting crawl: {len(sources)} sources")

    results = []
    errors = []

    for src in sources:
        sid = src["source_id"]
        url = src["url"]
        ptype = src["parser_type"]

        print(f"[runner] Crawling: {sid} ({ptype}) → {url[:60]}")

        try:
            if ptype == "dynamic_js":
                result = crawl_source_js(sid, url)
            elif ptype == "listing" and sid == "artconnect":
                result = crawl_artconnect()
            elif ptype == "listing" and sid in LISTING_CONFIGS:
                result = crawl_listing(sid, LISTING_CONFIGS[sid])
            else:
                result = crawl_source(sid, url)

            results.append(result)

            if not result["ok"]:
                errors.append({
                    "source_id": sid,
                    "name": src["name"],
                    "error": result.get("error", "unknown"),
                    "url": url,
                })
                print(f"[runner] FAIL {sid}: {result.get('error')}")
            else:
                status = "NEW" if result.get("is_new_content") else "unchanged"
                print(f"[runner] OK   {sid}: {status}")

        except Exception as e:
            err_msg = str(e)
            errors.append({"source_id": sid, "name": src["name"], "error": err_msg, "url": url})
            print(f"[runner] EXCEPTION {sid}: {err_msg}")

        time.sleep(2)  # пауза между запросами

    # Алерт если есть ошибки
    if errors:
        send_alert(errors)

    ok_count = sum(1 for r in results if r.get("ok"))
    new_count = sum(1 for r in results if r.get("is_new_content"))
    print(f"[runner] Done: {ok_count}/{len(sources)} ok, {new_count} new pages, {len(errors)} errors")

    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--frequency", choices=["daily", "weekly", "monthly"], default=None)
    parser.add_argument("--source", default=None, help="Конкретный source_id")
    args = parser.parse_args()

    run_crawler(frequency=args.frequency, source_id=args.source)
