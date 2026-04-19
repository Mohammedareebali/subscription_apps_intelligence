# CV / resume bullets — Project 1

Five drop-in bullets, each mapping to a different analytical capability. Pick your top 3 for the CV; use all five for LinkedIn.

---

- **Analysed 9,659 Google Play apps** to identify a **$1.99–$2.99 pricing sweet spot** for consumer paid apps — 70% of rating-≥4.3, above-median-install paid apps price in the $1–$5 band — and ranked 33 categories by a composite demand × quality-gap × monetization index stable across three weight schemes (Kendall τ = 0.78).

- **Built a fixed-effects OLS + LightGBM + SHAP pipeline** to isolate ratings drivers; *reviews-per-install* emerged as the largest coefficient (|β| = 0.209) in both the linear and tree-based models — a cross-model agreement that strengthened the PM recommendation.

- **Shipped a NLP pain-point extractor** (VADER + TF-IDF bigrams, 37,427 reviews, 6 categories) surfacing "waste time", "stopped working", and "fake profiles" as the top recurring complaint themes — PM-ready backlog items with direct product-roadmap implications.

- **Authored 8 production DuckDB SQL queries** (window functions, CTE chains, `PIVOT`, `QUALIFY`, `PERCENTILE_CONT`) against processed parquet, plus a 3-page Power BI dashboard with 7 custom DAX measures for a stakeholder-ready view of the analysis.

- **Delivered a reproducible, production-quality codebase**: pytest-covered `src/` modules (22/22 tests green), pinned `requirements.txt`, parquet persistence, and `jupyter nbconvert --execute` end-to-end validation — zero manual steps from clone to outputs.

---

## Skills surfaced (for the skills section)

Python · pandas · scikit-learn · statsmodels · LightGBM · SHAP · NLTK VADER · TF-IDF · DuckDB · SQL (window functions, CTEs, pivots) · Power BI · DAX · Jupyter · pytest · parquet · reproducible analysis

## LinkedIn post hook

> I analysed 9,659 mobile apps to find where subscription apps actually win on pricing, ratings, and category opportunity.
>
> Headline: 70% of top-performing paid apps price between $1–$5. Reviews-per-install matters more than raw install count for ratings. "Waste time" is the most universal complaint across 4 categories.
>
> Full analysis with SQL, Python, and a Power BI dashboard on GitHub:
> github.com/mohammedareebali/[repo]
