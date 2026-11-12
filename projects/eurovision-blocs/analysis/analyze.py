"""Eurovision Conspiracy Board - do countries really vote for their friends?

Pipeline
--------
1. Clean the votes (grand finals, 1975-2023, the "douze points" era).
2. For every vote, measure *bias*: how much more voter A gave song B than the
   rest of Europe gave that same song in that same year. This removes song
   quality from the picture.
3. Permutation test: shuffle who gave which points to a song and see how big
   the bias gets by pure chance. Correct for testing ~1,000 pairs at once
   (Benjamini-Hochberg).
4. Find voting blocs with community detection on the significant pairs.
5. Hold-out check: pairs discovered on 1975-2015 are re-tested on 2016-2023,
   separately for professional juries and for the public televote.

Run:  python analysis/download.py && python analysis/analyze.py
"""
from __future__ import annotations

import json
from pathlib import Path

import networkx as nx
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "votes.csv"
OUT = ROOT / "data" / "results.js"

FIRST_YEAR = 1975      # the 1-8, 10, 12 points system starts here
SPLIT_YEAR = 2016      # jury and televote are published separately from here
MIN_YEARS = 10         # a pair needs this many shared finals to be tested
N_PERM = 5000
ALPHA = 0.05
SEED = 1975

NAMES = {
    "ad": "Andorra", "al": "Albania", "am": "Armenia", "at": "Austria", "au": "Australia",
    "az": "Azerbaijan", "ba": "Bosnia & Herzegovina", "be": "Belgium", "bg": "Bulgaria",
    "by": "Belarus", "ch": "Switzerland", "cs": "Serbia & Montenegro", "cy": "Cyprus",
    "cz": "Czechia", "de": "Germany", "dk": "Denmark", "ee": "Estonia", "es": "Spain",
    "fi": "Finland", "fr": "France", "gb": "United Kingdom", "ge": "Georgia", "gr": "Greece",
    "hr": "Croatia", "hu": "Hungary", "ie": "Ireland", "il": "Israel", "is": "Iceland",
    "it": "Italy", "lt": "Lithuania", "lu": "Luxembourg", "lv": "Latvia", "ma": "Morocco",
    "mc": "Monaco", "md": "Moldova", "me": "Montenegro", "mk": "North Macedonia", "mt": "Malta",
    "nl": "Netherlands", "no": "Norway", "pl": "Poland", "pt": "Portugal", "ro": "Romania",
    "rs": "Serbia", "ru": "Russia", "se": "Sweden", "si": "Slovenia", "sk": "Slovakia",
    "sm": "San Marino", "tr": "Turkey", "ua": "Ukraine", "yu": "Yugoslavia",
}


# --------------------------------------------------------------------------- #
# 1. Clean
# --------------------------------------------------------------------------- #
def load_votes() -> pd.DataFrame:
    v = pd.read_csv(RAW)
    v = v[(v["round"] == "final") & (v["year"] >= FIRST_YEAR)]
    v = v[v["from_country_id"] != "wld"]              # 2023 "rest of the world" vote
    v = v[v["from_country_id"] != v["to_country_id"]]  # nobody votes for themselves
    v = v.rename(columns={"from_country_id": "voter", "to_country_id": "song"})
    v = v[["year", "voter", "song", "total_points", "tele_points", "jury_points"]]
    assert not v.duplicated(["year", "voter", "song"]).any(), "duplicate votes"
    unknown = set(v["voter"]) | set(v["song"])
    assert unknown <= set(NAMES), f"unmapped country ids: {unknown - set(NAMES)}"
    # From 2016 a country gives two sets of points (jury + public), so the
    # maximum to one song is 24 instead of 12. Put everything on a 0-1 scale.
    v["max_points"] = np.where(v["year"] >= SPLIT_YEAR, 24, 12)
    assert (v["total_points"] <= v["max_points"]).all()
    v["score"] = v["total_points"] / v["max_points"]
    return v.reset_index(drop=True)


# --------------------------------------------------------------------------- #
# 2. Bias = my points to the song minus everyone else's average for that song
# --------------------------------------------------------------------------- #
def add_bias(v: pd.DataFrame, col: str = "score", out: str = "bias") -> pd.DataFrame:
    g = v.groupby(["year", "song"])[col]
    total, n = g.transform("sum"), g.transform("count")
    v[out] = v[col] - (total - v[col]) / (n - 1)
    return v


def pair_table(v: pd.DataFrame, col: str = "bias") -> pd.DataFrame:
    p = v.groupby(["voter", "song"])[col].agg(["mean", "count"]).reset_index()
    return p.rename(columns={"mean": "bias", "count": "years"})


