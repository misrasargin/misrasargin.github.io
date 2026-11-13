"""Check the JavaScript statistics in stats.js against SciPy.

Runs the JS functions with Node and compares every value with an independent
Python calculation. Run:  python analysis/check_formulas.py
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

import numpy as np
from scipy.stats import norm

ROOT = Path(__file__).resolve().parents[1]

CASES = {
    "normCdf": [[x] for x in (-4, -1.96, -0.3, 0, 0.5, 1.2816, 2.5758, 5)],
    "normInv": [[p] for p in (0.0005, 0.01, 0.025, 0.2, 0.5, 0.8, 0.975, 0.9995)],
    "sampleSize": [[0.02, 0.024], [0.05, 0.0575], [0.10, 0.11], [0.25, 0.27], [0.40, 0.42], [0.03, 0.033, 0.01, 0.9]],
    "power": [[0.02, 0.024, 21000], [0.05, 0.0575, 5000], [0.10, 0.11, 14751], [0.40, 0.42, 3000, 0.01]],
    "analyse": [[5000, 250, 5000, 300], [1200, 96, 1180, 121], [800, 40, 800, 41], [20000, 400, 20000, 470]],
}


def py_sample_size(p1, p2, alpha=0.05, power=0.8):
    za, zb, pb = norm.ppf(1 - alpha / 2), norm.ppf(power), (p1 + p2) / 2
    return int(np.ceil((za * np.sqrt(2 * pb * (1 - pb)) + zb * np.sqrt(p1 * (1 - p1) + p2 * (1 - p2))) ** 2 / (p2 - p1) ** 2))


def py_power(p1, p2, n, alpha=0.05):
    za, pb, d = norm.ppf(1 - alpha / 2), (p1 + p2) / 2, abs(p2 - p1)
    se0, se1 = np.sqrt(2 * pb * (1 - pb) / n), np.sqrt((p1 * (1 - p1) + p2 * (1 - p2)) / n)
    return float(norm.cdf((d - za * se0) / se1) + norm.cdf((-d - za * se0) / se1))


def py_analyse(nA, xA, nB, xB):
    pA, pB, pool = xA / nA, xB / nB, (xA + xB) / (nA + nB)
    z = (pB - pA) / np.sqrt(pool * (1 - pool) * (1 / nA + 1 / nB))
    se1 = np.sqrt(pA * (1 - pA) / nA + pB * (1 - pB) / nB)
    return {"p": float(2 * norm.sf(abs(z))), "lo": pB - pA - 1.959963984540054 * se1, "hi": pB - pA + 1.959963984540054 * se1}


def main() -> None:
    script = f"const AB=require({json.dumps(str(ROOT / 'stats.js'))});const C={json.dumps(CASES)};" \
             "const o={};for(const f in C)o[f]=C[f].map(a=>AB[f](...a));console.log(JSON.stringify(o));"
    js = json.loads(subprocess.run(["node", "-e", script], capture_output=True, text=True, check=True).stdout)
    worst = 0.0
    for a, v in zip(CASES["normCdf"], js["normCdf"]):
        worst = max(worst, abs(v - norm.cdf(a[0])))
    for a, v in zip(CASES["normInv"], js["normInv"]):
        worst = max(worst, abs(v - norm.ppf(a[0])))
    for a, v in zip(CASES["power"], js["power"]):
        worst = max(worst, abs(v - py_power(*a)))
    for a, v in zip(CASES["analyse"], js["analyse"]):
        ref = py_analyse(*a)
        worst = max(worst, *(abs(v[k] - ref[k]) for k in ref))
    sizes = [(v, py_sample_size(*a)) for a, v in zip(CASES["sampleSize"], js["sampleSize"])]
    assert all(a == b for a, b in sizes), sizes
    assert worst < 1e-6, worst
    print(f"sample sizes identical: {sizes}")
    print(f"largest difference between JavaScript and SciPy in any other value: {worst:.1e}")


if __name__ == "__main__":
    main()
