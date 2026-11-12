"""Turn the raw downloads into three small, clean tables in data/interim/.

trips.npz      one row per trip: start minute, duration, start/end station, rider type
stations.json  the stations we model: id, name, position, number of docks
weather.csv    hourly weather in local (New York) time

Cleaning rules, all applied here and nowhere else:
- timestamps are floored to the minute and counted from 1 April 2026 00:00
- "false starts" are dropped: trips of one minute or less that end where they began
- stations are kept only if the live station feed lists them with at least one dock;
  a trip that ends anywhere else (New York side, removed station, bike never docked)
  simply leaves the system
"""
from __future__ import annotations

import json
import zipfile
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW, OUT = ROOT / "data" / "raw", ROOT / "data" / "interim"
T0 = pd.Timestamp("2026-04-01 00:00")
N_DAYS = 214                      # 1 April - 31 October
LOCAL = ZoneInfo("America/New_York")
COLS = ["rideable_type", "started_at", "ended_at", "start_station_id", "end_station_id", "member_casual"]


def read_trip_zip(path: Path) -> pd.DataFrame:
    """Read every trip CSV inside one monthly zip (ignores macOS helper files)."""
    frames = []
    with zipfile.ZipFile(path) as z:
        for name in z.namelist():
            if name.lower().endswith(".csv") and "__MACOSX" not in name and "/._" not in name:
                with z.open(name) as f:
                    frames.append(pd.read_csv(f, usecols=COLS, dtype=str, keep_default_na=False))
    return pd.concat(frames, ignore_index=True)


def minutes_since_t0(text: pd.Series) -> np.ndarray:
    # keep only "YYYY-MM-DD HH:MM:SS"; fractions of a second are not needed
    stamp = pd.to_datetime(text.str.slice(0, 19), format="%Y-%m-%d %H:%M:%S")
    return ((stamp - T0) // pd.Timedelta(minutes=1)).to_numpy().astype(np.int64)


def trips_table(raw: pd.DataFrame) -> pd.DataFrame:
    start = minutes_since_t0(raw["started_at"])
    end = minutes_since_t0(raw["ended_at"])
    t = pd.DataFrame({
        "start_min": start,
        "dur_min": end - start,
        "start_id": raw["start_station_id"].to_numpy(),
        "end_id": raw["end_station_id"].to_numpy(),
        "member": (raw["member_casual"] == "member").to_numpy(),
        "electric": (raw["rideable_type"] == "electric_bike").to_numpy(),
    })
    # stable sort: trips in the same minute keep their order in the files
    return t.sort_values("start_min", kind="stable").reset_index(drop=True)


def load_raw_trips() -> pd.DataFrame:
    files = sorted(RAW.glob("JC-2026*-citibike-tripdata*.zip"))
    if not files:
        raise SystemExit("no trip files in data/raw - run analysis/download.py first")
    return trips_table(pd.concat([read_trip_zip(f) for f in files], ignore_index=True))


def station_table(trips: pd.DataFrame) -> pd.DataFrame:
    path = RAW / "station_information.json"
    feed = json.loads(path.read_text())
    rows = feed["data"]["stations"] if "data" in feed else feed["stations"]
    if rows and isinstance(rows[0], dict):
        rows = [[r.get("short_name", ""), r["name"], r["capacity"], r["lat"], r["lon"]] for r in rows]
    st = pd.DataFrame([r[:5] for r in rows], columns=["id", "name", "docks", "lat", "lon"])
    used = set(trips["start_id"])
    st = st[st["id"].isin(used) & (st["docks"] > 0)].sort_values("id").reset_index(drop=True)
    return st


def weather_table() -> pd.DataFrame:
    w = pd.read_csv(RAW / "weather_gmt.csv", skiprows=3)
    w.columns = ["time", "temp_c", "rain_mm", "wind_kmh"]
    local = pd.to_datetime(w["time"]).dt.tz_localize("UTC").dt.tz_convert(LOCAL).dt.tz_localize(None)
    w["hour"] = ((local - T0) // pd.Timedelta(hours=1)).astype(int)
    w = w[(w["hour"] >= 0) & (w["hour"] < N_DAYS * 24)].drop_duplicates("hour")
    assert len(w) == N_DAYS * 24, f"weather has {len(w)} hours, expected {N_DAYS * 24}"
    return w[["hour", "temp_c", "rain_mm", "wind_kmh"]].reset_index(drop=True)


def clean(trips: pd.DataFrame, stations: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    n0 = len(trips)
    false_start = (trips["dur_min"] <= 1) & (trips["start_id"] == trips["end_id"])
    trips = trips[~false_start]
    index = {s: i for i, s in enumerate(stations["id"])}
    start = trips["start_id"].map(index)
    unknown_start = start.isna()
    trips = trips[~unknown_start].copy()
    trips["start"] = start[~unknown_start].astype(int)
    trips["end"] = trips["end_id"].map(index).fillna(-1).astype(int)   # -1 = leaves the system
    report = {
        "raw_trips": int(n0),
        "false_starts_dropped": int(false_start.sum()),
        "start_station_not_modelled": int(unknown_start.sum()),
        "trips": int(len(trips)),
        "leave_the_system": int((trips["end"] < 0).sum()),
    }
    return trips.reset_index(drop=True), report


def main(trips: pd.DataFrame | None = None) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    trips = load_raw_trips() if trips is None else trips
    stations = station_table(trips)
    trips, report = clean(trips, stations)
    weather = weather_table()
    np.savez_compressed(
        OUT / "trips.npz",
        start_min=trips["start_min"].to_numpy(np.int32), dur_min=trips["dur_min"].to_numpy(np.int32),
        start=trips["start"].to_numpy(np.int16), end=trips["end"].to_numpy(np.int16),
        member=trips["member"].to_numpy(bool), electric=trips["electric"].to_numpy(bool),
    )
    stations.to_json(OUT / "stations.json", orient="records", indent=1)
    weather.to_csv(OUT / "weather.csv", index=False)
    report["stations"] = int(len(stations))
    (OUT / "prepare_report.json").write_text(json.dumps(report, indent=1))
    print(json.dumps(report))


if __name__ == "__main__":
    main()
