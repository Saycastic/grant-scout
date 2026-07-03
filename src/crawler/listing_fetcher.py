"""
Listing Fetcher — для сайтов-агрегаторов типа artdeadline.com, artconnect.com.
Шаг 1: краулит страницу-листинг, собирает ссылки на отдельные гранты.
Шаг 2: краулит каждую отдельную страницу гранта.
Все страницы сохраняются в raw_pages с привязкой к source_id.
"""

import re
import time
import hashlib
import asyncio
from urllib.parse import urljoin, urlparse
from datetime import datetime

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
        "use_playwright": False,
    },
    "artconnect": {
        "listing_url": "https://www.artconnect.com/opportunities/grant-or-stipend",
        "link_prefix": "https://www.artconnect.com",
        "link_selector": 'a[href^="/opportunity/"]',
        "max_links": 40,
        "use_playwright": True,
        "detail_playwright": True,  # Отдельные страницы тоже через Playwright
    },
}


# ─── HTML listing (artdeadline-style) ────────────────────────────────────────

def _get_links_from_listing(url: str, link_pattern: str, max_links: int = 60) -> list[str]:
    """Загружает листинг и извлекает ссылки по regex паттерну."""
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

    links = list(dict.fromkeys(re.findall(link_pattern, html)))
    print(f"[listing] Found {len(links)} links on {url}")
    return links[:max_links]


# ─── Playwright listing ───────────────────────────────────────────────────────

async def _playwright_get_links(listing_url: str, link_selector: str,
                                 link_prefix: str = "", max_links: int = 40) -> list[str]:
    """Краулит JS-листинг через Playwright, возвращает список URL объявлений."""
    from playwright.async_api import async_playwright

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        try:
            await page.goto(listing_url, wait_until="domcontentloaded", timeout=30000)
            await page.wait_for_timeout(4000)

            # Dismiss cookie banner
            try:
                accept = await page.query_selector('[data-cky-tag="accept-button"], button:has-text("Accept")')
                if accept:
                    await accept.click()
                    await page.wait_for_timeout(800)
            except Exception:
                pass

            anchors = await page.query_selector_all(link_selector)
            hrefs = []
            for a in anchors:
                h = await a.get_attribute("href")
                if h:
                    if h.startswith("http"):
                        hrefs.append(h)
                    elif link_prefix:
                        hrefs.append(link_prefix + h)
            hrefs = list(dict.fromkeys(hrefs))
            print(f"[listing/pw] Found {len(hrefs)} links on {listing_url}")
            return hrefs[:max_links]
        finally:
            await browser.close()


async def _playwright_fetch_page(url: str) -> str:
    """Загружает JS-страницу объявления через Playwright, возвращает текст."""
    from playwright.async_api import async_playwright

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=30000)
            await page.wait_for_timeout(3500)

            # Dismiss cookie banner
            try:
                accept = await page.query_selector('[data-cky-tag="accept-button"], button:has-text("Accept")')
                if accept:
                    await accept.click()
                    await page.wait_for_timeout(500)
            except Exception:
                pass

            text = await page.inner_text("body")
            return text
        except Exception as e:
            print(f"[listing/pw] Error fetching {url}: {e}")
            return ""
        finally:
            await browser.close()


def _save_raw_page(source_id: str, url: str, text: str) -> dict:
    """Сохраняет текст страницы в raw_pages. Возвращает {ok, is_new_content}."""
    if not text.strip():
        return {"ok": False, "error": "empty content"}

    content_hash = hashlib.sha256(text.encode()).hexdigest()
    conn = get_conn()
    try:
        existing = conn.execute(
            "SELECT id, content_hash FROM raw_pages WHERE url = ?", (url,)
        ).fetchone()

        now = datetime.utcnow().isoformat()
        is_new_content = True

        if existing:
            if existing["content_hash"] == content_hash:
                is_new_content = False
                print(f"[listing/pw] No change: {url}")
            else:
                conn.execute(
                    "UPDATE raw_pages SET raw_text=?, content_hash=?, crawled_at=?, "
                    "extracted_at=NULL, extraction_status='pending' WHERE id=?",
                    (text, content_hash, now, existing["id"]),
                )
                conn.commit()
        else:
            conn.execute(
                """INSERT INTO raw_pages
                   (source_id, url, raw_text, content_hash, crawled_at, extraction_status)
                   VALUES (?, ?, ?, ?, ?, 'pending')""",
                (source_id, url, text, content_hash, now),
            )
            conn.commit()

        return {"ok": True, "is_new_content": is_new_content, "url": url}
    except Exception as e:
        print(f"[listing/pw] DB error for {url}: {e}")
        return {"ok": False, "error": str(e)}
    finally:
        conn.close()


# ─── Оркестратор ─────────────────────────────────────────────────────────────

def crawl_listing(source_id: str, config: dict) -> dict:
    """
    Краулит листинг и все страницы грантов.
    Возвращает: {ok, source_id, total, new, errors}
    """
    use_playwright = config.get("use_playwright", False)
    detail_playwright = config.get("detail_playwright", False)
    listing_url = config.get("listing_url")
    max_links = config.get("max_links", 40)

    if not listing_url:
        return {"ok": False, "source_id": source_id, "error": "missing listing_url"}

    # Шаг 1: собираем ссылки с листинга
    if use_playwright:
        links = asyncio.run(_playwright_get_links(
            listing_url,
            link_selector=config.get("link_selector", "a[href*='/opportunity/']"),
            link_prefix=config.get("link_prefix", ""),
            max_links=max_links,
        ))
    else:
        links = _get_links_from_listing(
            listing_url,
            link_pattern=config["link_pattern"],
            max_links=max_links,
        )

    if not links:
        return {"ok": False, "source_id": source_id, "error": "no links found on listing"}

    # Шаг 2: краулим каждую страницу
    total = len(links)
    new_count = 0
    error_count = 0

    for i, link in enumerate(links):
        print(f"[listing] {i+1}/{total} → {link}")
        try:
            if detail_playwright:
                text = asyncio.run(_playwright_fetch_page(link))
                result = _save_raw_page(source_id, link, text)
            else:
                result = crawl_source(source_id, link)

            if result.get("ok") and result.get("is_new_content"):
                new_count += 1
            elif not result.get("ok"):
                error_count += 1
        except Exception as e:
            print(f"[listing] ERROR {link}: {e}")
            error_count += 1

        time.sleep(2.0 if detail_playwright else 1.5)

    print(f"[listing] Done {source_id}: {total} links, {new_count} new, {error_count} errors")
    return {"ok": True, "source_id": source_id, "total": total, "new": new_count, "errors": error_count}
