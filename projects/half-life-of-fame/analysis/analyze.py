"""Half-life of fame: how fast does attention fade after its peak?

For each article we find its biggest day of 2025, measure how far it rose
above its own normal level, and follow the 90 days after.

Measures per event
  half-life      days until the extra views fall to half of the peak's extra views
  back to normal days until views are below twice the level before the event
  shape          does the fade follow a power law (slow, long tail) or an
                 exponential (constant percentage lost per day)?

Then the events are grouped by type (from their one-line Wikidata description)
and compared with bootstrap intervals and a Kruskal-Wallis test.

Output: data/results.js
"""
from __future__ import annotations

import json
import re
from datetime import date, timedelta
from pathlib import Path

import numpy as np
from scipy.stats import kruskal, spearmanr

ROOT = Path(__file__).resolve().parents[1]
RAW, OUT = ROOT / "data" / "raw" / "pageviews.json", ROOT / "data" / "results.js"

YEAR = (date(2025, 1, 1), date(2025, 12, 31))      # the peak must fall in this year
BASE_WINDOW = (60, 8)                              # normal level: median of days 60 to 8 before the peak
FOLLOW = 90                                        # days followed after the peak
MIN_RATIO, MIN_PEAK = 10, 20_000                   # what counts as a spike
FIT_DAYS = 30
N_BOOT = 2000
SEED = 2026

TYPES = [                                          # first match wins
    ("Person who died in 2025", r"\((?:born )?\d{3,4}\s*[–-]\s*2025\)|\(died 2025\)"),
    ("Film", r"\bfilm\b"),
    ("TV series", r"television|\bTV\b|miniseries|web series|anime|streaming series"),
    ("Sports event", r"\bseason\b|championship|tournament|grand prix|super bowl|world cup|olympic|\bfinals?\b|wrestl|pay-per-view|\bedition of\b|football match|\bbowl game|\bdraft\b"),
    ("Living person", r"\(born \d{4}\)|\b(actor|actress|singer|rapper|musician|politician|footballer|player|businessman|businesswoman|"
                      r"wrestler|comedian|model|writer|director|quarterback|cricketer|boxer|driver|journalist|activist|lawyer|"
                      r"entrepreneur|executive|athlete|personality|youtuber|streamer|judge|president|minister|pope|cardinal|bishop)\b"),
]
OTHER = "Other"


def classify(description: str) -> str:
    for name, pattern in TYPES:
        if re.search(pattern, description, re.I):
            return name
    return OTHER


def crossing(excess: np.ndarray, level: float) -> float:
    """First time the series falls to `level`, with straight-line interpolation between days. NaN if never."""
    for t in range(1, len(excess)):
        if excess[t] <= level:
            a, b = excess[t - 1], excess[t]
            return float(t - 1 + (a - level) / (a - b)) if a > b else float(t)
    return float("nan")


def r_squared(x: np.ndarray, y: np.ndarray) -> tuple[float, float]:
    slope, intercept = np.polyfit(x, y, 1)
    resid = y - (slope * x + intercept)
    return float(1 - resid.var() / y.var()), float(slope)


def median_ci(x: np.ndarray, rng) -> tuple[float, float, float]:
    boot = np.median(rng.choice(x, (N_BOOT, len(x))), axis=1)
    return float(np.median(x)), float(np.percentile(boot, 2.5)), float(np.percentile(boot, 97.5))


