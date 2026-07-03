"""
Dry-run test экстрактора — без LLM-вызова, проверяем только пайплайн и парсинг.
"""
import sys
sys.path.insert(0, '/root/grant-scout')

from src.database.db import get_conn
from src.extractor.llm_normalizer import _parse_json, make_canonical_key

# 1. Проверяем что в raw_pages есть данные
conn = get_conn()
pages = conn.execute("SELECT id, source_id, url, length(raw_text) as tlen FROM raw_pages WHERE status_code = 200").fetchall()
print(f"raw_pages in DB: {len(pages)}")
for p in pages:
    print(f"  page {p['id']} | {p['source_id']} | {p['tlen']} chars | {p['url'][:60]}")

# 2. Тест парсинга JSON от LLM (симулируем ответ)
fake_llm_response = '''[
  {
    "title": "Individual Awards 2025",
    "organization": "Sustainable Arts Foundation",
    "grant_type": "award",
    "discipline": ["visual art", "writing"],
    "is_visual_art_relevant": true,
    "is_contemporary_art_relevant": true,
    "applicant_type": ["individual artists", "writers"],
    "eligible_residency": ["USA"],
    "eligible_nationality": [],
    "amount": "$5,000",
    "currency": "USD",
    "deadline": null,
    "deadline_raw": "not specified",
    "application_fee": "",
    "is_paid_opportunity": false,
    "requires_fiscal_sponsor": false,
    "open_to_international_applicants": false,
    "url": "https://www.sustainableartsfoundation.org/awards",
    "source_url": "https://www.sustainableartsfoundation.org/awards",
    "summary_ru": "Фонд Sustainable Arts выдаёт по $5,000 двадцати художникам и писателям с детьми.",
    "why_relevant_ru": "Прямая денежная поддержка для visual artists без ограничений по использованию.",
    "opportunity_quality": "high",
    "confidence": 0.95
  }
]'''

grants = _parse_json(fake_llm_response)
print(f"\nParsed {len(grants)} grants from fake LLM response")
g = grants[0]
print(f"  Title: {g['title']}")
print(f"  Org: {g['organization']}")
print(f"  Amount: {g['amount']}")
print(f"  Quality: {g['opportunity_quality']}")
print(f"  Confidence: {g['confidence']}")

key = make_canonical_key(g['organization'], g['title'], g['deadline'] or '', g['url'])
print(f"  Canonical key: {key}")

# 3. Проверяем что таблица opportunities существует
count = conn.execute("SELECT COUNT(*) FROM opportunities").fetchone()[0]
print(f"\nOpportunities in DB: {count}")
conn.close()

print("\nDry-run OK — pipeline structure is valid.")
