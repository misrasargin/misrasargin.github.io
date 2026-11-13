"""Download daily Wikipedia page views for articles that were in the news in 2025.

Which articles? No hand-picking: for each month of 2025, the 100 most viewed
English Wikipedia articles (excluding the main page and special pages). For
every one of them, 18 months of daily views by human readers, and a one-line
description from Wikidata that is later used to sort them into types.

Sources: Wikimedia Pageviews API and Wikidata, both free and open (CC0).
The script waits between requests and backs off when asked to.

Output: data/raw/pageviews.json
"""
from __future__ import annotations

import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, timedelta
from pathlib import Path

RAW = Path(__file__).resolve().parents[1] / "data" / "raw"
API = "https://wikimedia.org/api/rest_v1/metrics/pageviews/"
WIKIDATA = "https://www.wikidata.org/w/api.php"
HEADERS = {"User-Agent": "half-life-of-fame portfolio project (https://misrasargin.github.io)"}
FIRST, LAST = date(2024, 10, 1), date(2026, 3, 31)
TOP_PER_MONTH = 100
NOT_ARTICLES = re.compile(r"^(Special|Wikipedia|File|Portal|Help|Category|Template|Talk|User|Draft|MediaWiki|Module|Book):", re.I)


def get(url: str, tries: int = 4) -> dict:
    for attempt in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=HEADERS), timeout=60) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code == 429 and attempt < tries - 1:        # too many requests: wait and try again
                time.sleep(6 * (attempt + 1))
                continue
            raise
    raise RuntimeError(url)


def is_article(title: str) -> bool:
    return title not in ("Main_Page", "-") and not title.startswith(".") and not NOT_ARTICLES.match(title)


def main() -> None:
    RAW.mkdir(parents=True, exist_ok=True)
    target = RAW / "pageviews.json"
    if target.exists():
        print(f"already have {target.name}")
        return
    first_seen: dict[str, str] = {}
    for month in range(1, 13):
        top = get(f"{API}top/en.wikipedia/all-access/2025/{month:02d}/all-days")["items"][0]["articles"]
        for a in [a for a in top if is_article(a["article"])][:TOP_PER_MONTH]:
            first_seen.setdefault(a["article"], f"{month:02d}")
        time.sleep(0.3)
    titles = list(first_seen)
    days = [(FIRST + timedelta(n)).strftime("%Y%m%d") for n in range((LAST - FIRST).days + 1)]
    index = {d: i for i, d in enumerate(days)}

    descriptions: dict[str, str] = {}
    for k in range(0, len(titles), 50):
        q = urllib.parse.urlencode({"action": "wbgetentities", "sites": "enwiki", "titles": "|".join(titles[k:k + 50]),
                                    "props": "descriptions|sitelinks", "sitefilter": "enwiki", "languages": "en", "format": "json"})
        for e in get(f"{WIKIDATA}?{q}").get("entities", {}).values():
            title = e.get("sitelinks", {}).get("enwiki", {}).get("title")
            if title:
                descriptions[title.replace(" ", "_")] = e.get("descriptions", {}).get("en", {}).get("value", "")
        time.sleep(0.5)

    articles = []
    for n, title in enumerate(titles, 1):
        url = f"{API}per-article/en.wikipedia/all-access/user/{urllib.parse.quote(title, safe='')}/daily/{days[0]}/{days[-1]}"
        try:
            items = get(url)["items"]
        except urllib.error.HTTPError as e:
            print(f"skipped {title}: HTTP {e.code}")
            continue
        views = [-1] * len(days)                               # -1 marks a day with no data
        for it in items:
            views[index[it["timestamp"][:8]]] = it["views"]
        articles.append({"title": title, "first_top_month": first_seen[title], "description": descriptions.get(title, ""), "views": views})
        if n % 100 == 0:
            print(f"{n} of {len(titles)}")
        time.sleep(0.25)
    target.write_text(json.dumps({"first_day": FIRST.isoformat(), "n_days": len(days), "articles": articles}))
    print(f"saved {len(articles)} articles")


if __name__ == "__main__":
    main()
