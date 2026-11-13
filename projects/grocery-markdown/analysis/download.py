"""Download FreshRetailNet-50K (training split).

Hourly sales of fresh products from an online grocery platform: 50,000
store-product pairs over 90 days, with the discount of the day and the hours
each product was out of stock. Published by Dingdong Fresh under CC BY 4.0:
https://huggingface.co/datasets/Dingdong-Inc/FreshRetailNet-50K

Output: data/raw/train.parquet (about 106 MB)
"""
from pathlib import Path
import urllib.request

URL = "https://huggingface.co/datasets/Dingdong-Inc/FreshRetailNet-50K/resolve/main/data/train.parquet"
TARGET = Path(__file__).resolve().parents[1] / "data" / "raw" / "train.parquet"

if __name__ == "__main__":
    TARGET.parent.mkdir(parents=True, exist_ok=True)
    if TARGET.exists():
        print(f"already have {TARGET.name}")
    else:
        print("downloading train.parquet (106 MB)")
        urllib.request.urlretrieve(URL, TARGET)
