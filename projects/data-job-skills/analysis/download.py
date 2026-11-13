"""Download three years of "Ask HN: Who is hiring?" threads.

Every month Hacker News runs one thread where companies post open jobs, one
comment per company. The threads are public and served by the free HN Search
API (https://hn.algolia.com/api). Only the top-level comments (the job posts)
are kept, without author names.

Output: data/raw/threads.json
"""
from __future__ import annotations

import json
import time
import urllib.request
from pathlib import Path

RAW = Path(__file__).resolve().parents[1] / "data" / "raw"
API = "https://hn.algolia.com/api/v1/"
FIRST, LAST = "2023-11-01", "2026-11-01"        # 36 monthly threads, November 2023 - October 2026


def get(path: str) -> dict:
    with urllib.request.urlopen(API + path, timeout=60) as r:
        return json.load(r)


def main() -> None:
    RAW.mkdir(parents=True, exist_ok=True)
    target = RAW / "threads.json"
    if target.exists():
        print(f"already have {target.name}")
        return
    hits = get("search_by_date?tags=story,author_whoishiring&hitsPerPage=120")["hits"]
    wanted = [h for h in hits if h["title"].startswith("Ask HN: Who is hiring?") and FIRST <= h["created_at"][:10] < LAST]
    threads = []
    for h in wanted:
        item = get(f"items/{h['objectID']}")
        posts = [[c["id"], c["created_at"], c["text"]] for c in item.get("children", []) if c and c.get("text")]
        threads.append({"id": int(h["objectID"]), "title": h["title"], "date": h["created_at"][:10], "posts": posts})
        print(h["title"], len(posts))
        time.sleep(1)                              # be polite to the API
    target.write_text(json.dumps(threads))


if __name__ == "__main__":
    main()
