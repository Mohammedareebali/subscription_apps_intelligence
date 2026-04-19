# Interview talking points — Project 1

Anticipated questions and prepared answers. Aim to volunteer the caveats before the interviewer surfaces them — it reads as scientific honesty instead of evasion.

## 1. "Walk me through this project in 90 seconds."

> I took a public 10,000-app Google Play snapshot and asked four commercial questions on it: where should a consumer app price, does charging change how users rate, what drives ratings, and which categories are underbuilt. The analysis lives in four notebooks — market landscape, ratings drivers, opportunity scoring, and a demand-side acquisition shortlist — backed by a pytest-covered `src/` library and a DuckDB SQL layer. The headline recommendations are a `$1.99–$4.99` pricing band for the "winner" paid cohort, and a top-5 category opportunity ranking that's stable across three weight schemes. Everything is in a 3-page Power BI dashboard that ships from the same pre-aggregated model.

## 2. "The dataset is from 2018. Why is this still useful?"

> Two reasons. First, the *methodology* generalizes — nothing about the pricing-sweet-spot identification, the ratings-driver regression, or the composite scoring framework is time-bound. Second, the structural findings on Google Play — the shape of the install distribution, the free/paid split by category, the pain-point themes — have held in follow-up scrapes I've seen on Kaggle. But I wouldn't quote specific 2018 dollar figures to a 2025 PM without re-running against fresher data, and I say that explicitly in the methodology doc.

## 3. "Why did you use OLS + SHAP instead of just XGBoost with SHAP?"

> Two complementary jobs. OLS gives me interpretable coefficients with confidence intervals and a category fixed-effect term — that's the defensible narrative I hand to a non-technical stakeholder. LightGBM catches non-linearities OLS would miss and gives a second opinion on feature importance. The headline I'm claiming is "*linear and non-linear models agree on the top drivers*" — that claim is only credible if I've shown both.

## 4. "Why not propensity-score matching for free-vs-paid?"

> Sparse covariates. The observables Google Play gives me — category, size, age, install bucket — aren't rich enough to make the common-support assumption credible; the matched sample would shrink below any threshold I'd want to report. A fixed-effects regression is more defensible at this data quality. I'd reach for PSM if I had richer user-level features, and I'd want to check common support before reporting anything.

## 5. "Install counts are bucketed — how did you handle that?"

> Treated ordinally everywhere. `log(installs)` is used in regressions because the buckets are roughly log-spaced; install-weighted averages use the bucket upper bound as a conservative weight. It's flagged explicitly in the methodology doc and in the caveats section of notebook 01.

## 6. "How did you validate the scoring framework?"

> Sensitivity analysis. I scored under three weight schemes — balanced, growth-tilted, monetization-tilted — and reported the pairwise Kendall τ on the resulting category rankings. If τ had been low, the top-5 list would be an artefact of my weight choices; τ at 0.8+ means the ranking survives reasonable re-weighting.

## 7. "The acquisition shortlist — wouldn't a real M&A team laugh at this?"

> Yes, if I'd presented it as one. I don't. The caveat is in the notebook header, the README, and the executive summary: this is a **demand-side** shortlist — apps that look well-loved and well-sized — not a financial screen. Google Play has no revenue, no DAU, no churn. A real Bending-Spoons-style evaluation would layer SensorTower or data.ai revenue estimates on top. Framing this honestly is the difference between a junior mistake and a junior who understands what they don't have.

## 8. "Why DuckDB for the SQL layer instead of SQLite or Postgres?"

> Three reasons. One — DuckDB reads parquet directly, zero ETL between the notebooks and SQL. Two — the analytical SQL surface area (window functions, `QUALIFY`, `PIVOT`, percentile aggregations) is first-class and reads like Postgres, so nothing in my queries is DuckDB-exclusive in a way that would fail on a take-home. Three — zero-server reproducibility. A recruiter or interviewer can `pip install duckdb` and run every query against the checked-in parquet.

## 9. "What would you do with another week?"

> Three things. Join a more recent (2022–23) scrape and check which findings survive. Add a simple causal identification for the paid-vs-free premium — probably a matching design on App Name substrings within categories. And write a lightweight Streamlit companion to the Power BI dashboard so the repo is interactive even for someone without Power BI Desktop.

## 10. "What's the one weakness of this analysis you're most aware of?"

> The ratings-driver regression is associational, not causal. `log_reviews` correlates with ratings, but that's partly because better apps collect more reviews, not only because review volume itself moves ratings. I call it an association in the notebook and I wouldn't hand it to a PM as a causal "ship this and ratings will rise." That distinction matters.
