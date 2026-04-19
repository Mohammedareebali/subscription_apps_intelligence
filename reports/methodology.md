# Methodology

## 1. Data provenance

- **Apps frame** — Kaggle ["Google Play Store Apps"](https://www.kaggle.com/datasets/lava18/google-play-store-apps) by Lavanya Gupta, CC0. One row per app with Category, Rating, Reviews, Installs, Price, Size, Content Rating, Genres, Last Updated, Android Version.
- **Reviews frame** — the companion file `googleplaystore_user_reviews.csv`: one row per review with `Translated_Review`, a pre-scored `Sentiment` label (`Positive`/`Neutral`/`Negative`), and `Sentiment_Polarity` / `Sentiment_Subjectivity` continuous scores. ~64k rows covering ~1k apps (~10% of the apps corpus).

**Snapshot age** — the underlying crawl is from **2018**. This is disclosed in the top-level README and every notebook. Numerical findings are time-stamped to that snapshot; methodology generalizes.

## 2. Cleaning & feature engineering

The raw CSV has three columns with painful encoding. All parsing lives in [`src/cleaning.py`](../src/cleaning.py) and is unit-tested in [`tests/test_cleaning.py`](../tests/test_cleaning.py).

- **`Installs`** — strings like `"100,000+"`. Parsed to numeric and treated as **ordinal**, not an exact count. Install buckets, not counts, are what Google Play publishes.
- **`Size`** — mixed units: `"19M"`, `"8.7k"`, `"Varies with device"`. Converted to MB; `"Varies with device"` → `NaN`.
- **`Price`** — `"$4.99"` or `"0"`. Stripped to numeric USD.
- **`Last Updated`** — string dates like `"January 7, 2018"`. Parsed with pandas `to_datetime(..., errors="coerce", format="mixed")`.
- **Category** — uppercase, `"&"` → `"AND"`, spaces → underscores so joins/SQL are robust.

Engineered features added in [`src/features.py`](../src/features.py): `is_paid`, `price_band`, `log_installs`, `log_size_mb`, `log_reviews`, `age_days`, `reviews_per_install`.

Duplicates on `App` name are dropped keeping the first row. One notorious malformed row (all columns shift left by one) is filtered by requiring `Rating ∈ [0, 5]`.

## 3. Free-vs-paid comparison

Three estimators, reported side-by-side:

1. **Welch's *t*-test** on paid vs free `Rating`. Welch (not Student's) to accommodate unequal variances.
2. **Cohen's *d***, pooled-SD version, as a unit-free effect size.
3. **OLS with category fixed effects**:

   ```
   Rating ~ is_paid + C(category) + log_installs + log_size_mb
   ```

   The `is_paid` coefficient, with 95% CI, is the paid premium after absorbing category composition and install/size differences.

Per-category Welch + Cohen's *d* are computed in [`src/stats.py::within_group_comparison`](../src/stats.py) with a minimum-sample-size floor of 30 per cell and presented as a forest plot.

**Why not propensity-score matching?** The covariate set is sparse (category, size, age) and common support would shrink the matched sample below any credible threshold. A fixed-effects regression is more defensible at this data quality.

## 4. Pricing sweet spot

Narrow the paid corpus to "winners" — apps already demonstrating product-market fit:

- `Rating ≥ 4.3` (75th percentile of rating distribution)
- `Installs ≥ category median`

Among this pool, report price-band counts + KDE overlays for the top-5 paid-app categories. The recommendation is the price range with the highest density of winners, category-by-category.

## 5. Ratings drivers

Primary model — OLS with category fixed effects:

```
Rating ~ is_paid + log_installs + log_size_mb + log_reviews + age_days + reviews_per_install + C(category)
```

Coefficients reported with 95% CIs. A **Ridge** regressor with standardized features provides a shrinkage sanity check. Both are linear.

A **LightGBM** regressor + **SHAP** summary plot serves as a non-linear robustness check. The headline — *"Linear and tree-based models agree on the top drivers"* — is only claimed if the top-3 features by OLS |coef| and by LightGBM importance overlap in ≥2 slots.

## 6. NLP sentiment

VADER (NLTK) compound scores are computed over the full review text. VADER is a lexicon + rule-based sentiment scorer; its advantages are that it runs without a model download and handles negation and intensifiers reasonably. It under-performs transformer models on sarcasm and domain-specific language, which is a knowing trade for deployment simplicity.

**Pain-point extraction** — filter reviews with `compound < -0.3`, group by category, and extract top-TF-IDF bigrams with `sklearn.feature_extraction.text.TfidfVectorizer(ngram_range=(2,2), stop_words="english", min_df=5)`. Categories with fewer than 50 negative reviews are dropped.

## 7. Category opportunity scoring

Per-category signals, all positive = more opportunity:

| Signal | Definition |
|---|---|
| **Demand** | mean `log_installs` |
| **Quality gap** | 1 − median `Rating` |
| **Supply gap** | 1 / log(app count + 1) |
| **Monetization** | pct-paid × median paid price |

Each is min-max normalized to `[0, 1]`; composite score is a normalized weighted sum. Three weight schemes (balanced, growth-tilted, monetization-tilted) are evaluated and the pairwise **Kendall τ** of the resulting rankings is reported as a stability measure.

## 8. Acquisition shortlist

Within the top-5 scoring categories, filter to apps that pass:

- `Rating ≥ 4.3`, `Installs ≥ 100,000`, `Reviews ≥ 5,000`, `Last Updated ≤ 24 months before snapshot`.

Rank by `Rating × log(Installs + 1) × (1 − pct_negative_reviews)`.

**Explicit caveat**: Google Play data has no revenue, DAU, retention, or churn. This shortlist is a **demand-side screen**, not a financial model. A real Bending-Spoons-style acquisition evaluation would layer SensorTower / data.ai revenue estimates and cohort retention data on top.

## 9. Limitations

- 2018 snapshot; product-category mix and price distributions may look different in 2025.
- `Installs` is a coarse bucket, not a count. All install-based comparisons are ordinal.
- Review corpus covers ~10% of apps; NLP conclusions are scoped to that sample and skew towards widely-reviewed apps.
- VADER is a pragmatic sentiment tool; a transformer fine-tuned on app reviews would likely recover 3–6 pp of classification accuracy on sarcastic text.
- No revenue data. "Acquisition shortlist" is a demand proxy.
- No causal identification — the OLS coefficients are associations, not treatment effects.
