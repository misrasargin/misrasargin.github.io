"""Read the parquet file once and save plain arrays that load in a second.

One row is one product in one store on one day. Sales are in the dataset's
own normalised units (true units times a constant the publisher keeps
private), so everything downstream works with ratios, never with units.

Output: data/interim/days.npz and data/interim/hours.npy
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[1]
RAW, OUT = ROOT / "data" / "raw" / "train.parquet", ROOT / "data" / "interim"
COLS = ["store_id", "product_id", "first_category_id", "dt", "sale_amount", "hours_sale",
        "stock_hour6_22_cnt", "discount", "holiday_flag", "activity_flag"]


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    parts, hours = [], []
    for batch in pq.ParquetFile(RAW).iter_batches(batch_size=250_000, columns=COLS):
        h = batch.column("hours_sale").values.to_numpy(zero_copy_only=False)
        assert len(h) == batch.num_rows * 24, "every day must have 24 hourly values"
        hours.append(h.reshape(-1, 24).astype(np.float32))
        parts.append(batch.drop_columns(["hours_sale"]).to_pandas())
    t = pd.concat(parts, ignore_index=True)
    hours = np.concatenate(hours)
    series = (t["store_id"].astype(np.int64) * 100_000 + t["product_id"]).to_numpy()
    _, sid = np.unique(series, return_inverse=True)
    day0 = pd.Timestamp(t["dt"].min())
    day = (pd.to_datetime(t["dt"]) - day0).dt.days.to_numpy()
    np.savez(
        OUT / "days.npz",
        sid=sid.astype(np.int32), day=day.astype(np.int16), weekday=((day + day0.weekday()) % 7).astype(np.int8),
        category=t["first_category_id"].to_numpy(np.int16), store=t["store_id"].to_numpy(np.int32),
        product=t["product_id"].to_numpy(np.int32), sale=t["sale_amount"].to_numpy(np.float32),
        discount=t["discount"].to_numpy(np.float64), stockout_hours=t["stock_hour6_22_cnt"].to_numpy(np.int8),
        holiday=t["holiday_flag"].to_numpy(np.int8), promo=t["activity_flag"].to_numpy(np.int8),
        first_date=str(day0.date()), last_date=str(t["dt"].max()),
    )
    np.save(OUT / "hours.npy", hours)
    print(f"{len(t):,} product-days, {sid.max() + 1:,} store-product pairs, {day.max() + 1} days ({day0.date()} to {t['dt'].max()})")
    gap = np.abs(hours.sum(axis=1) - t["sale_amount"].to_numpy()).max()
    print(f"largest gap between the daily total and the sum of its hours: {gap:.4f}")


if __name__ == "__main__":
    main()