# --------------------------------------------------------------------------- #
# 3. Permutation test
# --------------------------------------------------------------------------- #
def permutation_test(v: pd.DataFrame, pairs: pd.DataFrame, rng: np.random.Generator):
    """Null hypothesis: *who* the voter is does not matter.

    Within one (year, song) the points are shuffled between the voters, the
    bias is recomputed, and every pair's average bias is stored. Repeating
    this N_PERM times gives each pair its own chance distribution.
    """
    key = {(a, b): i for i, (a, b) in enumerate(zip(pairs["voter"], pairs["song"]))}
    sums = np.zeros((N_PERM, len(pairs)))
    for _, grp in v.groupby(["year", "song"]):
        idx = np.array([key.get((a, b), -1) for a, b in zip(grp["voter"], grp["song"])])
        scores = grp["score"].to_numpy()
        n = len(scores)
        shuffled = rng.permuted(np.tile(scores, (N_PERM, 1)), axis=1)
        bias = shuffled - (scores.sum() - shuffled) / (n - 1)
        keep = idx >= 0
        sums[:, idx[keep]] += bias[:, keep]
    null = sums / pairs["years"].to_numpy()
    obs = pairs["bias"].to_numpy()
    p = (1 + (null >= obs).sum(axis=0)) / (N_PERM + 1)
    return p, null


def benjamini_hochberg(p: np.ndarray, alpha: float) -> np.ndarray:
    order = np.argsort(p)
    ranked = p[order] * len(p) / (np.arange(len(p)) + 1)
    passed = ranked <= alpha
    k = np.max(np.where(passed)[0]) + 1 if passed.any() else 0
    sig = np.zeros(len(p), dtype=bool)
    sig[order[:k]] = True
    return sig


def test_pairs(v: pd.DataFrame, rng: np.random.Generator):
    pairs = pair_table(v)
    pairs = pairs[pairs["years"] >= MIN_YEARS].reset_index(drop=True)
    pairs["p"], null = permutation_test(v, pairs, rng)
    pairs["significant"] = benjamini_hochberg(pairs["p"].to_numpy(), ALPHA)
    return pairs, null


# --------------------------------------------------------------------------- #
# 4. Blocs
# --------------------------------------------------------------------------- #
def find_blocs(pairs: pd.DataFrame):
    sig = pairs[pairs["significant"]]
    lookup = {(a, b): x for a, b, x in zip(pairs["voter"], pairs["song"], pairs["bias"])}
    g = nx.Graph()
    for a, b, x in zip(sig["voter"], sig["song"], sig["bias"]):
        back = max(lookup.get((b, a), 0.0), 0.0)
        g.add_edge(a, b, weight=(x + back) / 2)   # stronger when it goes both ways
    blocs = nx.community.louvain_communities(g, weight="weight", seed=SEED)
    blocs = sorted(blocs, key=len, reverse=True)
    modularity = nx.community.modularity(g, blocs, weight="weight")
    return g, blocs, modularity


# --------------------------------------------------------------------------- #
# 5. Hold-out: discovered before 2016, re-tested after, jury vs public
# --------------------------------------------------------------------------- #
def holdout(v: pd.DataFrame, rng: np.random.Generator) -> dict:
    train, test = v[v["year"] < SPLIT_YEAR].copy(), v[v["year"] >= SPLIT_YEAR].copy()
    found, _ = test_pairs(add_bias(train), rng)
    friends = set(zip(found.loc[found["significant"], "voter"], found.loc[found["significant"], "song"]))

    test["tele"], test["jury"] = test["tele_points"] / 12, test["jury_points"] / 12
    test = add_bias(add_bias(test, "tele", "tele_bias"), "jury", "jury_bias")
    test["friend"] = [(a, b) in friends for a, b in zip(test["voter"], test["song"])]
    per_pair = test.groupby(["voter", "song", "friend"])[["tele_bias", "jury_bias"]].mean().reset_index()
    fr = per_pair[per_pair["friend"]]

    def ci(x: np.ndarray) -> list[float]:
        boot = rng.choice(x, (4000, len(x))).mean(axis=1)
        return [float(x.mean()), float(np.percentile(boot, 2.5)), float(np.percentile(boot, 97.5))]

    diff = (fr["tele_bias"] - fr["jury_bias"]).to_numpy()
    return {
        "train_pairs_found": len(friends),
        "friend_pairs_seen_again": int(len(fr)),
        "other_pairs": int((~per_pair["friend"]).sum()),
        "friends_tele": ci(fr["tele_bias"].to_numpy() * 12),
        "friends_jury": ci(fr["jury_bias"].to_numpy() * 12),
        "tele_minus_jury": ci(diff * 12),
        "others_tele": ci(per_pair.loc[~per_pair["friend"], "tele_bias"].to_numpy() * 12),
        "others_jury": ci(per_pair.loc[~per_pair["friend"], "jury_bias"].to_numpy() * 12),
        "share_still_positive_tele": float((fr["tele_bias"] > 0).mean()),
        "share_still_positive_jury": float((fr["jury_bias"] > 0).mean()),
    }


