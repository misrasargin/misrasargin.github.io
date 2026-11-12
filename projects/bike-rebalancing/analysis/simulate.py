"""Parts 2 and 3 - Decide and Measure.

Decide.  At the start of every hour, each station's forecast is combined with
the bikes it holds right now to get two risks: running empty and filling up.
Stations above a risk threshold are flagged. Then one of three things happens:

  nothing    nobody moves bikes during the day
  discounts  riders near a flagged station are offered a discount to return
             their bike to a station that needs bikes, or to take one from a
             station that needs free docks; a share of them accept
  truck      a crew moves a limited number of bikes per hour from fuller
             stations to flagged ones
  both       the truck and the discounts together

Measure.  We cannot run the experiment on a real city, so we replay every real
trip of a month against simulated dock counts and count two kinds of failure:
a rider who finds no bike, and a rider who finds no free dock.

Assumptions (all stated on the site, all easy to change here):
- every station starts each day at 04:00 half full
- a rider who finds no bike gives up (the trip is lost)
- a rider who finds no dock rides to the nearest station with space
- a discount is offered only for a station within 400 m of the one the rider wanted
- truck moves are instant, 06:00-22:00, at most TRUCK_BIKES_PER_HOUR bikes an hour

Output: data/interim/simulation.json
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import skellam

from forecast import DATA, H, TEST, TUNE

RADIUS_M = 400
START_FILL = 0.5
RESET_HOUR = 4
TRUCK_HOURS = (6, 22)
TRUCK_BIKES_PER_HOUR = (8, 15, 30)
ACCEPT_RATES = (0.1, 0.2, 0.3, 0.5)
THRESHOLDS = (0.05, 0.1, 0.2, 0.3, 0.5)
MAIN_RATE = 0.3
MAIN_TRUCK = 15
REPS, TUNE_REPS = 20, 5
SEED = 2026


def distances_m(lat: np.ndarray, lon: np.ndarray) -> np.ndarray:
    lat, lon = np.radians(lat), np.radians(lon)
    dlat, dlon = lat[:, None] - lat[None, :], lon[:, None] - lon[None, :]
    a = np.sin(dlat / 2) ** 2 + np.cos(lat[:, None]) * np.cos(lat[None, :]) * np.sin(dlon / 2) ** 2
    return 6_371_000 * 2 * np.arcsin(np.sqrt(a))


class World:
    """Everything that stays the same between simulation runs."""

    def __init__(self) -> None:
        t = np.load(DATA / "trips.npz")
        self.stations = pd.read_json(DATA / "stations.json")
        self.docks = self.stations["docks"].to_numpy().astype(int)
        self.n = len(self.docks)
        self.start_min, self.dur = t["start_min"].astype(np.int64), t["dur_min"].astype(np.int64)
        self.start, self.end = t["start"].astype(int), t["end"].astype(int)
        d = distances_m(self.stations["lat"].to_numpy(), self.stations["lon"].to_numpy())
        np.fill_diagonal(d, np.inf)
        order = np.argsort(d, axis=1)
        self.by_distance = [list(order[s, : self.n - 1]) for s in range(self.n)]
        self.near = [[j for j in self.by_distance[s] if d[s, j] <= RADIUS_M] for s in range(self.n)]
        f = np.load(DATA / "forecast.npz")
        self.forecasts = {
            "model": (f["model_dep"], f["model_arr"]),
            "baseline": (f["base_dep"], f["base_arr"]),
            "perfect": (f["dep"].astype(float), f["arr"].astype(float)),
        }

    def events(self, span: tuple[int, int]):
        """Arrivals and departures inside the window, in time order.

        Trips that left before the window but land inside it still bring a bike.
        Within the same minute arrivals come first, then departures.
        """
        m0, m1 = (span[0] + RESET_HOUR) * 60, span[1] * 60
        arrive = self.start_min + self.dur
        dep_idx = np.where((self.start_min >= m0) & (self.start_min < m1))[0]
        arr_idx = np.where((arrive >= m0) & (arrive < m1) & (self.end >= 0) & (self.start_min >= m0 - 1440))[0]
        time = np.concatenate([arrive[arr_idx], self.start_min[dep_idx]])
        kind = np.concatenate([np.zeros(len(arr_idx), int), np.ones(len(dep_idx), int)])
        trip = np.concatenate([arr_idx, dep_idx])
        o = np.lexsort((trip, kind, time))
        before = set(arr_idx[self.start_min[arr_idx] < m0].tolist())   # already on the road at the start
        return time[o].tolist(), kind[o].tolist(), trip[o].tolist(), before, len(dep_idx), m0


def simulate(w: World, span, policy: str = "none", forecast: str = "model", threshold: float = 0.2,
             accept: float = 0.0, truck: int = 0, rng: np.random.Generator | None = None) -> dict:
    n, docks = w.n, w.docks.tolist()
    time, kind, trip, on_road, n_rides, m0 = w.events(span)
    lam_dep, lam_arr = w.forecasts[forecast]
    half = [int(round(c * START_FILL)) for c in docks]
    bikes = half[:]
    low, high = [False] * n, [False] * n
    start, end = w.start, w.end
    near, by_distance = w.near, w.by_distance
    u_take = u_give = None
    if policy in ("discounts", "both"):
        u_take, u_give = rng.random(len(start)), rng.random(len(start))

    no_bike, no_dock = [0] * n, [0] * n
    no_bike_h, no_dock_h = [0] * 24, [0] * 24
    lost = set()
    took_discount = gave_discount = moved = 0
    moved_from: dict[int, int] = {}
    hour = m0 // 60 - 1

    for t, k, i in zip(time, kind, trip):
        while t // 60 > hour:                               # a new hour starts
            hour += 1
            if hour % 24 == RESET_HOUR:
                bikes = half[:]
            if policy == "none":
                continue
            b = np.array(bikes)
            la = np.clip(np.nan_to_num(lam_arr[hour]), 1e-3, None)
            ld = np.clip(np.nan_to_num(lam_dep[hour]), 1e-3, None)
            p_empty = np.nan_to_num(skellam.cdf(-b, la, ld))
            p_full = np.nan_to_num(skellam.sf(w.docks - b - 1, la, ld))
            low, high = (p_empty >= threshold).tolist(), (p_full >= threshold).tolist()
            if policy in ("truck", "both") and TRUCK_HOURS[0] <= hour % 24 < TRUCK_HOURS[1]:
                budget = truck
                # 1) bring bikes to stations about to run empty, from the fullest stations
                donors = sorted(range(n), key=lambda s: (high[s], bikes[s] - half[s]), reverse=True)
                for r in np.argsort(-p_empty):
                    if not low[r] or budget == 0:
                        break
                    for g in donors:
                        need = half[r] - bikes[r]
                        if need <= 0 or budget == 0:
                            break
                        take = min(need, bikes[g] - half[g], budget)
                        if take > 0 and not low[g]:
                            bikes[g] -= take; bikes[r] += take; budget -= take; moved += take
                # 2) clear docks at stations about to fill up, towards the emptiest stations
                takers = sorted(range(n), key=lambda s: (low[s], half[s] - bikes[s]), reverse=True)
                for g in np.argsort(-p_full):
                    if not high[g] or budget == 0:
                        break
                    for r in takers:
                        extra = bikes[g] - half[g]
                        if extra <= 0 or budget == 0:
                            break
                        give = min(extra, half[r] - bikes[r], budget)
                        if give > 0 and not high[r]:
                            bikes[g] -= give; bikes[r] += give; budget -= give; moved += give

        if k == 1:                                          # a rider wants a bike at station s
            s = start[i]
            if u_take is not None and not high[s] and u_take[i] < accept:
                for g in near[s]:                           # discount: take it from a station that is filling up
                    if high[g] and bikes[g] > 0:
                        s = g; took_discount += 1
                        break
            if bikes[s] == 0:
                no_bike[s] += 1; no_bike_h[(t // 60) % 24] += 1; lost.add(i)
            else:
                bikes[s] -= 1
        else:                                               # a rider wants to return a bike at station s
            if i in lost:
                continue
            s = end[i]
            if u_give is not None and not low[s] and u_give[i] < accept:
                for r in near[s]:                           # discount: return it to a station that is running out
                    if low[r] and bikes[r] < docks[r]:
                        s = r; gave_discount += 1
                        break
            if bikes[s] >= docks[s]:
                no_dock[s] += 1; no_dock_h[(t // 60) % 24] += 1
                for j in by_distance[s]:
                    if bikes[j] < docks[j]:
                        bikes[j] += 1
                        break
            else:
                bikes[s] += 1

    return {
        "rides": n_rides, "no_bike": sum(no_bike), "no_dock": sum(no_dock),
        "failures": sum(no_bike) + sum(no_dock),
        "discounts": took_discount + gave_discount, "discounts_take": took_discount, "discounts_return": gave_discount,
        "bikes_moved": moved,
        "by_station": [a + b for a, b in zip(no_bike, no_dock)],
        "by_hour": [a + b for a, b in zip(no_bike_h, no_dock_h)],
    }


def average(runs: list[dict]) -> dict:
    out = {}
    for key in runs[0]:
        v = np.array([r[key] for r in runs], float)
        out[key] = np.round(v.mean(axis=0), 2).tolist()
        if v.ndim == 1:
            out[key + "_sd"] = round(float(v.std(ddof=1)), 2) if len(runs) > 1 else 0.0
    out["runs"] = len(runs)
    return out


def discount_runs(w, span, reps, policy: str = "discounts", **kw) -> dict:
    # the same random riders in every scenario, so scenarios differ only by the policy
    return average([simulate(w, span, policy, rng=np.random.default_rng(SEED + r), **kw) for r in range(reps)])


def main() -> None:
    w = World()
    out = {"assumptions": {
        "radius_m": RADIUS_M, "start_fill": START_FILL, "reset_hour": RESET_HOUR, "truck_hours": TRUCK_HOURS,
        "main_accept_rate": MAIN_RATE, "main_truck_bikes_per_hour": MAIN_TRUCK, "reps": REPS,
        "stations_with_a_neighbour": int(sum(1 for x in w.near if x)),
        "total_bikes": int(sum(round(c * START_FILL) for c in w.docks)), "total_docks": int(w.docks.sum()),
    }}

    # --- tune the risk threshold on September only -------------------------------------
    none_tune = simulate(w, TUNE)
    tune = {"none": none_tune["failures"], "discounts": [], "truck": []}
    for th in THRESHOLDS:
        d = discount_runs(w, TUNE, TUNE_REPS, threshold=th, accept=MAIN_RATE)
        k = simulate(w, TUNE, "truck", threshold=th, truck=MAIN_TRUCK)
        tune["discounts"].append({"threshold": th, "failures": d["failures"], "discounts": d["discounts"]})
        tune["truck"].append({"threshold": th, "failures": k["failures"], "bikes_moved": k["bikes_moved"]})
        print("tune", th, "discounts", d["failures"], d["discounts"], "| truck", k["failures"], k["bikes_moved"])
    th_d = min(tune["discounts"], key=lambda r: r["failures"])["threshold"]
    th_t = min(tune["truck"], key=lambda r: r["failures"])["threshold"]
    tune["chosen"] = {"discounts": th_d, "truck": th_t}
    out["tune"] = tune

    # --- measure on October ---------------------------------------------------------------
    test = {"none": simulate(w, TEST)}
    print("october none", {k: test["none"][k] for k in ("rides", "no_bike", "no_dock")})
    test["discounts"] = {str(p): discount_runs(w, TEST, REPS, threshold=th_d, accept=p) for p in ACCEPT_RATES}
    test["truck"] = {str(k): simulate(w, TEST, "truck", threshold=th_t, truck=k) for k in TRUCK_BIKES_PER_HOUR}
    test["by_forecast"] = {
        f: discount_runs(w, TEST, REPS, threshold=th_d, accept=MAIN_RATE, forecast=f)
        for f in ("baseline", "model", "perfect")
    }
    test["both"] = {
        str(p): discount_runs(w, TEST, REPS, "both", threshold=th_t, accept=p, truck=MAIN_TRUCK) for p in ACCEPT_RATES
    }
    # the trade-off behind the threshold: a stricter rule gives fewer, better-aimed discounts
    test["by_threshold"] = {
        str(th): {
            "discounts": discount_runs(w, TEST, REPS, threshold=th, accept=MAIN_RATE),
            "truck": simulate(w, TEST, "truck", threshold=th, truck=MAIN_TRUCK),
        } for th in THRESHOLDS
    }
    out["test"] = test
    (DATA / "simulation.json").write_text(json.dumps(out))

    base = test["none"]["failures"]
    for p, r in test["discounts"].items():
        saved = base - r["failures"]
        print(f"discounts accept={p}: failures {r['failures']:.0f} (sd {r['failures_sd']}), avoided {saved:.0f}, "
              f"discounts {r['discounts']:.0f}, per avoided {r['discounts'] / saved:.2f}")
    for k, r in test["truck"].items():
        saved = base - r["failures"]
        print(f"truck {k}/h: failures {r['failures']}, avoided {saved}, moved {r['bikes_moved']}, per avoided {r['bikes_moved'] / saved:.2f}")
    for f, r in test["by_forecast"].items():
        print(f"forecast={f}: failures {r['failures']:.0f}, discounts {r['discounts']:.0f}")
    for p, r in test["both"].items():
        print(f"truck + discounts accept={p}: failures {r['failures']:.0f}, discounts {r['discounts']:.0f}, moved {r['bikes_moved']:.0f}")
    for th, r in test["by_threshold"].items():
        d, k = r["discounts"], r["truck"]
        print(f"threshold={th}: discounts avoid {base - d['failures']:.0f} with {d['discounts']:.0f} "
              f"({d['discounts'] / (base - d['failures']):.2f} each) | truck avoids {base - k['failures']} "
              f"with {k['bikes_moved']} ({k['bikes_moved'] / (base - k['failures']):.2f} each)")


if __name__ == "__main__":
    main()
