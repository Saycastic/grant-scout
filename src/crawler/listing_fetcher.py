"""
Listing Fetcher — для сайтов-агрегаторов типа artdeadline.com.
Шаг 1: краулит страницу-листинг, собирает ссылки на отдельные гранты.
Шаг 2: краулит каждую отдельную страницу гранта.
Все страницы сохраняются в raw_pages с привязкой к source_id.
"""

import re
import time
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup

from src.database.db import get_conn
from src.crawler.html_fetcher import crawl_source


# Конфиги для известных листингов
LISTING_CONFIGS = {
    "artdeadline": {
        "listing_url": "https://artdeadline.com/?type=Grant",
        "link_pattern": r"https://artdeadline\.com/ops/[^/\"'\s]+/?",
        "max_links": 60,
    },
}


def _get_links_from_listing(url: str, link_pattern: str, max_links: int = 60) -> list[str]:
    """Загружает листинг и извлекает ссылки на отдельные гранты."""
    headers = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }
    try:
        resp = httpx.get(url, headers=headers, timeout=20, follow_redirects=True)
        resp.raise_for_status()
        html = resp.text
    except Exception as e:
        print(f"[listing] Failed to fetch listing {url}: {e}")
        return []

    # Ищем ссылки по паттерну
    links = list(dict.fromkeys(re.findall(link_pattern, html)))  # уникальные, порядок сохранён
    print(f"[listing] Found {len(links)} links on {url}")
    return links[:max_links]


def crawl_listing(source_id: str, config: dict) -> dict:
    """
    Краулит листинг и все страницы грантов.
    Возвращает: {"ok": bool, "total": N, "new": N, "errors": N}
    """
    listing_url = config.get("listing_url")
    link_pattern = config.get("link_pattern")
    max_links = config.get("max_links", 40)

    if not listing_url or not link_pattern:
        return {"ok": False, "error": "missing listing config"}

    links = _get_links_from_listing(listing_url, link_pattern, max_links)
    if not links:
        return {"ok": False, "error": "no links found on listing page"}

    conn = get_conn()
    total = len(links)
    new_count = 0
    error_count = 0

    for i, link in enumerate(links):
        print(f"[listing] {i+1}/{total} → {link}")
        try:
            result = crawl_source(source_id, link)
            if result.get("ok") and result.get("is_new_content"):
                new_count += 1
            elif not result.get("ok"):
                error_count += 1
        except Exception as e:
            print(f"[listing] ERROR {link}: {e}")
            error_count += 1

        time.sleep(1.5)  # вежливая пауза

    conn.close()
    print(f"[listing] Done {source_id}: {total} links, {new_count} new, {error_count} errors")
    return {"ok": True, "total": total, "new": new_count, "errors": error_count}
