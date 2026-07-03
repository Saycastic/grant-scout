import sys
sys.path.insert(0, '/root/grant-scout')

from src.crawler.html_fetcher import crawl_source

tests = [
    ('sustainable_arts', 'https://www.sustainableartsfoundation.org/awards'),
    ('fca', 'https://www.foundationforcontemporaryarts.org/grants/'),
    ('artdeadline', 'https://artdeadline.com/?type=Grant'),
]

for sid, url in tests:
    result = crawl_source(sid, url)
    if result['ok']:
        text = result['clean_text']
        preview = text[:200].replace('\n', ' ')
        print(f"OK   {sid}: {len(text)} chars | new={result['is_new_content']}")
        print(f"     {preview}")
    else:
        print(f"FAIL {sid}: {result['error']}")
    print()
