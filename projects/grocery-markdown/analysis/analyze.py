"""Markdown or waste? When should a shop discount a fresh product, and by how much?

Three parts, like the bike project: predict, decide, measure.

Predict.  How much more does a product sell at a discount? Each product in each
store is compared with itself: its sales on discounted days against what it
normally sells on that weekday at full price. Only days with no stock-out are
used, because a product that ran out shows sales, not demand.

Decide.  Late in the day a shop holds stock that expires tonight. Given the
hour and how the stock compares with what normally still sells, pick the
discount that earns the most from the remaining stock.

Measure.  Replay held-out days: take what really sold hour by hour at full
price, give the shop a stock level, and compare three policies: never
discount, a flat 30% off in the evening, and the rule above.

Split by time: the first 60 days estimate everything, the last 30 days test it.
Output: data/results.js
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from scipy.optimize import brentq

ROOT = Path(__file__).resolve().parents[1]
DATA, OUT = ROOT / "data" / "interim", ROOT / "data" / "results.js"

TRAIN_DAYS = 60
FULL_PRICE = 0.98                       # a "discount" of 2% or less counts as full price
EDGES = np.array([0.50, 0.60, 0.70, 0.80, 0.90, 0.95, 0.98])
MIN_BASE_DAYS = 8                       # full-price days a product needs to have a baseline
N_BOOT = 400
DECISION_HOURS = [17, 18, 19, 20, 21]
PRICES = np.round(np.arange(1.0, 0.49, -0.05), 2)     # price as a share of full price
STOCK_GRID = np.round(np.arange(0.0, 6.001, 0.05), 2)
STOCK_LEVELS = [1.0, 1.3, 1.6]          # morning stock as a multiple of a normal day's sales
FLAT_PRICE = 0.70
SEED = 2026


def ratio_of_sums(num, den, index, size):
    return np.bincount(index, num, size) / np.bincount(index, den, size)


def weighted_quantiles(x, w, probs):
    o = np.argsort(x)
    cw = np.cumsum(w[o])
    return np.interp(probs * cw[-1], cw, x[o])


def solve_elasticity(sales, expected, price):
    """The e that makes total predicted sales equal total actual sales: sum(expected * price^-e) = sum(sales)."""
    return brentq(lambda e: np.sum(expected * price ** (-e)) - np.sum(sales), 0.0, 12.0)


def main() -> None:
    rng = np.random.default_rng(SEED)
    d = np.load(DATA / "days.npz")
    hours = np.load(DATA / "hours.npy", mmap_mode="r")
    sid, day, weekday, cat = d["sid"], d["day"], d["weekday"].astype(int), d["category"].astype(int)
    sale, price, promo = d["sale"].astype(float), d["discount"].astype(float), d["promo"]
    n_series = int(sid.max()) + 1
    in_stock = d["stockout_hours"] == 0
    train, full = day < TRAIN_DAYS, price >= FULL_PRICE

    # ------------------------------------------------------------------ baseline
    m = train & in_stock & full
    n_base = np.bincount(sid[m], minlength=n_series)
    base = np.where(n_base >= MIN_BASE_DAYS, np.bincount(sid[m], sale[m], n_series) / np.maximum(n_base, 1), np.nan)
    ok = m & np.isfinite(base[sid])
    key = cat * 7 + weekday
    wk = ratio_of_sums(sale[ok], base[sid[ok]], key[ok], (cat.max() + 1) * 7)      # weekday pattern per category
    expected = base[sid] * wk[key]
    valid = in_stock & np.isfinite(expected) & (expected > 0) & (price >= EDGES[0])

    # ------------------------------------------------------------------ predict: the lift from a discount
    disc = valid & ~full
    bucket = np.digitize(price, EDGES) - 1                                           # 0..5
    nb = len(EDGES) - 1
    tr = disc & train
    flat = sid[tr] * nb + bucket[tr]
    S = np.bincount(flat, sale[tr], n_series * nb).reshape(n_series, nb)
    E = np.bincount(flat, expected[tr], n_series * nb).reshape(n_series, nb)
    P = np.bincount(flat, price[tr] * expected[tr], n_series * nb).reshape(n_series, nb)
    lift = S.sum(0) / E.sum(0)
    mean_price = P.sum(0) / E.sum(0)
    weights = rng.multinomial(n_series, np.full(n_series, 1 / n_series), N_BOOT).astype(float)
    boot = (weights @ S) / (weights @ E)
    lift_ci = np.percentile(boot, [2.5, 97.5], axis=0)

    # the same curve with and without a promotion slot, to show how much of the lift is the promotion
    by_promo = {}
    for flag in (0, 1):
        mm = tr & (promo == flag)
        by_promo[flag] = (np.bincount(bucket[mm], sale[mm], nb) / np.bincount(bucket[mm], expected[mm], nb)).tolist()
        by_promo[f"n{flag}"] = np.bincount(bucket[mm], minlength=nb).tolist()

    # one number: the price elasticity (fine 1%-wide price bins per product, so it can be bootstrapped)
    fine = np.clip(((price - EDGES[0]) * 100).astype(int), 0, 47)
    flat = sid[tr] * 48 + fine[tr]
    Sf = np.bincount(flat, sale[tr], n_series * 48).reshape(n_series, 48)
    Ef = np.bincount(flat, expected[tr], n_series * 48).reshape(n_series, 48)
    pf = EDGES[0] + (np.arange(48) + 0.5) / 100
    elasticity = solve_elasticity(Sf.sum(0), Ef.sum(0), pf)
    e_boot = [solve_elasticity(w @ Sf, w @ Ef, pf) for w in weights[:200]]
    series_cat = np.zeros(n_series, int)
    series_cat[sid] = cat
    volume = np.bincount(series_cat, Ef.sum(1))
    by_category = []
    for c in np.argsort(-volume)[:8]:
        rows = np.where(series_cat == c)[0]
        e = solve_elasticity(Sf[rows].sum(0), Ef[rows].sum(0), pf)
        w = rng.multinomial(len(rows), np.full(len(rows), 1 / len(rows)), 200).astype(float)
        eb = [solve_elasticity(x @ Sf[rows], x @ Ef[rows], pf) for x in w]
        by_category.append({"category": int(c), "products": int(len(rows)), "elasticity": e,
                            "lo": float(np.percentile(eb, 2.5)), "hi": float(np.percentile(eb, 97.5))})
    lift_at = lambda p: p ** (-elasticity)

    # held-out check: do the first 60 days predict discounted sales in the last 30?
    te = disc & ~train
    pred = {"ignore the discount": expected[te], "lift per discount band": expected[te] * lift[bucket[te]],
            "one elasticity": expected[te] * lift_at(price[te])}
    validation = {k: {"wape": float(np.abs(sale[te] - v).sum() / sale[te].sum()), "bias": float(v.sum() / sale[te].sum() - 1)}
                  for k, v in pred.items()}
    test_lift = (np.bincount(bucket[te], sale[te], nb) / np.bincount(bucket[te], expected[te], nb)).tolist()

    # ------------------------------------------------------------------ the shape of a day
    m_full = np.where(valid & full & train)[0]
    m_disc = np.where(tr)[0]
    take = lambda idx: np.asarray(hours[np.sort(rng.choice(idx, min(len(idx), 400_000), replace=False))], float)
    H_full = take(m_full)
    profile = H_full.sum(0) / H_full.sum()
    H_disc = take(m_disc)
    profile_disc = H_disc.sum(0) / H_disc.sum()
    remaining = profile[::-1].cumsum()[::-1]                                         # share of the day still to come from hour h

    # how wrong can "what normally still sells" be? ratio of actual to expected remaining sales
    idx = np.sort(rng.choice(m_full, min(len(m_full), 400_000), replace=False))
    Hs, ex = np.asarray(hours[idx], float), expected[idx]
    probs = (np.arange(199) + 0.5) / 199
    noise = {h: weighted_quantiles(Hs[:, h:].sum(1) / (ex * remaining[h]), ex, probs) for h in DECISION_HOURS}

    # ------------------------------------------------------------------ decide
    mult = lift_at(PRICES)                                                           # demand multiplier at each price
    table = {}
    for h in DECISION_HOURS:
        xi = noise[h]
        sold = np.minimum(STOCK_GRID[:, None, None], mult[None, :, None] * xi[None, None, :]).mean(2)   # stock x price
        revenue = sold * PRICES[None, :]
        best = revenue.argmax(1)
        table[h] = {"price": PRICES[best], "revenue": revenue[np.arange(len(STOCK_GRID)), best], "revenue_full": revenue[:, 0],
                    "sold": sold[np.arange(len(STOCK_GRID)), best], "sold_full": sold[:, 0]}

    # ------------------------------------------------------------------ measure: replay held-out full-price days
    m_test = np.where(valid & full & ~train)[0]
    Ht, et = np.asarray(hours[m_test], float), expected[m_test]
    backtest = []
    for q in STOCK_LEVELS:
        stock = q * et
        for h in DECISION_HOURS:
            before = np.minimum(stock, Ht[:, :h].sum(1))
            left, demand = stock - before, Ht[:, h:].sum(1)
            ratio = np.where(left > 0, left / (et * remaining[h]), 0.0)
            rule_price = table[h]["price"][np.clip(np.round(ratio / 0.05).astype(int), 0, len(STOCK_GRID) - 1)]
            row = {"stock": q, "hour": h, "days": int(len(m_test)), "stock_left_share": float(left.sum() / stock.sum())}
            for name, p in (("none", np.ones_like(left)), ("flat", np.full_like(left, FLAT_PRICE)), ("rule", rule_price)):
                sold = np.minimum(left, demand * p ** (-elasticity))
                row[name] = {"revenue": float((before + p * sold).sum()), "waste": float((left - sold).sum() / stock.sum()),
                             "discounted_days": float((p < 1).mean())}
            for name in ("flat", "rule"):
                row[name]["revenue_change"] = row[name]["revenue"] / row["none"]["revenue"] - 1
            backtest.append(row)

    r = lambda x, nd=4: np.round(np.asarray(x, float), nd).tolist()
    result = {
        "meta": {
            "product_days": int(len(sid)), "series": n_series, "stores": int(len(np.unique(d["store"]))),
            "products": int(len(np.unique(d["product"]))), "days": int(day.max()) + 1,
            "first_date": str(d["first_date"]), "last_date": str(d["last_date"]), "train_days": TRAIN_DAYS,
            "in_stock_share": float(in_stock.mean()), "discounted_share": float((~full).mean()),
            "series_with_baseline": int(np.isfinite(base).sum()), "usable_days": int(valid.sum()),
            "discounted_train_days": int(tr.sum()), "discounted_test_days": int(te.sum()), "replay_days": int(len(m_test)),
            "flat_price": FLAT_PRICE, "bootstrap": N_BOOT,
        },
        "lift": [{"band": f"{round((1 - EDGES[i + 1]) * 100)}-{round((1 - EDGES[i]) * 100)}% off", "price": float(mean_price[i]),
                  "lift": float(lift[i]), "lo": float(lift_ci[0, i]), "hi": float(lift_ci[1, i]), "test_lift": test_lift[i],
                  "no_promo": by_promo[0][i], "promo": by_promo[1][i], "n_no_promo": by_promo["n0"][i], "n_promo": by_promo["n1"][i],
                  "days": int(np.bincount(bucket[tr], minlength=nb)[i])} for i in range(nb)][::-1],
        "elasticity": {"value": elasticity, "lo": float(np.percentile(e_boot, 2.5)), "hi": float(np.percentile(e_boot, 97.5)),
                       "by_category": by_category},
        "validation": validation,
        "profile": {"full": r(profile), "discounted": r(profile_disc), "remaining": r(remaining),
                    "largest_gap": float(np.abs(profile - profile_disc).max())},
        "noise": {str(h): r(noise[h], 3) for h in DECISION_HOURS},
        "prices": PRICES.tolist(), "stock_grid": STOCK_GRID.tolist(),
        "table": {str(h): {k: r(v) for k, v in table[h].items()} for h in DECISION_HOURS},
        "backtest": backtest,
    }
    OUT.write_text("window.GROCERY = " + json.dumps(result, separators=(",", ":")) + ";\n")
    print(f"wrote {OUT.name}: {OUT.stat().st_size / 1024:.0f} KB")
    print({k: (round(v, 3) if isinstance(v, float) else v) for k, v in result["meta"].items()})
    for b in result["lift"]:
        print(f"  {b['band']:>11}: lift x{b['lift']:.2f} ({b['lo']:.2f}-{b['hi']:.2f}), held-out x{b['test_lift']:.2f}, "
              f"no promo x{b['no_promo']:.2f} ({b['n_no_promo']:,}), promo x{b['promo']:.2f} ({b['n_promo']:,})")
    e = result["elasticity"]
    print(f"elasticity {e['value']:.2f} ({e['lo']:.2f}-{e['hi']:.2f}); by category:",
          [(c["category"], c["products"], round(c["elasticity"], 2)) for c in by_category])
    print("validation", {k: {a: round(b, 3) for a, b in v.items()} for k, v in validation.items()})
    print("share of day left at", {h: round(float(remaining[h]), 3) for h in DECISION_HOURS}, "profile gap", round(result["profile"]["largest_gap"], 4))
    for h in (19,):
        t = table[h]
        print(f"rule at {h}:00, stock ratio -> price:", {float(s): float(t['price'][i]) for i, s in enumerate(STOCK_GRID) if s in (0.5, 1.0, 1.5, 2.0, 3.0, 4.0, 6.0)})
    for b in backtest:
        if b["hour"] == 19:
            print(f"stock x{b['stock']} at 19:00: left {b['stock_left_share']:.1%} | none waste {b['none']['waste']:.1%} | "
                  f"flat rev {b['flat']['revenue_change']:+.2%} waste {b['flat']['waste']:.1%} | "
                  f"rule rev {b['rule']['revenue_change']:+.2%} waste {b['rule']['waste']:.1%} (discounts {b['rule']['discounted_days']:.0%} of days)")


if __name__ == "__main__":
    main()