def main() -> None:
    rng = np.random.default_rng(SEED)
    data = json.loads(RAW.read_text())
    day0 = date.fromisoformat(data["first_day"])
    lo, hi = (YEAR[0] - day0).days, (YEAR[1] - day0).days
    events, skipped = [], {"no data": 0, "always popular": 0, "too small": 0, "missing days": 0}
    for a in data["articles"]:
        v = np.array(a["views"], float)
        v[v < 0] = np.nan
        if np.isnan(v[lo:hi + 1]).all():
            skipped["no data"] += 1
            continue
        peak_day = lo + int(np.nanargmax(v[lo:hi + 1]))
        before = v[peak_day - BASE_WINDOW[0]: peak_day - BASE_WINDOW[1] + 1]
        after = v[peak_day: peak_day + FOLLOW + 1]
        if np.isnan(before).mean() > 0.5 or np.isnan(after).any():
            # a page created during the event has no "before": treat missing days before it as zero views
            if np.isnan(after).any():
                skipped["missing days"] += 1
                continue
            before = np.nan_to_num(before)
        base = max(float(np.nanmedian(before)), 1.0)
        peak = float(v[peak_day])
        if peak < MIN_PEAK:
            skipped["too small"] += 1
            continue
        if peak < MIN_RATIO * base:
            skipped["always popular"] += 1
            continue
        excess = np.maximum(after - base, 0.0)
        half = crossing(excess, excess[0] / 2)
        tenth = crossing(excess, excess[0] / 10)
        back = crossing(after, 2 * base)
        t = np.arange(1, FIT_DAYS + 1)
        e = excess[1:FIT_DAYS + 1]
        ok = e > 0
        fit = None
        if ok.sum() >= 20:
            r2_pow, slope = r_squared(np.log(t[ok]), np.log(e[ok]))
            r2_exp, _ = r_squared(t[ok].astype(float), np.log(e[ok]))
            fit = {"exponent": -slope, "r2_power": r2_pow, "r2_exp": r2_exp}
        window = v[peak_day - 14: peak_day + 61]
        events.append({
            "title": a["title"].replace("_", " "), "description": a["description"], "type": classify(a["description"]),
            "peak_date": (day0 + timedelta(peak_day)).isoformat(), "peak": int(peak), "base": int(round(base)),
            "ratio": peak / base, "half_life": half, "tenth_life": tenth, "back_to_normal": back, "fit": fit,
            "views": [None if np.isnan(x) else int(x) for x in window],
        })

    half_raw = np.array([e["half_life"] for e in events])
    half = np.where(np.isnan(half_raw), FOLLOW, half_raw)          # never halved within 90 days: counted as 90
    back = np.array([e["back_to_normal"] for e in events])
    back_filled = np.where(np.isnan(back), FOLLOW, back)            # not back within 90 days: counted as 90 (a lower bound)
    fits = [e["fit"] for e in events if e["fit"]]
    power_better = float(np.mean([f["r2_power"] > f["r2_exp"] for f in fits]))
    types = {}
    for name in [n for n, _ in TYPES] + [OTHER]:
        m = np.array([e["type"] == name for e in events])
        if m.sum() < 8:
            continue
        ex = np.array([e["fit"]["exponent"] for e in events if e["type"] == name and e["fit"]])
        # typical fade: median over events of extra views as a share of the peak's extra views
        curves = np.array([np.maximum(np.array([x or 0 for x in e["views"][14:75]], float) - e["base"], 0) / max(e["peak"] - e["base"], 1)
                           for e in events if e["type"] == name])
        types[name] = {
            "events": int(m.sum()), "half_life": median_ci(half[m], rng), "back_to_normal": median_ci(back_filled[m], rng),
            "still_elevated_after_90_days": float(np.isnan(back[m]).mean()),
            "exponent": median_ci(ex, rng) if len(ex) >= 8 else None,
            "curve": np.round(np.median(curves, axis=0), 4).tolist(),
        }
    groups = [half[np.array([e["type"] == n for e in events])] for n in types]
    kw = kruskal(*groups)
    groups_back = [back_filled[np.array([e["type"] == n for e in events])] for n in types]
    kw_back = kruskal(*groups_back)
    rho = spearmanr([e["ratio"] for e in events], half)

    result = {
        "meta": {
            "articles": len(data["articles"]), "events": len(events), "skipped": skipped, "follow_days": FOLLOW,
            "min_ratio": MIN_RATIO, "min_peak": MIN_PEAK, "fit_days": FIT_DAYS, "bootstrap": N_BOOT,
            "first_day": data["first_day"], "year": YEAR[0].year,
        },
        "overall": {
            "half_life": median_ci(half, rng), "back_to_normal": median_ci(back_filled, rng),
            "half_life_under_one_day": float((half < 1).mean()), "still_elevated_after_90_days": float(np.isnan(back).mean()),
            "never_halved": int(np.isnan(half_raw).sum()),
            "fitted": len(fits), "power_law_better": power_better,
            "exponent": median_ci(np.array([f["exponent"] for f in fits]), rng),
            "kruskal_half_life": {"statistic": float(kw.statistic), "p": float(kw.pvalue)},
            "kruskal_back": {"statistic": float(kw_back.statistic), "p": float(kw_back.pvalue)},
            "size_vs_half_life": {"rho": float(rho.statistic), "p": float(rho.pvalue)},
        },
        "types": types,
        "events": sorted(events, key=lambda e: -e["peak"]),
    }
    OUT.write_text("window.FAME = " + json.dumps(result, separators=(",", ":")).replace("NaN", "null") + ";\n")
    # a tiny file for the portfolio home page, so it does not have to load every series
    example = max((e for e in events if e["type"] == "Film"), key=lambda e: e["peak"])
    summary = {"events": len(events), "half_life": result["overall"]["half_life"][0], "back_to_normal": result["overall"]["back_to_normal"][0],
               "types": {k: {"half_life": v["half_life"][0], "back_to_normal": v["back_to_normal"][0], "curve": v["curve"]} for k, v in types.items()},
               "example": {"title": example["title"], "views": example["views"]}}
    OUT.with_name("summary.js").write_text("window.FAME_SUMMARY = " + json.dumps(summary, separators=(",", ":")) + ";\n")
    print(f"wrote {OUT.name}: {OUT.stat().st_size / 1024:.0f} KB")
    print(result["meta"])
    o = result["overall"]
    print({k: (np.round(v, 3).tolist() if isinstance(v, (tuple, list, float)) else v) for k, v in o.items()})
    for name, d in types.items():
        print(f"{name:<24} n={d['events']:>3} half-life {d['half_life'][0]:.2f} ({d['half_life'][1]:.2f}-{d['half_life'][2]:.2f}) "
              f"back {d['back_to_normal'][0]:.1f} ({d['back_to_normal'][1]:.1f}-{d['back_to_normal'][2]:.1f}) still up {d['still_elevated_after_90_days']:.0%}")
    for e in result["events"][:8]:
        print(f"  {e['title']:<32} {e['type']:<24} {e['peak_date']} peak {e['peak']:>9,} x{e['ratio']:.0f} half {e['half_life']:.2f} back {e['back_to_normal']}")
    other = [e for e in events if e["type"] == OTHER]
    print("examples of Other:", [(e["title"], e["description"][:40]) for e in other[:25]])


if __name__ == "__main__":
    main()
