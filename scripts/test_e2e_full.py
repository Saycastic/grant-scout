import sys, os, json
sys.path.insert(0, "/root/grant-scout")

# Загружаем ключи из agent-manager
from pathlib import Path
env_path = Path("/root/.agent-manager/.env")
for line in env_path.read_text().splitlines():
    line = line.strip()
    if line and not line.startswith("#") and "=" in line:
        k, _, v = line.partition("=")
        os.environ.setdefault(k.strip(), v.strip())

# Форсируем прямой Anthropic
os.environ["LLM_API_KEY"] = os.environ.get("ANTHROPIC_API_KEY", "")
os.environ["LLM_PROVIDER"] = "anthropic"
os.environ["LLM_MODEL"] = "claude-haiku-4-5"

from src.crawler.html_fetcher import crawl_source
from src.extractor.pipeline import process_page
from src.delivery.telegram import build_digest
from src.database.db import get_conn

sources = [
    ("sustainable_arts", "https://www.sustainableartsfoundation.org/awards"),
    ("fca", "https://www.foundationforcontemporaryarts.org/grants/"),
    ("artdeadline", "https://artdeadline.com/?type=Grant"),
]

print("=" * 50)
print("STEP 1: CRAWL")
print("=" * 50)
page_ids = []
for sid, url in sources:
    result = crawl_source(sid, url)
    print(f"  {sid}: ok={result['ok']} chars={len(result.get('clean_text',''))} new={result.get('is_new_content')}")
    if result["ok"] and result.get("page_id"):
        page_ids.append((result["page_id"], url, result["clean_text"]))

print()
print("=" * 50)
print("STEP 2: EXTRACT via LLM")
print("=" * 50)
total_new = 0
for page_id, url, text in page_ids:
    print(f"\n  Processing page {page_id} ({url[:50]})...")
    stats = process_page(page_id, url, text)
    print(f"  → processed={stats['processed']} new={stats['new']} skipped={stats['skipped']} errors={stats['errors']}")
    total_new += stats["new"]

print()
print("=" * 50)
print(f"STEP 3: DIGEST ({total_new} new opportunities)")
print("=" * 50)

conn = get_conn()
opps = conn.execute("""
    SELECT * FROM opportunities
    WHERE opportunity_quality != 'reject'
      AND is_visual_art_relevant = 1
    ORDER BY
      CASE opportunity_quality WHEN 'high' THEN 1 WHEN 'medium' THEN 2 ELSE 3 END,
      first_seen_at DESC
    LIMIT 20
""").fetchall()
conn.close()

opps_list = [dict(o) for o in opps]
print(f"  Opportunities in DB: {len(opps_list)}")

messages = build_digest(opps_list, digest_type="new")
print(f"  Messages to send: {len(messages)}")
print()
for i, m in enumerate(messages):
    print(f"--- Telegram Message {i+1} ({len(m)} chars) ---")
    print(m)
    print()
