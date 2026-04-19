# Why Subscription Apps Win

**Growth, pricing & product intelligence across 10,000+ mobile apps.**

> Analysis of the Google Play Store to identify pricing sweet spots, the drivers of user ratings, and underbuilt category opportunities for consumer-app operators and acquirers.

![Hero chart — category opportunity quadrant](images/hero_quadrant.png)

## Key findings

- **70% of top-performing paid apps price between $1.00–$4.99.** Among paid apps with rating ≥ 4.3 and above-median installs, the sweet spot median is **$2.99** (IQR $1.99–$4.99). Above $9.99, the winner pool drops by 7×.
- **Paid apps rate +0.11 stars higher than free**, after controlling for category, installs, and size (OLS fixed effects, *p* < 0.0001, *n* = 7,027, 95% CI [+0.06, +0.17]).
- **Reviews-per-install is the #1 ratings driver** (|β| = 0.209) — ahead of raw review volume and install count. Both OLS and LightGBM/SHAP agree, making it the most actionable PM lever.
- **"Waste time" is the most universal complaint** — top negative bigram in 4 of 6 categories. "Stopped working" (Health & Fitness), "fake profiles" (Dating), and "worst service" (Travel) round out the PM backlog.
- **Entertainment, Weather, and Finance rank as top opportunity categories** by composite demand × quality-gap × monetization index — stable across 3 weight schemes (Kendall τ = 0.78).

## Dashboard

Interactive 3-page Plotly HTML dashboard — open in any browser, no install required:
[`dashboard/index.html`](dashboard/index.html) · [Market Overview](dashboard/01_market_overview.html) · [Category Deep-Dive](dashboard/02_category_deepdive.html) · [Opportunity Finder](dashboard/03_opportunity_finder.html)

Regenerate with `python dashboard/build_dashboard.py` — reads from `data/processed/*.parquet`, fully reproducible.

Power BI alternative: [`dashboard/powerbi_build_guide.md`](dashboard/powerbi_build_guide.md) ships a pre-aggregated `powerbi_model.csv` + step-by-step build guide with 7 DAX measures for anyone who prefers Power BI Desktop.

## Tech stack

Python 3.12 · pandas · scikit-learn · statsmodels · lightgbm · SHAP · NLTK (VADER) · DuckDB · Plotly · Power BI · Jupyter · pytest

## Repo structure

```
01_subscription_apps_intelligence/
├── notebooks/            # 4 narrative notebooks
├── src/                  # reusable cleaning, stats, nlp, scoring modules
├── tests/                # pytest for src/
├── sql/                  # 8 DuckDB queries over processed parquet
├── data/                 # raw (gitignored) + processed parquet
├── images/               # charts (300 DPI PNG)
├── dashboard/            # Plotly HTML (build_dashboard.py) + Power BI guide
└── reports/              # executive summary, methodology, CV bullets, interview talking points
```

## Reproduce

```bash
cd 01_subscription_apps_intelligence
python3.12 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
# place googleplaystore.csv + googleplaystore_user_reviews.csv in data/raw/ (see data/raw/README.md)
jupyter nbconvert --execute --to notebook --inplace notebooks/*.ipynb
pytest tests/
```

## Methodology

Full methods — parsing choices, regression specification, NLP pipeline, scoring weights and sensitivity analysis — in [`reports/methodology.md`](reports/methodology.md).

## Business recommendations

Three actionable calls for a consumer-subscription-app operator/acquirer in [`reports/executive_summary.md`](reports/executive_summary.md).

## Data caveat

The primary dataset is a **2018 Google Play snapshot** (Kaggle, CC0). `Installs` is bucketed (e.g. `100,000+`), not an exact count — treated as ordinal in all analyses. The companion reviews file covers ~10% of apps; sentiment conclusions are scoped to that sample.

## Author

**Mohammed Areeb Ali** · [github.com/mohammedareebali](https://github.com/mohammedareebali)
