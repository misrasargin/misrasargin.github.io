# Eurovision Conspiracy Board

**Question.** Do Eurovision countries give their friends more points than the song deserves?

**Answer.** Yes. Of 1,341 country pairs tested on 48 grand finals (1975 to 2023), 119 show favouritism that
survives a permutation test and a multiple-testing correction. Favours are returned (r = 0.63), and on held-out
years the public vote carries most of it (+4.2 extra points for a friend) while juries show much less (+1.3).

- Interactive page: https://misrasargin.github.io/projects/eurovision-blocs/
- Method report: https://misrasargin.github.io/projects/eurovision-blocs/report.html

## How it works

1. `analysis/download.py` fetches the open voting data (Spijkervet & Burgoyne, release 2023) into `data/raw/`.
2. `analysis/analyze.py` cleans it, measures bias for every pair, runs 5,000 shuffles, finds blocs,
   runs the hold-out check and writes `data/results.js`.
3. `index.html` and `report.html` read every number from `data/results.js`.

Bias is the points A gave B minus the average everyone else gave B that year, so song quality cancels out.

## Limitations

The analysis shows that favouritism exists, not why. See the report for the full list.

## Data credit

Spijkervet, J. and Burgoyne, J. A. Eurovision Song Contest Dataset. https://github.com/Spijkervet/eurovision-dataset