# --------------------------------------------------------------------------- #
def main() -> None:
    rng = np.random.default_rng(SEED)
    v = add_bias(load_votes())
    pairs, null = test_pairs(v, rng)

    # How many "friendships" would we announce if we skipped the correction?
    thresholds = np.percentile(null, 95, axis=0)
    false_alarms = (null > thresholds).sum(axis=1)
    naive = int((pairs["p"] < ALPHA).sum())

    # Is favouritism returned?  bias(A->B) vs bias(B->A)
    wide = pairs.set_index(["voter", "song"])["bias"]
    both = [(wide[a, b], wide[b, a]) for a, b in wide.index if a < b and (b, a) in wide.index]
    reciprocity = float(np.corrcoef(np.array(both).T)[0, 1])

    g, blocs, modularity = find_blocs(pairs)
    bloc_of = {c: i for i, members in enumerate(blocs) for c in members}
    hold = holdout(v, rng)

    pts = lambda x: round(float(x) * 12, 2)   # report bias in classic 12-point units
    active = v.groupby("voter")["year"].agg(["min", "max", "nunique"])
    result = {
        "meta": {
            "years": [int(v["year"].min()), int(v["year"].max())],
            "finals": int(v["year"].nunique()),
            "votes": int(len(v)),
            "countries": int(len(set(v["voter"]) | set(v["song"]))),
            "pairs_tested": int(len(pairs)),
            "min_years": MIN_YEARS,
            "permutations": N_PERM,
            "alpha": ALPHA,
            "naive_significant": naive,
            "expected_by_chance": round(float(false_alarms.mean()), 1),
            "chance_max": int(false_alarms.max()),
            "bh_significant": int(pairs["significant"].sum()),
            "reciprocity_r": round(reciprocity, 3),
            "reciprocal_pairs": len(both),
            "modularity": round(float(modularity), 3),
        },
        "chance_hist": np.bincount(false_alarms).tolist(),
        "countries": [
            {"id": c, "name": NAMES[c], "bloc": bloc_of.get(c, -1),
             "first": int(active.loc[c, "min"]) if c in active.index else None,
             "last": int(active.loc[c, "max"]) if c in active.index else None,
             "finals": int(active.loc[c, "nunique"]) if c in active.index else 0}
            for c in sorted(set(v["voter"]) | set(v["song"]), key=NAMES.get)
        ],
        "pairs": [
            {"from": a, "to": b, "bias": pts(x), "years": int(n), "p": round(float(p), 4), "sig": bool(s)}
            for a, b, x, n, p, s in zip(pairs["voter"], pairs["song"], pairs["bias"],
                                         pairs["years"], pairs["p"], pairs["significant"])
        ],
        "blocs": [sorted(NAMES[c] for c in members) for members in blocs],
        "holdout": {k: ([round(x, 2) for x in val] if isinstance(val, list) else
                        (round(val, 3) if isinstance(val, float) else val)) for k, val in hold.items()},
    }
    OUT.write_text("window.EUROVISION = " + json.dumps(result, separators=(",", ":")) + ";\n")

    m = result["meta"]
    print(f"{m['votes']:,} votes, {m['finals']} finals, {m['countries']} countries")
    print(f"pairs tested: {m['pairs_tested']}  | p<0.05 uncorrected: {naive} "
          f"(chance alone gives ~{m['expected_by_chance']}, max {m['chance_max']})")
    print(f"significant after BH: {m['bh_significant']}  | reciprocity r = {m['reciprocity_r']}")
    print(f"blocs (modularity {m['modularity']}):")
    for b in result["blocs"]:
        print("  ", ", ".join(b))
    top = pairs.sort_values("bias", ascending=False).head(12)
    for a, b, x, n, p in zip(top["voter"], top["song"], top["bias"], top["years"], top["p"]):
        print(f"   {NAMES[a]:>22} -> {NAMES[b]:<22} +{x*12:.2f} pts over {n} finals (p={p:.4f})")
    print("hold-out:", json.dumps(result["holdout"]))


if __name__ == "__main__":
    main()
