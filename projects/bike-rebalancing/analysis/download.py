"""Download the raw data for the bike rebalancing project.

1. Citi Bike trip records for Jersey City and Hoboken, April-October 2026
   (official system data, https://citibikenyc.com/system-data)
2. Station list with dock counts (the system's public GBFS feed)
3. Hourly weather for the same months (Open-Meteo archive, in GMT)

Files are cached in data/raw/ and never downloaded twice.
"""
from pathlib import Path
import urllib.request

RAW = Path(__file__).resolve().parents[1] / "data" / "raw"
BUCKET = "https://s3.amazonaws.com/tripdata/"
TRIP_FILES = [
    "JC-202604-citibike-tripdata.zip",
    "JC-202605-citibike-tripdata.csv.zip",
    "JC-202606-citibike-tripdata.csv.zip",
    "JC-202607-citibike-tripdata.csv.zip",
    "JC-202608-citibike-tripdata.csv.zip",
    "JC-202609-citibike-tripdata.csv.zip",
    "JC-202610-citibike-tripdata.zip",
]
OTHER = {
    "station_information.json": "https://gbfs.citibikenyc.com/gbfs/en/station_information.json",
    "weather_gmt.csv": (
        "https://archive-api.open-meteo.com/v1/archive?latitude=40.72&longitude=-74.04"
        "&start_date=2026-04-01&end_date=2026-11-01"
        "&hourly=temperature_2m,precipitation,wind_speed_10m&timezone=GMT&format=csv"
    ),
}


def fetch(url: str, target: Path) -> None:
    if target.exists():
        print(f"already have {target.name}")
        return
    print(f"downloading {target.name}")
    urllib.request.urlretrieve(url, target)


def main() -> None:
    RAW.mkdir(parents=True, exist_ok=True)
    for name in TRIP_FILES:
        fetch(BUCKET + name, RAW / name)
    for name, url in OTHER.items():
        fetch(url, RAW / name)


if __name__ == "__main__":
    main()
