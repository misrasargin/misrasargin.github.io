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
| [Eurovision Conspiracy Board](projects/eurovision-blocs/) | Do countries really vote for their friends? | Permutation test, Benjamini-Hochberg, Louvain communities, hold-out validation |

## Run a project yourself

```
cd projects/eurovision-blocs
pip install -r requirements.txt
python analysis/download.py
python analysis/analyze.py
```

Then open `index.html` in a browser. No server is needed.

## Third-party files

- `assets/vendor/d3.min.js`: D3 by Mike Bostock, ISC license (`assets/vendor/LICENSE-d3.txt`)
- `assets/fonts/`: Bricolage Grotesque and Atkinson Hyperlegible, SIL Open Font License 1.1 (license files in the same folder)
