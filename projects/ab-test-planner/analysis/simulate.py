"""Simulations behind the A/B test planner.

1. Does the sample-size formula deliver the power it promises?
   For several realistic shops we simulate thousands of tests at the planned
   size and count how often the lift is detected. It should be close to 80%.

2. What happens if you peek?
   With no real difference between A and B, we check the result after every
   "look" and stop the first time p < 0.05. The more often you look, the more
   often you declare a winner that is not there.

3. If you must peek, how strict should each look be?
   The single p-value threshold that brings the false-alarm rate back to 5%
   (a Pocock-style boundary), found by simulation.

Output: data/results.js
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from scipy.stats import norm

OUT = Path(__file__).resolve().parents[1] / "data" / "results.js"
SEED = 2026
N_SIM = 40_000
ALPHA, POWER = 0.05, 0.80
LOOKS = [1, 2, 3, 5, 7, 10, 14, 21, 28]

# (label, baseline conversion rate, relative lift to detect)
SCENARIOS = [
    ("Online shop, 2% buy, +20% lift", 0.02, 0.20),
    ("Online shop, 3% buy, +10% lift", 0.03, 0.10),
    ("Newsletter, 5% click, +15% lift", 0.05, 0.15),
    ("Coupon, 10% redeem, +10% lift", 0.10, 0.10),
    ("Loyalty sign-up, 25%, +8% lift", 0.25, 0.08),
    ("Checkout, 40% finish, +5% lift", 0.40, 0.05),
]


def sample_size(p1: float, p2: float, alpha: float = ALPHA, power: float = POWER) -> int:
    za, zb, pbar = norm.ppf(1 - alpha / 2), norm.ppf(power), (p1 + p2) / 2
    top = za * np.sqrt(2 * pbar * (1 - pbar)) + zb * np.sqrt(p1 * (1 - p1) + p2 * (1 - p2))
    return int(np.ceil(top ** 2 / (p2 - p1) ** 2))


def z_stat(xa, xb, n):
    """Pooled two-proportion z statistic, equal group size n."""
    pool = (xa + xb) / (2 * n)
    se = np.sqrt(pool * (1 - pool) * 2 / n)
    return np.divide(xb / n - xa / n, se, out=np.zeros_like(se), where=se > 0)


def check_power(rng) -> list[dict]:
    rows = []
    for label, p1, lift in SCENARIOS:
        p2 = p1 * (1 + lift)
        n = sample_size(p1, p2)
        xa, xb = rng.binomial(n, p1, N_SIM), rng.binomial(n, p2, N_SIM)
        hit = np.abs(z_stat(xa.astype(float), xb.astype(float), n)) > norm.ppf(1 - ALPHA / 2)
        # the same test when there is no difference: how often does it cry wolf?
        ya, yb = rng.binomial(n, p1, N_SIM), rng.binomial(n, p1, N_SIM)
        wolf = np.abs(z_stat(ya.astype(float), yb.astype(float), n)) > norm.ppf(1 - ALPHA / 2)
        rows.append({"label": label, "baseline": p1, "lift": lift, "n_per_group": n,
                     "power": float(hit.mean()), "false_alarm": float(wolf.mean())})
    return rows


def peeking(rng, p: float = 0.05, n_total: int = 14_000) -> dict:
    """No true difference. Look k times at equal steps; record the largest |z| seen."""
    out = []
    for k in LOOKS:
        step = n_total // k
        xa = np.cumsum(rng.binomial(step, p, (N_SIM, k)), axis=1).astype(float)
        xb = np.cumsum(rng.binomial(step, p, (N_SIM, k)), axis=1).astype(float)
        n = step * np.arange(1, k + 1)
        zmax = np.abs(z_stat(xa, xb, n)).max(axis=1)
        z_needed = float(np.quantile(zmax, 1 - ALPHA))          # boundary that restores 5%
        out.append({
            "looks": k,
            "false_alarm": float((zmax > norm.ppf(1 - ALPHA / 2)).mean()),
            "z_needed": z_needed,
            "p_needed": float(2 * norm.sf(z_needed)),
        })
    return {"baseline": p, "visitors_per_group": n_total, "by_looks": out}


def main() -> None:
    rng = np.random.default_rng(SEED)
    result = {
        "meta": {"simulations": N_SIM, "alpha": ALPHA, "power": POWER, "seed": SEED},
        "power_check": check_power(rng),
        "peeking": peeking(rng),
    }
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text("window.ABTEST = " + json.dumps(result, separators=(",", ":")) + ";\n")
    for r in result["power_check"]:
        print(f"{r['label']:<36} n={r['n_per_group']:>7,}  power={r['power']:.3f}  false alarm={r['false_alarm']:.3f}")
    for r in result["peeking"]["by_looks"]:
        print(f"looks={r['looks']:>2}  false alarm={r['false_alarm']:.3f}  p needed={r['p_needed']:.4f}")


if __name__ == "__main__":
    main()
