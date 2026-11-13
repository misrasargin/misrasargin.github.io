"""Run the SQL in queries.sql and add the statistics.

For every share (for example "42% of data engineer posts mention Python") we
report a 95% Wilson interval, because some roles have only a few hundred posts.

Two comparisons are tested, each corrected for the number of tests
(Benjamini-Hochberg, 5% false discovery rate):
- what sets a role apart: a skill's share in posts that mention the role
  against its share in all other posts
- what changed: a skill's share in the first twelve months against the last twelve

Output: data/results.js
"""
from __future__ import annotations

import json
import re
import sqlite3
from pathlib import Path

import numpy as np
from scipy.stats import norm

ROOT = Path(__file__).resolve().parents[1]
DB, SQL, OUT = ROOT / "data" / "interim" / "jobs.db", Path(__file__).with_name("queries.sql"), ROOT / "data" / "results.js"
ALPHA = 0.05
MIN_POSTS = 8            # a skill needs this many posts in a role to be listed for it
MIN_DISTINCT = 15        # ... and this many to be called typical of the role
MIN_RATIO = 2.0          # ... and to appear at least twice as often with the role as without it


def load_queries() -> dict[str, str]:
    parts = re.split(r"^-- name: (\w+)\s*$", SQL.read_text(), flags=re.M)
    return {name: body.strip() for name, body in zip(parts[1::2], parts[2::2])}


def wilson(k: int, n: int, z: float = 1.959964) -> tuple[float, float]:
    if n == 0:
        return 0.0, 0.0
    p = k / n
    centre, half = p + z * z / (2 * n), z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return float((centre - half) / (1 + z * z / n)), float((centre + half) / (1 + z * z / n))


def two_proportions(k1: int, n1: int, k2: int, n2: int) -> dict:
    """Difference p2 - p1 with a 95% interval and a two-sided p-value."""
    p1, p2, pool = k1 / n1, k2 / n2, (k1 + k2) / (n1 + n2)
    se0 = np.sqrt(pool * (1 - pool) * (1 / n1 + 1 / n2))
    se1 = np.sqrt(p1 * (1 - p1) / n1 + p2 * (1 - p2) / n2)
    z = (p2 - p1) / se0 if se0 > 0 else 0.0
    return {"diff": p2 - p1, "lo": p2 - p1 - 1.959964 * se1, "hi": p2 - p1 + 1.959964 * se1, "p": float(2 * norm.sf(abs(z)))}


def benjamini_hochberg(p: list[float], alpha: float = ALPHA) -> list[bool]:
    p = np.asarray(p)
    order = np.argsort(p)
    passed = p[order] * len(p) / (np.arange(len(p)) + 1) <= alpha
    k = np.max(np.where(passed)[0]) + 1 if passed.any() else 0
    sig = np.zeros(len(p), bool)
    sig[order[:k]] = True
    return sig.tolist()


