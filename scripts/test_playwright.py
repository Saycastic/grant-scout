"""Тест Playwright-краулера на JS-источниках."""
import os, sys
sys.path.insert(0, "/root/grant-scout")

from pathlib import Path
for line in Path("/root/grant-scout/.env").read_text().splitlines():
    line = line.strip()
    if line and not line.startswith("#") and "=" in line:
        k, _, v = line.partition("=")
        os.environ[k.strip()] = v.strip()

from src.crawler.js_fetcher import crawl_source_js
from src.extractor.pipeline import process_page

sources = [
    ("nyfa_opportunities", "https://www.nyfa.org/opportunities/?discipline=Visual+Arts&type=Grant"),
    ("pollock_krasner", "https://pkf.org/apply/"),
    ("creative_capital", "https://creative-capital.org/"),
]

for sid, url in sources:
    print(f"\nCrawling {sid}...")
    result = crawl_source_js(sid, url)
    chars = len(result.get("clean_text", ""))
    print(f"  ok={result['ok']} chars={chars} new={result.get('is_new_content')}")

    if result["ok"] and result.get("page_id"):
        stats = process_page(result["page_id"], url, result["clean_text"])
        print(f"  extract: new={stats['new']} skipped={stats['skipped']} errors={stats['errors']}")
    elif not result["ok"]:
        print(f"  error: {result.get('error')}")
