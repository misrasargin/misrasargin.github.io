# Mısra Sargın: data science portfolio

Live site: https://misrasargin.github.io

Each project takes a claim people repeat, tests it on open data, and reports how sure we can be.
Every project folder has the same shape:

| File | What it is |
|---|---|
| `index.html` | Plain-language summary and interactive charts |
| `report.html` | Method report: data, cleaning, tests, limitations |
| `analysis/` | Python code that downloads the data and produces every number |
| `data/results.js` | The analysis output that the pages read their numbers from |

## Projects

| Project | Question | Methods |
|---|---|---|
| [Discount or Truck?](projects/bike-rebalancing/) | Is it cheaper to rebalance a bike-share system with rider discounts or with a truck? | Poisson gradient boosting, calibration, Skellam risk, replay simulation |
| [Markdown or Waste?](projects/grocery-markdown/) | When should a shop discount fresh food, and by how much? | Price elasticity with product-level baselines, bootstrap, expected-revenue optimisation, backtest |
| [Did the Promotion Work?](projects/ab-test-planner/) | How long must an A/B test run, and how do you read the result? | Power analysis, test of two proportions, sequential-testing simulation |
| [What Do Data Jobs Ask For?](projects/data-job-skills/) | Which skills go with which data role, and what changed in three years? | Data pipeline, SQLite and SQL, text mining, Wilson intervals, Benjamini-Hochberg |
| [Half-Life of Fame](projects/half-life-of-fame/) | How fast does attention fade after a spike? | Event detection in time series, half-life and tail measures, bootstrap, Kruskal-Wallis |
| [Eurovision Conspiracy Board](projects/eurovision-blocs/) | Do countries really vote for their friends? | Permutation test, Benjamini-Hochberg, Louvain communities, hold-out validation |

## Run a project yourself

```
cd projects/eurovision-blocs
pip install -r requirements.txt
python analysis/download.py
python analysis/analyze.py
```

Then open `index.html` in a browser. No server is needed. Each project's own README lists its scripts.

## Third-party files

- `assets/vendor/d3.min.js`: D3 by Mike Bostock, ISC license (`assets/vendor/LICENSE-d3.txt`)
- `assets/fonts/`: Bricolage Grotesque and Atkinson Hyperlegible, SIL Open Font License 1.1 (license files in the same folder)
