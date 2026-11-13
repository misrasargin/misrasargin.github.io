"""The words the pipeline looks for: roles, skills and seniority.

Each entry is a regular expression matched against the post text, ignoring
case unless the pattern says otherwise. Ambiguous words get strict patterns:
"R" must look like the language, "Spark" must not be the investor, and so on.
Excel and spreadsheets are left out on purpose: in these posts they almost
always describe the customer's problem, not a skill the job needs.
The patterns were tuned by reading random matches (see the report).
"""

ROLES = {
    "Data analyst": r"data analy|analytics engineer|business intelligence|\bBI (analyst|engineer|developer)|product analyst",
    "Data scientist": r"data scien",
    "Data engineer": r"data engineer",
    "ML / AI engineer": r"machine learning engineer|\bML engineer|\bMLE\b|\bAI engineer|ML/AI engineer|AI/ML engineer|applied scientist|research scientist|research engineer|machine learning scientist",
}

# skill -> (group, pattern)
SKILLS = {
    # languages
    "Python": ("Languages", r"\bpython\b"),
    "SQL": ("Languages", r"\bsql\b"),
    "R": ("Languages", r"(?-i:\bR\b(?!\s*&)(?=\s*(,|/|\)|and\b|or\b|programming|language|Shiny|Studio))|(?<=[,/(]\s)\bR\b(?!\s*&)|(?<=Python/)R\b|\bRStudio\b|\btidyverse\b)"),
    "Scala": ("Languages", r"\bscala\b"),
    "Java": ("Languages", r"\bjava\b"),
    "Go": ("Languages", r"\bgolang\b|(?-i:\bGo\b(?=\s*(,|/|\)|and\b|or\b|lang)))|(?-i:(?<=[,/(]\s)Go\b)"),
    "Rust": ("Languages", r"\brust\b"),
    "TypeScript / JavaScript": ("Languages", r"typescript|javascript|\bnode\.?js\b|\breact\b"),
    "C++": ("Languages", r"c\+\+"),
    # data engineering
    "Spark": ("Data engineering", r"\b(apache )?spark\b(?!\s+capital)|pyspark"),
    "Kafka": ("Data engineering", r"\bkafka\b"),
    "Airflow": ("Data engineering", r"\bairflow\b"),
    "dbt": ("Data engineering", r"\bdbt\b"),
    "Snowflake": ("Data engineering", r"\bsnowflake\b"),
    "BigQuery": ("Data engineering", r"\bbigquery\b|big query"),
    "Databricks": ("Data engineering", r"\bdatabricks\b"),
    "Redshift": ("Data engineering", r"\bredshift\b"),
    "Postgres": ("Data engineering", r"postgres"),
    "ClickHouse": ("Data engineering", r"\bclickhouse\b"),
    "Data pipelines / ETL": ("Data engineering", r"\bETL\b|\bELT\b|data pipelines?|\bpipelines?\b.{0,20}\bdata\b"),
    "Data warehouse": ("Data engineering", r"data ?warehous|data ?lake|lakehouse"),
    "Kubernetes": ("Cloud and infrastructure", r"kubernetes|\bk8s\b"),
    "Docker": ("Cloud and infrastructure", r"\bdocker\b"),
    "Terraform": ("Cloud and infrastructure", r"\bterraform\b"),
    "AWS": ("Cloud and infrastructure", r"\bAWS\b|amazon web services"),
    "GCP": ("Cloud and infrastructure", r"\bGCP\b|google cloud"),
    "Azure": ("Cloud and infrastructure", r"\bazure\b"),
    # machine learning
    "PyTorch": ("Machine learning", r"pytorch|\btorch\b"),
    "TensorFlow": ("Machine learning", r"tensorflow"),
    "scikit-learn": ("Machine learning", r"scikit|sklearn"),
    "pandas / NumPy": ("Machine learning", r"\bpandas\b|\bnumpy\b|\bpolars\b"),
    "LLMs": ("Machine learning", r"\bLLMs?\b|large language model|generative ai|\bgenai\b|\bgen ai\b|foundation model"),
    "RAG": ("Machine learning", r"(?-i:\bRAG\b)|retrieval[- ]augmented"),
    "AI agents": ("Machine learning", r"\bagentic\b|\bagents\b|\b(AI|LLM|autonomous|coding|voice)[- ]agent\b"),
    "Fine-tuning": ("Machine learning", r"fine[- ]?tun"),
    "Deep learning": ("Machine learning", r"deep learning|neural net|transformers?\b"),
    "Computer vision": ("Machine learning", r"computer vision|\bCV models?\b|image (recognition|segmentation)"),
    "NLP": ("Machine learning", r"\bNLP\b|natural language processing"),
    "MLOps": ("Machine learning", r"\bmlops\b|model (deployment|serving)|ML infra|ML platform"),
    "Evaluation": ("Machine learning", r"\bevals?\b|model evaluation|evaluation (framework|harness|pipeline)s?"),
    # analytics and statistics
    "Statistics": ("Analytics and statistics", r"\bstatistic|\bbayesian\b|(linear|logistic) regression|regression (models?|analysis)|\bprobability\b"),
    "Experiments / A/B tests": ("Analytics and statistics", r"a/b test|\bab test|experimentation|\bexperiment design|causal inference"),
    "Forecasting": ("Analytics and statistics", r"forecast|time[- ]series"),
    "Dashboards / BI tools": ("Analytics and statistics", r"\bdashboards?\b|\btableau\b|power ?bi\b|\blooker\b|\bmetabase\b|\bsuperset\b"),
    "Data visualisation": ("Analytics and statistics", r"data visuali[sz]ation|\bvisuali[sz]ations?\b|\bd3\.?js\b|\bplotly\b"),
    "Optimisation": ("Analytics and statistics", r"operations research|\boptimi[sz]ation (models?|problems?|algorithms?)|linear programming|convex optimi|mixed[- ]integer|combinatorial optimi"),
}

SENIORITY = {
    "junior": r"\bjunior\b|new[- ]grads?|entry[- ]level|\binterns?\b|\binternships?\b|early[- ]career|recent graduates?",
    "senior": r"\bsenior\b|\bstaff\b|\bprincipal\b|\blead\b|\bSr\.?\b",
}
REMOTE = r"\bremote\b"
