# Did the Promotion Work? An A/B test planner

**Question.** A shop shows half its visitors a new offer. How long must the test run before the result means
something, and how should the result be read?

**What it is.** An interactive tool with three parts:

- **Plan:** visitors per day, today's conversion rate and the smallest lift worth finding give the number of
  visitors per group and the number of weeks.
- **Check:** counts from a finished test give the difference, its 95% interval, the p-value and a plain verdict.
- **Peeking:** a simulation of 40,000 tests with no real effect. Looking once gives 5% fake winners; looking
  daily for four weeks gives 27%.

- Interactive page: https://misrasargin.github.io/projects/ab-test-planner/
- Method report: https://misrasargin.github.io/projects/ab-test-planner/report.html

## Files

| File | What it is |
|---|---|
| `stats.js` | The statistics: normal CDF and inverse, sample size, power, test of two proportions |
| `page.js` | The interactive charts |
| `analysis/simulate.py` | Simulations: does the planner reach 80% power, and what peeking does |
| `analysis/check_formulas.py` | Compares `stats.js` with SciPy (needs Node.js) |
| `data/results.js` | Simulation output that the pages read |

## Run it

```
pip install -r requirements.txt
python analysis/simulate.py
python analysis/check_formulas.py
```

## Limitations

Yes-or-no outcomes only, independent visitors, even split, steady traffic. See the report.
