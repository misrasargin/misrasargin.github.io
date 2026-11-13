"""Turn the raw threads into a small SQLite database.

Tables
  posts(post_id, month, month_index, n_chars, junior, senior, remote)
  post_roles(post_id, role)      one row for each role a post mentions
  post_skills(post_id, skill)    one row for each skill a post mentions
  skills(skill, skill_group)

The text itself is not stored: only what was found in it.
Output: data/interim/jobs.db
"""
from __future__ import annotations

import html
import json
import re
import sqlite3
from pathlib import Path

import vocab

ROOT = Path(__file__).resolve().parents[1]
RAW, DB = ROOT / "data" / "raw" / "threads.json", ROOT / "data" / "interim" / "jobs.db"
MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]


def clean(text: str) -> str:
    """HN stores comments as HTML: turn paragraphs into line breaks, drop tags, decode entities."""
    text = re.sub(r"<[^>]+>", " ", text.replace("<p>", "\n"))
    return re.sub(r"[ \t]+", " ", html.unescape(text))


def month_of(title: str) -> str:
    m = re.search(r"\((\w+) (\d{4})\)", title)
    return f"{m.group(2)}-{MONTHS.index(m.group(1)) + 1:02d}"


def main() -> None:
    threads = json.loads(RAW.read_text())
    roles = {k: re.compile(v, re.I) for k, v in vocab.ROLES.items()}
    skills = {k: re.compile(v[1], re.I) for k, v in vocab.SKILLS.items()}
    junior, senior, remote = (re.compile(p, re.I) for p in (vocab.SENIORITY["junior"], vocab.SENIORITY["senior"], vocab.REMOTE))
    months = sorted({month_of(t["title"]) for t in threads})

    DB.parent.mkdir(parents=True, exist_ok=True)
    DB.unlink(missing_ok=True)
    db = sqlite3.connect(DB)
    db.executescript("""
        CREATE TABLE posts (post_id INTEGER PRIMARY KEY, month TEXT, month_index INTEGER, n_chars INTEGER,
                            junior INTEGER, senior INTEGER, remote INTEGER);
        CREATE TABLE post_roles (post_id INTEGER, role TEXT);
        CREATE TABLE post_skills (post_id INTEGER, skill TEXT);
        CREATE TABLE skills (skill TEXT PRIMARY KEY, skill_group TEXT);
        CREATE INDEX idx_roles ON post_roles(role, post_id);
        CREATE INDEX idx_skills ON post_skills(skill, post_id);
    """)
    db.executemany("INSERT INTO skills VALUES (?, ?)", [(k, v[0]) for k, v in vocab.SKILLS.items()])
    seen, short = set(), 0
    for t in threads:
        month = month_of(t["title"])
        for post_id, _, raw in t["posts"]:
            text = clean(raw)
            if post_id in seen:
                continue
            if len(text) < 200:                    # questions and one-line replies, not job posts
                short += 1
                continue
            seen.add(post_id)
            db.execute("INSERT INTO posts VALUES (?, ?, ?, ?, ?, ?, ?)",
                       (post_id, month, months.index(month), len(text),
                        int(bool(junior.search(text))), int(bool(senior.search(text))), int(bool(remote.search(text)))))
            db.executemany("INSERT INTO post_roles VALUES (?, ?)", [(post_id, r) for r, rx in roles.items() if rx.search(text)])
            db.executemany("INSERT INTO post_skills VALUES (?, ?)", [(post_id, s) for s, rx in skills.items() if rx.search(text)])
    db.commit()
    n = db.execute("SELECT COUNT(*) FROM posts").fetchone()[0]
    print(f"{n:,} job posts in {len(months)} months ({months[0]} to {months[-1]}); {short} short comments skipped")
    for role, c in db.execute("SELECT role, COUNT(*) FROM post_roles GROUP BY role ORDER BY 2 DESC"):
        print(f"  {role:<18} {c:>5}")
    db.close()


if __name__ == "__main__":
    main()
