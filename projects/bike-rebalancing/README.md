# Discount or Truck? Rebalancing a bike-share system

**Question.** Bike-share stations run empty in one place and fill up in another. Is it cheaper to fix that
with rider discounts or with a truck?

**Answer.** For Jersey City and Hoboken in October 2026, the truck. If nobody moved bikes, 17% of 111,281
rides would fail (no bike, or no free dock). Discounts accepted by 30% of riders avoid 19% of those failures;
one truck moving up to 15 bikes an hour avoids 33%. A discount is the cheaper tool only if it costs less
than 30% of what the truck costs per bike moved.

- Interactive page: https://misrasargin.github.io/projects/bike-rebalancing/
- Method report: https://misrasargin.github.io/projects/bike-rebalancing/report.html

## The three parts

| Part | What it does | Script |
|---|---|---|
| Predict | Forecasts each station's departures and arrivals for the next hour (gradient-boosted trees, Poisson loss). 9% lower error than a 4-week-average rule on a held-out month. | `analysis/forecast.py` |
| Decide | Turns the forecast and the bikes at each station into a risk of running empty or full, flags risky stations, and offers discounts to riders within 400 m. | `analysis/simulate.py` |
| Measure | Replays every real ride of October against simulated dock counts under three policies: nothing, discounts, truck. | `analysis/simulate.py` |

## Run it

```
pip install -r requirements.txt
python analysis/download.py        # trip files, station list, weather -> data/raw/
python analysis/prepare.py         # cleaning -> data/interim/
python analysis/forecast.py        # model and baselines
python analysis/simulate.py        # tuning on September, replay of October
python analysis/build_results.py   # data/results.js, which the pages read
```

The split follows time: train 29 April to 31 August, tune the discount rule on September, report October.

## Limitations

The replay is a simulation with stated assumptions: stations start each day half full, a fixed share of
riders accept a discount, and truck moves are instant. See the report for the full list.

## Data credit

- Citi Bike system data, https://citibikenyc.com/system-data (trip records and station feed)
- Weather data by Open-Meteo.com

Only aggregated results are stored in this repository, not the trip records.
