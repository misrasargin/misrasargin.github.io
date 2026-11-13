"""Collect everything the web pages show into one file: data/results.js.

The pages read every number from this file, so the text cannot drift away
from the analysis.
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd

from forecast import DATA, DAY0, TEST
from simulate import MAIN_RATE, MAIN_TRUCK

OUT = DATA.parent / "results.js"
WEEK_START = (DAY0["oct"] + 4) * 24          # Monday 5 October 00:00
N_WEEK_STATIONS = 12


def r(x, nd=2):
    return np.round(np.asarray(x, float), nd).tolist()


def main() -> None:
    stations = pd.read_json(DATA / "stations.json")
    f = np.load(DATA / "forecast.npz")
    metrics = json.loads((DATA / "forecast_metrics.json").read_text())
    sim = json.loads((DATA / "simulation.json").read_text())
    prep = json.loads((DATA / "prepare_report.json").read_text())
    test, s = sim["test"], slice(*TEST)

    net = (f["arr"] - f["dep"])[s].astype(float)
    net_hat = (f["model_arr"] - f["model_dep"])[s]
    hours = np.arange(*TEST)
    weekday = ((hours // 24 + 2) % 7) < 5
    hod = hours % 24
    profile = lambda x, mask: np.array([x[mask & (hod == h)].mean(axis=0) for h in range(24)]).T   # station x 24

    wd, we, wd_hat = profile(net, weekday), profile(net, ~weekday), profile(net_hat, weekday)
    dep_per_day = f["dep"][s].sum(axis=0) / (len(hours) / 24)
    main_d, main_t = test["discounts"][str(MAIN_RATE)], test["truck"][str(MAIN_TRUCK)]
    main_b = test["both"][str(MAIN_RATE)]
    st = [
        {"id": row.id, "name": row.name, "lat": round(row.lat, 5), "lon": round(row.lon, 5), "docks": int(row.docks),
         "rides_per_day": round(float(dep_per_day[i]), 1),
         "weekday": r(wd[i], 1), "weekend": r(we[i], 1), "weekday_forecast": r(wd_hat[i], 1),
         "fail_none": test["none"]["by_station"][i], "fail_discounts": round(main_d["by_station"][i]),
         "fail_truck": main_t["by_station"][i], "fail_both": round(main_b["by_station"][i])}
        for i, row in enumerate(stations.itertuples())
    ]
    busiest = np.argsort(-dep_per_day)[:N_WEEK_STATIONS]
    wk = slice(WEEK_START, WEEK_START + 168)
    week = [
        {"id": stations["id"][i], "name": stations["name"][i],
         "actual": (f["arr"] - f["dep"])[wk, i].tolist(),
         "model": r((f["model_arr"] - f["model_dep"])[wk, i], 1),
         "baseline": r((f["base_arr"] - f["base_dep"])[wk, i], 1)}
        for i in busiest
    ]

    slim = lambda d: {k: v for k, v in d.items() if k not in ("by_station", "by_hour")}
    base = test["none"]["failures"]
    d_main, t_main = main_d["failures"], main_t["failures"]
    per_discount = main_d["discounts"] / (base - d_main)
    per_truck = main_t["bikes_moved"] / (base - t_main)
    mt = metrics["test"]
    result = {
        "meta": {
            **prep, "months": "April to October 2026", "test_month": "October 2026",
            "rides_replayed": test["none"]["rides"], "main_accept_rate": MAIN_RATE, "main_truck": MAIN_TRUCK,
            "threshold_discounts": sim["tune"]["chosen"]["discounts"], "threshold_truck": sim["tune"]["chosen"]["truck"],
        },
        "headline": {
            "fail_share": base / test["none"]["rides"],
            "error_cut": 1 - mt["model"]["net_mae"] / mt["baseline"]["net_mae"],
            "error_cut_vs_last_week": 1 - mt["model"]["net_mae"] / mt["last_week"]["net_mae"],
            "avoided_discounts": (base - d_main) / base,
            "avoided_truck": (base - t_main) / base,
            "avoided_both": (base - main_b["failures"]) / base,
            "discounts_per_avoided": per_discount,
            "bikes_per_avoided": per_truck,
            "break_even": per_truck / per_discount,
            "morning_share": sum(test["none"]["by_hour"][7:10]) / base,
        },
        "forecast": {
            "test": mt, "rainy": metrics["test_rainy_hours"], "busy_stations": metrics["busy_stations"],
            "reliability": metrics["reliability_model"],
        },
        "stations": st,
        "week": {"start": "Mon 5 Oct", "stations": week},
        "sim": {
            "assumptions": sim["assumptions"], "tune": sim["tune"],
            "none": slim(test["none"]),
            "discounts": {k: slim(v) for k, v in test["discounts"].items()},
            "truck": {k: slim(v) for k, v in test["truck"].items()},
            "both": {k: slim(v) for k, v in test["both"].items()},
            "by_forecast": {k: slim(v) for k, v in test["by_forecast"].items()},
            "by_threshold": {k: {"discounts": slim(v["discounts"]), "truck": slim(v["truck"])}
                             for k, v in test["by_threshold"].items()},
            "by_hour": {"none": test["none"]["by_hour"], "discounts": r(main_d["by_hour"], 0),
                        "truck": main_t["by_hour"], "both": r(main_b["by_hour"], 0)},
        },
    }
    OUT.write_text("window.BIKES = " + json.dumps(result, separators=(",", ":")) + ";\n")
    print(f"wrote {OUT.name}: {OUT.stat().st_size / 1024:.0f} KB")
    print(json.dumps({k: round(v, 3) for k, v in result["headline"].items()}))


if __name__ == "__main__":
    main()
