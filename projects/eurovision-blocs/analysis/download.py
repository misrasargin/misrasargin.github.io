"""Download the Eurovision voting data (1957-2023).

Source: Spijkervet & Burgoyne, "Eurovision Song Contest Dataset"
https://github.com/Spijkervet/eurovision-dataset  (release 2023)
The raw file is cached in data/raw/ and never downloaded twice.
"""
from pathlib import Path
import urllib.request

URL = "https://github.com/Spijkervet/eurovision-dataset/releases/download/2023/votes.csv"
RAW = Path(__file__).resolve().parents[1] / "data" / "raw"


def main() -> Path:
    RAW.mkdir(parents=True, exist_ok=True)
    target = RAW / "votes.csv"
    if target.exists():
        print(f"already have {target} ({target.stat().st_size:,} bytes)")
        return target
    print(f"downloading {URL}")
    urllib.request.urlretrieve(URL, target)
    print(f"saved {target} ({target.stat().st_size:,} bytes)")
    return target


if __name__ == "__main__":
    main()
