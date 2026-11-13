# Markdown or Waste? Pricing fresh food before it expires

**Question.** When should a shop discount a fresh product, and by how much?

**Answer.** In 4.5 million product-days from an online grocer, a 10 to 20% discount multiplies a product's
sales by 1.33 and a 30 to 40% discount by 1.88 (price elasticity 1.87). An evening rule built on that keeps
full price until the shelf holds about twice what normally still sells, then deepens the discount. Replayed
on 374,060 held-out days with stock 30% above a normal day, the rule cuts waste from 30% to 21% of the stock
and raises revenue by 2.9%; a flat 30% discount manages 25% and 1.8%.

- Interactive page: https://misrasargin.github.io/projects/grocery-markdown/
- Method report: https://misrasargin.github.io/projects/grocery-markdown/report.html

## The three parts

| Part | What it does |
|---|---|
| Predict | Compares each product's discounted days with its own full-price baseline, on days without a stock-out. Bootstrap intervals, held-out check. |
| Decide | For the hour and the stock on the shelf, picks the price with the highest expected revenue before closing. |
| Measure | Replays held-out days hour by hour under three policies: never discount, flat 30% off, the rule. |

## Run it

```
pip install -r requirements.txt
python analysis/download.py     # 106 MB
python analysis/prepare.py
python analysis/analyze.py
```

## Limitations

The discounts were not randomised, and the dataset has no stock counts or expiry dates: those parts of the
replay are assumptions. See the report.

## Data credit

FreshRetailNet-50K by Dingdong Fresh, CC BY 4.0. https://huggingface.co/datasets/Dingdong-Inc/FreshRetailNet-50K
Only aggregated results are stored in this repository.
