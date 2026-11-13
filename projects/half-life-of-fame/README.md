# Half-Life of Fame

**Question.** After a spike of attention, how fast do people stop looking?

**Answer.** Among the most-read English Wikipedia articles of 2025, 658 had a clear spike. The typical one loses
half of its extra readers in 1.6 days and is back near its normal level after 29 days. The kind of article
matters most: a sports event is back to normal in about 6 days, a film in 43, a television series in 66.
People who died in 2025 lose half their extra readers within a day but stay elevated for about 48 days.

- Interactive page: https://misrasargin.github.io/projects/half-life-of-fame/
- Method report: https://misrasargin.github.io/projects/half-life-of-fame/report.html

## How it works

1. `analysis/download.py` takes the 100 most-viewed articles of each month of 2025 from the Wikimedia
   Pageviews API, downloads 18 months of daily views for each, and adds a one-line Wikidata description.
2. `analysis/analyze.py` finds each article's biggest day, measures its normal level before it, and follows
   the 90 days after: half-life, days until back near normal, and whether the fade is closer to a power law
   or an exponential. Kinds of article are compared with bootstrap intervals and a Kruskal-Wallis test.

```
pip install -r requirements.txt
python analysis/download.py     # about five minutes; it waits between requests
python analysis/analyze.py
```

## Limitations

Page views measure curiosity on one website in one language, daily data cannot resolve fades faster than a
day, and the kinds of article come from simple patterns on descriptions. See the report.

## Data credit

Wikimedia Pageviews API and Wikidata, both CC0.