def main() -> None:
    db = sqlite3.connect(DB)
    db.row_factory = sqlite3.Row
    q = {name: [dict(r) for r in db.execute(sql)] for name, sql in load_queries().items()}
    tot = q["totals"][0]
    n_all = tot["posts"]
    group = {r["skill"]: r["skill_group"] for r in q["skill_totals"]}
    skill_all = {r["skill"]: r["posts"] for r in q["skill_totals"]}
    role_n = {r["role"]: r["posts"] for r in q["role_totals"]}
    by_role = {(r["role"], r["skill"]): r["posts"] for r in q["skill_by_role"]}
    by_role.update({("Any data role", r["skill"]): r["posts"] for r in q["skill_any_data_role"]})
    junior = {r["role"]: r["junior"] / r["posts"] for r in q["junior_by_role"]}

    # --- skills per role, and what sets each role apart -----------------------------------
    rows = []
    for role, n in role_n.items():
        for skill, total in skill_all.items():
            k = by_role.get((role, skill), 0)
            if k < MIN_POSTS:
                continue
            lo, hi = wilson(k, n)
            test = two_proportions(total - k, n_all - n, k, n)
            other = (total - k) / (n_all - n)
            rows.append({"role": role, "skill": skill, "group": group[skill], "n": k, "share": k / n, "lo": lo, "hi": hi,
                         "share_other": other, "ratio": (k / n) / other if other > 0 else None, "p": test["p"]})
    for r, sig in zip(rows, benjamini_hochberg([r["p"] for r in rows])):
        r["distinct"] = bool(sig and r["n"] >= MIN_DISTINCT and r["ratio"] is not None and r["ratio"] >= MIN_RATIO)
    roles = {
        role: {"posts": n, "junior_share": junior.get(role),
               "skills": sorted(({k: v for k, v in r.items() if k not in ("role", "p")} for r in rows if r["role"] == role),
                                key=lambda r: -r["share"])}
        for role, n in role_n.items()
    }

    # --- what changed between the first and the last year -----------------------------------
    years = q["posts_by_year"][0]
    trends = []
    for r in q["skill_by_year"]:
        if r["first_year"] + r["last_year"] < 30:
            continue
        t = two_proportions(r["first_year"], years["first_year"], r["last_year"], years["last_year"])
        trends.append({"skill": r["skill"], "group": group[r["skill"]], "first": r["first_year"] / years["first_year"],
                       "last": r["last_year"] / years["last_year"], **t})
    for t, sig in zip(trends, benjamini_hochberg([t["p"] for t in trends])):
        t["sig"] = bool(sig)
        del t["p"]
    trends.sort(key=lambda t: -t["diff"])

    months = [r["month"] for r in q["posts_per_month"]]
    posts_m = [r["posts"] for r in q["posts_per_month"]]
    role_m = {role: [0] * len(months) for role in role_n if role != "Any data role"}
    for r in q["role_per_month"]:
        role_m[r["role"]][months.index(r["month"])] = r["posts"]
    track = ["LLMs", "AI agents", "Python", "SQL", "Kubernetes", "TypeScript / JavaScript"]
    skill_m = {s: [0] * len(months) for s in track}
    for r in q["skill_per_month"]:
        if r["skill"] in skill_m:
            skill_m[r["skill"]][months.index(r["month"])] = r["posts"]

    def share(skill: str, role: str = "Any data role") -> float:
        return by_role.get((role, skill), 0) / role_n[role]

    result = {
        "meta": {
            "posts": n_all, "months": tot["months"], "first_month": tot["first_month"], "last_month": tot["last_month"],
            "data_posts": role_n["Any data role"], "data_share": role_n["Any data role"] / n_all,
            "junior_share": tot["junior"] / n_all, "senior_share": tot["senior"] / n_all, "remote_share": tot["remote"] / n_all,
            "first_year_posts": years["first_year"], "last_year_posts": years["last_year"],
            "skills_tracked": len(skill_all), "min_posts": MIN_POSTS, "min_distinct": MIN_DISTINCT, "min_ratio": MIN_RATIO,
        },
        "headline": {
            "python_data": share("Python"), "sql_data": share("SQL"), "sql_analyst": share("SQL", "Data analyst"),
            "llm_first": next(t["first"] for t in trends if t["skill"] == "LLMs"),
            "llm_last": next(t["last"] for t in trends if t["skill"] == "LLMs"),
            "agents_first": next(t["first"] for t in trends if t["skill"] == "AI agents"),
            "agents_last": next(t["last"] for t in trends if t["skill"] == "AI agents"),
            "sql_ratio_analyst": next(r["ratio"] for r in rows if r["role"] == "Data analyst" and r["skill"] == "SQL"),
            "junior_analyst": junior["Data analyst"], "junior_engineer": junior["Data engineer"],
            "r_posts": skill_all["R"],
        },
        "months": months, "posts_per_month": posts_m, "junior_per_month": [r["junior"] for r in q["posts_per_month"]],
        "role_per_month": role_m, "skill_per_month": skill_m, "roles": roles, "trends": trends,
    }
    OUT.write_text("window.JOBS = " + json.dumps(result, separators=(",", ":")) + ";\n")
    print(f"wrote {OUT.name}: {OUT.stat().st_size / 1024:.0f} KB")
    print({k: (round(v, 3) if isinstance(v, float) else v) for k, v in result["meta"].items()})
    for role, d in roles.items():
        top = ", ".join(f"{s['skill']} {s['share']:.0%}" for s in d["skills"][:7])
        apart = ", ".join(f"{s['skill']} x{s['ratio']:.1f}" for s in sorted((s for s in d["skills"] if s["distinct"]), key=lambda s: -s["ratio"])[:6])
        print(f"{role} ({d['posts']}, junior {d['junior_share'] if d['junior_share'] is None else round(d['junior_share'], 3)}): {top}\n    sets it apart: {apart}")
    print("up:  ", ", ".join(f"{t['skill']} {t['first']:.1%}->{t['last']:.1%}{'*' if t['sig'] else ''}" for t in trends[:7]))
    print("down:", ", ".join(f"{t['skill']} {t['first']:.1%}->{t['last']:.1%}{'*' if t['sig'] else ''}" for t in trends[-7:]))


if __name__ == "__main__":
    main()
