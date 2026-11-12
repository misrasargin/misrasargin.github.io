"""Part 1 - Predict: how many bikes will each station gain or lose in the next hour?

For every station and every hour we forecast two counts, departures and
arrivals. Net flow is arrivals minus departures.

Two forecasts are compared on months the model never saw:
- baseline: the average of the same hour on the same weekday over the last 4 weeks
- model:    gradient-boosted trees with a Poisson loss (two models, one per count)

Time split (no shuffling, the future is never used to predict the past):
  train   29 April - 31 August
  tune    September   (used later to tune the discount rule)
  test    October     (every number reported on the site comes from here)

Output: data/interim/forecast.npz and data/interim/forecast_metrics.json
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import skellam
from sklearn.ensemble import HistGradientBoostingRegressor

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "interim"

N_DAYS = 214
H = N_DAYS * 24
DAY0 = {"apr": 0, "may": 30, "jun": 61, "jul": 91, "aug": 122, "sep": 153, "oct": 183, "end": 214}
FIRST = 4 * 168                                   # first hour with 4 weeks of history
TRAIN = (FIRST, DAY0["sep"] * 24)
TUNE = (DAY0["sep"] * 24, DAY0["oct"] * 24)
TEST = (DAY0["oct"] * 24, H)
# US public holidays inside the period, as day numbers counted from 1 April
HOLIDAYS = [54, 79, 93, 94, 159, 194]             # 25 May, 19 Jun, 3-4 Jul, 7 Sep, 12 Oct
SEED = 2026


def load():
    t = np.load(DATA / "trips.npz")
    stations = pd.read_json(DATA / "stations.json")
    weather = pd.read_csv(DATA / "weather.csv").sort_values("hour")
    return t, stations, weather


def hourly_counts(t, n_stations: int):
    """dep[h, s] and arr[h, s]: trips leaving / reaching station s during hour h."""
    dep = np.zeros((H, n_stations), np.int32)
    arr = np.zeros((H, n_stations), np.int32)
    h_dep = t["start_min"] // 60
    np.add.at(dep, (h_dep, t["start"]), 1)
    h_arr = (t["start_min"] + t["dur_min"]) // 60
    ok = (t["end"] >= 0) & (h_arr < H)
    np.add.at(arr, (h_arr[ok], t["end"][ok]), 1)
    return dep, arr


def lag(x: np.ndarray, k: int) -> np.ndarray:
    out = np.full(x.shape, np.nan, np.float32)
    out[k:] = x[:-k]
    return out


def rolling_sum_24(x: np.ndarray) -> np.ndarray:
    """Total over the 24 hours before each hour (not including it)."""
    c = np.vstack([np.zeros((1, x.shape[1])), np.cumsum(x, axis=0)])
    out = np.full(x.shape, np.nan, np.float32)
    out[24:] = c[24:-1] - c[:-25]
    return out


def four_week_mean(x: np.ndarray) -> np.ndarray:
    return np.mean([lag(x, 168 * k) for k in (1, 2, 3, 4)], axis=0)


def build_features(dep, arr, stations, weather, use_weather: bool = True) -> pd.DataFrame:
    n = dep.shape[1]
    hours = np.arange(H)
    day = hours // 24
    col = lambda v: np.repeat(v, n)                       # one value per hour -> every station
    f = {
        "station": np.tile(np.arange(n), H),
        "hour_of_day": col(hours % 24),
        "weekday": col((day + 2) % 7),                    # 1 April 2026 is a Wednesday (Mon = 0)
        "holiday": col(np.isin(day, HOLIDAYS).astype(int)),
        "docks": np.tile(stations["docks"].to_numpy(), H),
    }
    if use_weather:
        w = weather.set_index("hour").loc[hours]
        f["temp_c"] = col(w["temp_c"].to_numpy())
        f["rain_mm"] = col(w["rain_mm"].to_numpy())
        f["wind_kmh"] = col(w["wind_kmh"].to_numpy())
        f["rain_last_3h"] = col(w["rain_mm"].rolling(3, min_periods=1).sum().shift(1).fillna(0).to_numpy())
    for name, x in (("dep", dep), ("arr", arr)):
        for k in (1, 2, 24, 168):
            f[f"{name}_lag{k}"] = lag(x, k).ravel()
        f[f"{name}_4wk_mean"] = four_week_mean(x).ravel()
        f[f"{name}_last_24h"] = rolling_sum_24(x).ravel()
    return pd.DataFrame(f)


def rows(span: tuple[int, int], n: int) -> slice:
    return slice(span[0] * n, span[1] * n)


def fit(X: pd.DataFrame, y: np.ndarray) -> HistGradientBoostingRegressor:
    model = HistGradientBoostingRegressor(
        loss="poisson", learning_rate=0.06, max_iter=500, max_leaf_nodes=63, min_samples_leaf=40,
        l2_regularization=1.0, categorical_features=["station"],
        early_stopping=True, validation_fraction=0.1, n_iter_no_change=25, random_state=SEED,
    )
    return model.fit(X, y)


def mae(a, b) -> float:
    return float(np.mean(np.abs(a - b)))


def score(dep, arr, lam_dep, lam_arr, span, busy) -> dict:
    s = slice(*span)
    net, net_hat = arr[s] - dep[s], lam_arr[s] - lam_dep[s]
    return {
        "dep_mae": mae(dep[s], lam_dep[s]),
        "arr_mae": mae(arr[s], lam_arr[s]),
        "net_mae": mae(net, net_hat),
        "net_mae_busy": mae(net[:, busy], net_hat[:, busy]),
        "net_rmse": float(np.sqrt(np.mean((net - net_hat) ** 2))),
    }


def reliability(dep, arr, lam_dep, lam_arr, span, k: int = 3) -> dict:
    """Is a forecast '30% chance this station loses 3+ bikes' right 30% of the time?

    If arrivals and departures are independent Poisson counts, net flow follows a
    Skellam distribution, which gives the probability of any gain or loss.
    """
    s = slice(*span)
    la, ld = np.clip(lam_arr[s], 1e-3, None), np.clip(lam_dep[s], 1e-3, None)
    net = arr[s] - dep[s]
    edges = np.array([0, 0.02, 0.05, 0.1, 0.2, 0.3, 0.4, 0.5, 0.7, 1.0001])
    out = {}
    for label, p, hit in (
        ("loses", skellam.cdf(-k, la, ld), net <= -k),
        ("gains", skellam.sf(k - 1, la, ld), net >= k),
    ):
        b = np.digitize(p, edges) - 1
        bins = [
            {"predicted": float(p[b == i].mean()), "observed": float(hit[b == i].mean()), "n": int((b == i).sum())}
            for i in range(len(edges) - 1) if (b == i).sum() >= 50
        ]
        base = float(hit.mean())
        out[label] = {
            "bins": bins, "base_rate": base,
            "brier": float(np.mean((p - hit) ** 2)), "brier_base_rate": float(np.mean((base - hit) ** 2)),
        }
    return out


def main() -> None:
    t, stations, weather = load()
    n = len(stations)
    dep, arr = hourly_counts(t, n)
    X = build_features(dep, arr, stations, weather)
    y_dep, y_arr = dep.ravel(), arr.ravel()
    tr, every = rows(TRAIN, n), rows((FIRST, H), n)

    lam = {}
    for name, y in (("dep", y_dep), ("arr", y_arr)):
        m = fit(X[tr], y[tr])
        full = np.full(H * n, np.nan, np.float32)
        full[every] = m.predict(X[every])
        lam[name] = full.reshape(H, n)
        print(f"{name}: {m.n_iter_} trees")
    base = {"dep": four_week_mean(dep), "arr": four_week_mean(arr)}
    last_week = {"dep": lag(dep, 168), "arr": lag(arr, 168)}

    # ablation: the same model without any weather information
    Xn = build_features(dep, arr, stations, weather, use_weather=False)
    lam_nw = {}
    for name, y in (("dep", y_dep), ("arr", y_arr)):
        full = np.full(H * n, np.nan, np.float32)
        full[every] = fit(Xn[tr], y[tr]).predict(Xn[every])
        lam_nw[name] = full.reshape(H, n)

    volume = dep[slice(*TRAIN)].sum(axis=0)
    busy = volume >= np.quantile(volume, 0.75)
    metrics = {"splits": {"train": TRAIN, "tune": TUNE, "test": TEST}, "busy_stations": int(busy.sum())}
    for split, span in (("tune", TUNE), ("test", TEST)):
        metrics[split] = {
            "last_week": score(dep, arr, last_week["dep"], last_week["arr"], span, busy),
            "baseline": score(dep, arr, base["dep"], base["arr"], span, busy),
            "model": score(dep, arr, lam["dep"], lam["arr"], span, busy),
            "model_no_weather": score(dep, arr, lam_nw["dep"], lam_nw["arr"], span, busy),
        }
    # rainy hours only: where weather should matter most
    wet = np.where(weather["rain_mm"].to_numpy()[slice(*TEST)] > 0)[0] + TEST[0]
    net = arr - dep
    metrics["test_rainy_hours"] = {
        "hours": int(len(wet)),
        "model": mae(net[wet], (lam["arr"] - lam["dep"])[wet]),
        "model_no_weather": mae(net[wet], (lam_nw["arr"] - lam_nw["dep"])[wet]),
        "baseline": mae(net[wet], (base["arr"] - base["dep"])[wet]),
    }
    metrics["reliability_model"] = reliability(dep, arr, lam["dep"], lam["arr"], TEST)
    metrics["reliability_baseline"] = reliability(dep, arr, base["dep"], base["arr"], TEST)

    np.savez_compressed(
        DATA / "forecast.npz", dep=dep, arr=arr,
        model_dep=lam["dep"], model_arr=lam["arr"], base_dep=base["dep"], base_arr=base["arr"],
    )
    (DATA / "forecast_metrics.json").write_text(json.dumps(metrics, indent=1))
    for split in ("tune", "test"):
        for k, v in metrics[split].items():
            print(split, f"{k:>17}", {a: round(b, 3) for a, b in v.items()})
    print("rainy", metrics["test_rainy_hours"])
    for side in ("loses", "gains"):
        r = metrics["reliability_model"][side]
        print(side, "brier", round(r["brier"], 4), "vs base rate", round(r["brier_base_rate"], 4),
              [(round(b["predicted"], 2), round(b["observed"], 2), b["n"]) for b in r["bins"]])


if __name__ == "__main__":
    main()
