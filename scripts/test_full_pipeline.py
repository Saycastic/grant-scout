import sys
sys.path.insert(0, '/root/grant-scout')

from src.crawler.html_fetcher import crawl_source
from src.delivery.telegram import build_digest
from datetime import date, timedelta

# 1. Crawl
print("=== CRAWL ===")
sites = [
    ("fca", "https://www.foundationforcontemporaryarts.org/grants/"),
    ("artdeadline", "https://artdeadline.com/?type=Grant"),
]
for sid, url in sites:
    result = crawl_source(sid, url)
    chars = len(result.get("clean_text") or "")
    print(f"  {sid}: ok={result['ok']} chars={chars} new={result.get('is_new_content')}")

# 2. Format digest
print("\n=== FORMAT DIGEST ===")
fake_opps = [
    {
        "id": 1,
        "title": "Grants to Artists",
        "organization": "Foundation for Contemporary Arts",
        "amount": "undisclosed",
        "deadline": (date.today() + timedelta(days=45)).isoformat(),
        "deadline_raw": "October 2025",
        "open_to_international": True,
        "opportunity_quality": "high",
        "url": "https://www.foundationforcontemporaryarts.org/grants/by-application/",
        "summary_ru": "FCA выдаёт гранты художникам без ограничений по дисциплине. Подходит для visual и performing arts.",
        "sent_at": None,
        "is_visual_art_relevant": 1,
    },
    {
        "id": 2,
        "title": "Arte Laguna Prize",
        "organization": "Arte Laguna",
        "amount": "EUR 10,000",
        "deadline": (date.today() + timedelta(days=8)).isoformat(),
        "deadline_raw": "8 days left",
        "open_to_international": True,
        "opportunity_quality": "medium",
        "url": "https://artdeadline.com/ops/arte-laguna-prize/",
        "summary_ru": "Международный приз Arte Laguna. Призовой фонд 10,000 EUR для визуальных художников.",
        "sent_at": None,
        "is_visual_art_relevant": 1,
    },
]

msgs = build_digest(fake_opps, digest_type="new")
for i, m in enumerate(msgs):
    print(f"\n--- Message {i+1} ({len(m)} chars) ---")
    print(m)
