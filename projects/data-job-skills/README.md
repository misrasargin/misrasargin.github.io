# What Do Data Jobs Ask For?

**Question.** Which skills go with which data role, and what has changed in three years?

**Answer.** In 11,302 job posts from Hacker News hiring threads (November 2023 to October 2026):

- SQL is 7.9 times more common in posts that mention a data analyst than in other posts; dashboards and dbt follow.
- Data engineer posts stand out for Airflow, dbt, warehouses and Spark; data scientist posts for pandas and statistics;
  ML engineer posts for PyTorch and fine-tuning.
- Mentions of AI agents rose from 2% to 19% of all posts, the largest change in the data.
- Only 5% of posts mention a junior, intern or new-graduate opening (14% for posts with a data analyst).

- Interactive page: https://misrasargin.github.io/projects/data-job-skills/
- Method report: https://misrasargin.github.io/projects/data-job-skills/report.html

## The pipeline

| Step | Script | Output |
|---|---|---|
| Download 36 monthly threads from the HN search API | `analysis/download.py` | `data/raw/threads.json` |
| Clean each post and search it for roles and skills | `analysis/build_db.py`, `analysis/vocab.py` | `data/interim/jobs.db` (SQLite) |
| Count with SQL | `analysis/queries.sql` | |
| Intervals, tests, multiple-testing correction | `analysis/analyze.py` | `data/results.js` |

```
pip install -r requirements.txt
python analysis/download.py
python analysis/build_db.py
python analysis/analyze.py
```

## Limitations

One community, leaning to start-ups and senior software jobs. Posts list several jobs, so skills are tied
to roles only by co-occurrence. Mentions are not requirements. See the report.

## Data credit

Hacker News "Ask HN: Who is hiring?" threads, through the HN Search API by Algolia (https://hn.algolia.com/api).
Only counts are stored in this repository, not the posts.
