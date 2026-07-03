import sys, os, json
sys.path.insert(0, "/root/grant-scout")

# Load agent-manager env (has Anthropic key + base_url)
from pathlib import Path
env_path = Path("/root/.agent-manager/.env")
for line in env_path.read_text().splitlines():
    line = line.strip()
    if line and not line.startswith("#") and "=" in line:
        k, _, v = line.partition("=")
        os.environ.setdefault(k.strip(), v.strip())

from src.crawler.html_fetcher import crawl_source
from src.extractor.llm_normalizer import call_llm

# Crawl FCA
print("=== CRAWL: Foundation for Contemporary Arts ===")
result = crawl_source("fca", "https://www.foundationforcontemporaryarts.org/grants/")
print(f"ok={result['ok']} chars={len(result.get('clean_text',''))}")
text = result["clean_text"]
print("Text preview:", text[:300])
print()

# Also crawl ArtDeadline for richer content
print("=== CRAWL: ArtDeadline ===")
result2 = crawl_source("artdeadline", "https://artdeadline.com/?type=Grant")
print(f"ok={result2['ok']} chars={len(result2.get('clean_text',''))}")
print("Text preview:", result2["clean_text"][:400])
print()

# Форсируем прямой Anthropic (ключ уже в env из .agent-manager/.env)
os.environ["LLM_API_KEY"] = os.environ.get("ANTHROPIC_API_KEY", "")
os.environ["LLM_PROVIDER"] = "anthropic"
os.environ["LLM_MODEL"] = "claude-haiku-4-5"

print("=== EXTRACT via LLM: FCA ===")
grants = call_llm(text, "https://www.foundationforcontemporaryarts.org/grants/")
print(f"Grants found: {len(grants)}")
for g in grants:
    print(f"  [{g.get('opportunity_quality','?')}] {g.get('title','?')} | {g.get('amount','?')} | deadline: {g.get('deadline','?')}")
    print(f"    {g.get('summary_ru','')}")
    print()
