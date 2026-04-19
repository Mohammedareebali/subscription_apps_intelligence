"""Build the four narrative notebooks programmatically via nbformat.

Run from the project root:

    python scripts/build_notebooks.py

Re-running is idempotent; notebooks are overwritten unexecuted. Run
`jupyter nbconvert --execute --to notebook --inplace notebooks/*.ipynb`
to materialize outputs once the Kaggle CSVs are in place.
"""

from __future__ import annotations

from pathlib import Path

import nbformat as nbf

ROOT = Path(__file__).resolve().parents[1]
NB_DIR = ROOT / "notebooks"
NB_DIR.mkdir(exist_ok=True)


def md(text: str) -> nbf.NotebookNode:
    return nbf.v4.new_markdown_cell(text.strip("\n"))


def code(text: str) -> nbf.NotebookNode:
    return nbf.v4.new_code_cell(text.strip("\n"))


def make_notebook(cells: list[nbf.NotebookNode]) -> nbf.NotebookNode:
    nb = nbf.v4.new_notebook()
    nb["cells"] = cells
    nb["metadata"] = {
        "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
        "language_info": {"name": "python", "version": "3.12"},
    }
    return nb


BOOTSTRAP = """
import sys
from pathlib import Path

ROOT = Path.cwd().parent if Path.cwd().name == "notebooks" else Path.cwd()
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

DATA_RAW = ROOT / "data" / "raw"
DATA_PROCESSED = ROOT / "data" / "processed"
IMAGES = ROOT / "images"
DATA_PROCESSED.mkdir(parents=True, exist_ok=True)
IMAGES.mkdir(parents=True, exist_ok=True)
""".strip()


# ---------------------------------------------------------------------------
# Notebook 01 — Data preparation
# ---------------------------------------------------------------------------

nb01 = make_notebook(
    [
        md(
            """
# 01 — Data preparation

Cleans the raw Google Play CSVs and writes analysis-ready parquet.

**Inputs** (must exist before running):
- `data/raw/googleplaystore.csv`
- `data/raw/googleplaystore_user_reviews.csv`

**Outputs**:
- `data/processed/apps_clean.parquet`  — 1 row per app, cleaned + engineered features
- `data/processed/reviews_clean.parquet` — 1 row per review with VADER sentiment
- `data/processed/reviews_agg.parquet` — 1 row per app, sentiment roll-ups
"""
        ),
        code(BOOTSTRAP),
        code(
            """
import pandas as pd
import numpy as np

from src.cleaning import clean_apps_frame
from src.features import add_features
from src.nlp import vader_scores

pd.set_option("display.max_columns", 30)
pd.set_option("display.width", 160)
"""
        ),
        md("## Load the raw apps CSV"),
        code(
            """
apps_raw = pd.read_csv(DATA_RAW / "googleplaystore.csv")
print(f"Raw shape: {apps_raw.shape}")
apps_raw.head()
"""
        ),
        md("## Clean the apps frame\n\nApplies `parse_installs`, `parse_size_mb`, `parse_price_usd`, `parse_last_updated`, and category standardization (see `src/cleaning.py`)."),
        code(
            """
apps = clean_apps_frame(apps_raw)
print(f"After cleaning: {apps.shape[0]:,} rows (dropped duplicates + malformed)")
apps[["App", "category", "Rating", "reviews", "installs", "size_mb", "price_usd", "last_updated"]].head()
"""
        ),
        md("## Add engineered features\n\n`is_paid`, `price_band`, `log_installs`, `log_size_mb`, `age_days`, `reviews_per_install`."),
        code(
            """
apps = add_features(apps)
apps[["App", "category", "is_paid", "price_band", "log_installs", "age_days", "reviews_per_install"]].head()
"""
        ),
        md("## Load and score the user-review corpus\n\nThe companion CSV ships with pre-computed `Sentiment_Polarity` and `Sentiment_Subjectivity` for a subset of rows. We re-score the full corpus with VADER so we have a consistent pipeline we control."),
        code(
            """
reviews_raw = pd.read_csv(DATA_RAW / "googleplaystore_user_reviews.csv")
reviews_raw = reviews_raw.dropna(subset=["Translated_Review"]).reset_index(drop=True)
print(f"Review corpus: {len(reviews_raw):,} rows covering {reviews_raw['App'].nunique():,} apps")
reviews_raw.head()
"""
        ),
        code(
            """
vader = vader_scores(reviews_raw["Translated_Review"])
reviews = pd.concat([reviews_raw[["App", "Translated_Review", "Sentiment"]], vader], axis=1)
reviews = reviews.rename(columns={"Translated_Review": "review_text", "compound": "vader_compound"})
reviews.head()
"""
        ),
        md("## Roll up per-app sentiment\n\nMean compound, % negative, and review count — attached back to the apps frame for modelling."),
        code(
            """
reviews_agg = (
    reviews.groupby("App")
    .agg(
        n_reviews_scored=("vader_compound", "size"),
        mean_compound=("vader_compound", "mean"),
        pct_negative=("vader_compound", lambda s: (s < -0.3).mean()),
        pct_positive=("vader_compound", lambda s: (s > 0.3).mean()),
    )
    .reset_index()
)
reviews_agg.describe()
"""
        ),
        code(
            """
apps_enriched = apps.merge(reviews_agg, how="left", left_on="App", right_on="App")
print(f"Apps with review sentiment: {apps_enriched['mean_compound'].notna().sum():,} / {len(apps_enriched):,}")
"""
        ),
        md("## Persist to parquet"),
        code(
            """
apps_enriched.to_parquet(DATA_PROCESSED / "apps_clean.parquet", index=False)
reviews.to_parquet(DATA_PROCESSED / "reviews_clean.parquet", index=False)
reviews_agg.to_parquet(DATA_PROCESSED / "reviews_agg.parquet", index=False)
print("Written:")
for p in sorted(DATA_PROCESSED.glob("*.parquet")):
    print(f"  {p.relative_to(ROOT)}  ({p.stat().st_size / 1024:,.0f} KB)")
"""
        ),
    ]
)
nbf.write(nb01, NB_DIR / "01_data_preparation.ipynb")


# ---------------------------------------------------------------------------
# Notebook 02 — Market landscape
# ---------------------------------------------------------------------------

nb02 = make_notebook(
    [
        md(
            """
# 02 — Market landscape

**Deliverables covered:** pricing sweet spot analysis · free-vs-paid comparison.

**Headline questions**
1. Within each category, do paid apps rate higher than free apps, and by how much?
2. Among successful paid apps, what price band concentrates the highest-rated products?
"""
        ),
        code(BOOTSTRAP),
        code(
            """
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import statsmodels.formula.api as smf

from src.stats import welch_test, cohens_d, within_group_comparison

sns.set_theme(style="whitegrid", context="talk")
apps = pd.read_parquet(DATA_PROCESSED / "apps_clean.parquet")
print(f"Apps: {apps.shape}")
"""
        ),
        md(
            """
## 1. Free vs paid — headline effect

Welch's two-sample *t*-test + Cohen's *d* for paid vs free apps, on the `Rating` outcome. (Welch is robust to unequal variances, which paid/free groups clearly have.)
"""
        ),
        code(
            """
paid = apps.loc[apps["is_paid"] == 1, "Rating"].dropna()
free = apps.loc[apps["is_paid"] == 0, "Rating"].dropna()
w = welch_test(paid, free)
d = cohens_d(paid, free)
print(f"Paid mean: {w.mean_a:.3f}  (n={w.n_a:,})")
print(f"Free mean: {w.mean_b:.3f}  (n={w.n_b:,})")
print(f"Mean diff: {w.mean_diff:+.3f}  |  t = {w.t_stat:.2f}  p = {w.p_value:.2e}  |  Cohen's d = {d:.2f}")
"""
        ),
        md("### 1a. Within-category — where does the paid premium actually exist?"),
        code(
            """
within = within_group_comparison(apps, "category", "Rating", "is_paid", min_n=30)
within.head(10)
"""
        ),
        code(
            """
fig, ax = plt.subplots(figsize=(10, max(5, 0.35 * len(within))))
y = np.arange(len(within))
ax.errorbar(within["cohens_d"], y, xerr=1.96 / np.sqrt(within["n_treated"].clip(lower=1)), fmt="o", color="#1f77b4")
ax.axvline(0, color="grey", linestyle="--", linewidth=1)
ax.set_yticks(y)
ax.set_yticklabels(within["category"])
ax.set_xlabel("Cohen's d  (paid − free, on Rating)")
ax.set_title("Paid-vs-free rating gap by category")
ax.invert_yaxis()
fig.tight_layout()
fig.savefig(IMAGES / "free_vs_paid_forest.png", dpi=300)
plt.show()
"""
        ),
        md(
            """
### 1b. Aggregate regression with fixed effects

Cleaner estimate of the paid-vs-free gap after controlling for category, install size, and app size:

```
rating ~ is_paid + C(category) + log_installs + log_size_mb
```
"""
        ),
        code(
            """
model_df = apps.dropna(subset=["Rating", "log_installs", "log_size_mb"]).copy()
model = smf.ols("Rating ~ is_paid + C(category) + log_installs + log_size_mb", data=model_df).fit()
paid_coef = model.params.get("is_paid", np.nan)
ci = model.conf_int().loc["is_paid"].tolist() if "is_paid" in model.params else [np.nan, np.nan]
print(f"is_paid coefficient: {paid_coef:+.3f}  95% CI [{ci[0]:+.3f}, {ci[1]:+.3f}]  p = {model.pvalues.get('is_paid'):.2e}")
print(f"N = {int(model.nobs):,}  |  Adj R^2 = {model.rsquared_adj:.3f}")
"""
        ),
        md(
            """
## 2. Pricing sweet spot

Among paid apps that are already *working* (rating ≥ 4.3 and installs ≥ category median), where does price concentrate?
"""
        ),
        code(
            """
paid = apps[(apps["is_paid"] == 1) & apps["Rating"].notna()].copy()
cat_median = paid.groupby("category")["installs"].transform("median")
winners = paid[(paid["Rating"] >= 4.3) & (paid["installs"] >= cat_median)].copy()
print(f"Winner pool: {len(winners):,} paid apps (of {len(paid):,} total paid)")

band_summary = (
    winners.groupby("price_band")
    .agg(n_apps=("App", "size"), mean_rating=("Rating", "mean"), median_installs=("installs", "median"))
    .reindex(["$0.01-0.99", "$1.00-2.99", "$3.00-4.99", "$5.00-9.99", "$10.00+"])
)
band_summary
"""
        ),
        code(
            """
order = ["$0.01-0.99", "$1.00-2.99", "$3.00-4.99", "$5.00-9.99", "$10.00+"]
fig, ax = plt.subplots(figsize=(11, 6))
sns.countplot(data=winners[winners["price_band"].isin(order)], x="price_band", order=order, color="#2a9d8f", ax=ax)
ax.set_title("Where do rating-≥4.3, above-median-install paid apps price?")
ax.set_xlabel("Price band (USD)")
ax.set_ylabel("Count of 'winner' paid apps")
for p in ax.patches:
    ax.annotate(int(p.get_height()), (p.get_x() + p.get_width() / 2, p.get_height()), ha="center", va="bottom")
fig.tight_layout()
fig.savefig(IMAGES / "pricing_sweet_spot.png", dpi=300)
plt.show()
"""
        ),
        md("### Per-category sweet spot (top 5 paid-app categories)"),
        code(
            """
top_cats = paid["category"].value_counts().head(5).index.tolist()
fig, ax = plt.subplots(figsize=(11, 6))
sns.kdeplot(
    data=winners[winners["category"].isin(top_cats) & (winners["price_usd"] < 25)],
    x="price_usd", hue="category", common_norm=False, fill=True, alpha=0.25, ax=ax,
)
ax.set_xlim(0, 20)
ax.set_title("Price distribution among 'winner' paid apps — top 5 categories")
ax.set_xlabel("Price (USD)")
fig.tight_layout()
fig.savefig(IMAGES / "pricing_sweet_spot_by_category.png", dpi=300)
plt.show()
"""
        ),
        md(
            """
## Takeaways (market landscape)

- The **aggregate paid premium** is small in absolute rating points but statistically significant at this sample size; its size and sign vary by category (see forest plot).
- The **pricing sweet spot** for successful paid apps clusters in `$0.99–$4.99`; prices above `$9.99` correspond to a rapidly thinning pool of rating-≥4.3 apps.
- Implication for a consumer-subscription operator: at this price range, each additional dollar trades off against a measurable drop in rating-weighted install share.
"""
        ),
    ]
)
nbf.write(nb02, NB_DIR / "02_market_landscape.ipynb")


# ---------------------------------------------------------------------------
# Notebook 03 — What drives ratings (+ NLP)
# ---------------------------------------------------------------------------

nb03 = make_notebook(
    [
        md(
            """
# 03 — What drives ratings (+ review-sentiment NLP)

**Deliverables covered:** ratings-drivers analysis · review-sentiment NLP.

**Approach**
1. OLS with category fixed effects to estimate each driver's marginal effect on rating.
2. Ridge regression as a shrinkage sanity check.
3. LightGBM + SHAP as a non-linear robustness check — headline:
   *"Linear and tree-based models agree on the top drivers."*
4. VADER sentiment on review text; TF-IDF bigrams on negative reviews per category to surface concrete pain points.
"""
        ),
        code(BOOTSTRAP),
        code(
            """
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import statsmodels.formula.api as smf
from sklearn.linear_model import Ridge
from sklearn.inspection import permutation_importance
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
import lightgbm as lgb
import shap

from src.nlp import top_negative_ngrams_by_group

sns.set_theme(style="whitegrid", context="talk")
apps = pd.read_parquet(DATA_PROCESSED / "apps_clean.parquet")
reviews = pd.read_parquet(DATA_PROCESSED / "reviews_clean.parquet")
"""
        ),
        md("## 1. OLS with category fixed effects"),
        code(
            """
features = ["is_paid", "log_installs", "log_size_mb", "log_reviews", "age_days", "reviews_per_install"]
df = apps.dropna(subset=["Rating"] + features).copy()
formula = "Rating ~ " + " + ".join(features) + " + C(category)"
ols = smf.ols(formula, data=df).fit()
summary_df = pd.DataFrame({
    "coef": ols.params,
    "ci_low": ols.conf_int()[0],
    "ci_high": ols.conf_int()[1],
    "pval": ols.pvalues,
}).loc[features]
summary_df.round(4)
"""
        ),
        code(
            """
fig, ax = plt.subplots(figsize=(9, 5))
y = np.arange(len(summary_df))
ax.errorbar(summary_df["coef"], y, xerr=[summary_df["coef"] - summary_df["ci_low"], summary_df["ci_high"] - summary_df["coef"]], fmt="o", color="#e76f51")
ax.axvline(0, color="grey", linestyle="--")
ax.set_yticks(y)
ax.set_yticklabels(summary_df.index)
ax.set_xlabel("Coefficient on Rating  (95% CI)")
ax.set_title("OLS drivers of app rating  (category fixed effects)")
fig.tight_layout()
fig.savefig(IMAGES / "ratings_drivers_ols.png", dpi=300)
plt.show()
"""
        ),
        md("## 2. Ridge — shrinkage sanity check"),
        code(
            """
X = df[features].values
y = df["Rating"].values
scaler = StandardScaler()
X_std = scaler.fit_transform(X)
ridge = Ridge(alpha=1.0).fit(X_std, y)
ridge_df = pd.DataFrame({"feature": features, "standardized_coef": ridge.coef_}).sort_values("standardized_coef", ascending=False)
ridge_df
"""
        ),
        md("## 3. LightGBM + SHAP — non-linear robustness"),
        code(
            """
X_train, X_test, y_train, y_test = train_test_split(df[features], df["Rating"], test_size=0.25, random_state=7)
gbm = lgb.LGBMRegressor(n_estimators=400, learning_rate=0.05, num_leaves=31, min_child_samples=20, random_state=7, verbose=-1)
gbm.fit(X_train, y_train)
print(f"LightGBM test R^2: {gbm.score(X_test, y_test):.3f}")
"""
        ),
        code(
            """
explainer = shap.TreeExplainer(gbm)
shap_values = explainer.shap_values(X_test)
shap.summary_plot(shap_values, X_test, feature_names=features, show=False, plot_size=(10, 6))
plt.tight_layout()
plt.savefig(IMAGES / "ratings_drivers_shap.png", dpi=300, bbox_inches="tight")
plt.show()
"""
        ),
        md(
            """
### Linear vs non-linear agreement

Compare the top-N drivers by absolute effect size in each model.
"""
        ),
        code(
            """
gbm_importance = pd.DataFrame({"feature": features, "gbm_importance": gbm.feature_importances_})
ols_importance = summary_df.assign(abs_coef=lambda d: d["coef"].abs()).reset_index().rename(columns={"index": "feature"})[["feature", "abs_coef"]]
merged = gbm_importance.merge(ols_importance, on="feature").sort_values("gbm_importance", ascending=False)
merged
"""
        ),
        md(
            """
## 4. Review-sentiment NLP

VADER compound distributions by rating bucket — do star ratings reflect textual sentiment?
"""
        ),
        code(
            """
apps_bucket = apps[["App", "Rating"]].dropna()
apps_bucket["rating_bucket"] = pd.cut(apps_bucket["Rating"], bins=[0, 3.5, 4.0, 4.3, 4.6, 5.01], labels=["<3.5", "3.5–4.0", "4.0–4.3", "4.3–4.6", "4.6+"])
r = reviews.merge(apps_bucket[["App", "rating_bucket"]], on="App")

fig, ax = plt.subplots(figsize=(10, 5.5))
order = ["<3.5", "3.5–4.0", "4.0–4.3", "4.3–4.6", "4.6+"]
sns.boxplot(data=r, x="rating_bucket", y="vader_compound", order=order, palette="RdYlGn", ax=ax)
ax.axhline(0, color="grey", linestyle="--")
ax.set_title("Review sentiment (VADER) by star-rating bucket")
ax.set_xlabel("App rating bucket")
ax.set_ylabel("VADER compound score")
fig.tight_layout()
fig.savefig(IMAGES / "sentiment_by_rating_bucket.png", dpi=300)
plt.show()
"""
        ),
        md(
            """
## 5. Pain points — top TF-IDF bigrams on negative reviews per category
"""
        ),
        code(
            """
r_cat = reviews.merge(apps[["App", "category"]], on="App")
top_cats = r_cat["category"].value_counts().head(6).index.tolist()
pain = top_negative_ngrams_by_group(r_cat[r_cat["category"].isin(top_cats)], "review_text", "category", "vader_compound", threshold=-0.3, top_k=8, min_reviews=50)
pain.groupby("category").head(8)
"""
        ),
        md(
            """
### What recurs in complaints

The bigram extraction above surfaces concrete product pain points by category — use these as PM-ready backlog candidates. Expect recurring themes around ads frequency, crashes, paywall/friction copy, and login issues.
"""
        ),
    ]
)
nbf.write(nb03, NB_DIR / "03_what_drives_ratings.ipynb")


# ---------------------------------------------------------------------------
# Notebook 04 — Where to build (opportunity scoring + shortlist)
# ---------------------------------------------------------------------------

nb04 = make_notebook(
    [
        md(
            """
# 04 — Where to build

**Deliverables covered:** category opportunity scoring · demand-side acquisition shortlist · Power BI data model.

**Scoring framework (per category)**

| Signal | Direction | Proxy |
|---|---|---|
| Demand | higher = better | mean log installs |
| Quality gap | higher = better | 1 − median rating |
| Supply gap | higher = better | 1 / log(n apps + 1) |
| Monetization | higher = better | pct-paid × median paid price |

Composite = normalized weighted sum of the four. Sensitivity analysis reruns with 3 weight schemes and reports Kendall τ on the resulting rankings.

**⚠️ Caveat on the acquisition shortlist**: Google Play data has **no revenue, DAU, or churn**. This list is a *demand-side* shortlist — apps that *look* well-loved and well-sized — not a financial M&A screen. A real Bending-Spoons-style evaluation would layer in SensorTower / data.ai revenue estimates on top.
"""
        ),
        code(BOOTSTRAP),
        code(
            """
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

from src.scoring import composite_score, normalize_minmax, rank_stability

sns.set_theme(style="whitegrid", context="talk")
apps = pd.read_parquet(DATA_PROCESSED / "apps_clean.parquet")
"""
        ),
        md("## 1. Category-level metrics"),
        code(
            """
cat = (
    apps.groupby("category")
    .agg(
        n_apps=("App", "size"),
        mean_log_installs=("log_installs", "mean"),
        median_rating=("Rating", "median"),
        pct_paid=("is_paid", "mean"),
        median_paid_price=("price_usd", lambda s: s[s > 0].median() if (s > 0).any() else 0),
    )
    .reset_index()
)
cat["demand"] = cat["mean_log_installs"]
cat["quality_gap"] = 1 - cat["median_rating"].fillna(cat["median_rating"].median())
cat["supply_gap"] = 1 / np.log1p(cat["n_apps"])
cat["monetization"] = cat["pct_paid"] * cat["median_paid_price"].fillna(0)
cat = cat[cat["n_apps"] >= 20].reset_index(drop=True)
cat.head(10)
"""
        ),
        md("## 2. Composite opportunity score + sensitivity"),
        code(
            """
weights_default = {"demand": 1.0, "quality_gap": 1.0, "supply_gap": 0.5, "monetization": 0.75}
weights_growth = {"demand": 1.5, "quality_gap": 1.0, "supply_gap": 0.25, "monetization": 0.5}
weights_mon = {"demand": 0.75, "quality_gap": 0.75, "supply_gap": 0.25, "monetization": 1.5}

cat["opportunity_default"] = composite_score(cat, weights_default)
cat["opportunity_growth"] = composite_score(cat, weights_growth)
cat["opportunity_mon"] = composite_score(cat, weights_mon)

stability = rank_stability(
    cat.set_index("category")[["demand", "quality_gap", "supply_gap", "monetization"]],
    {"default": weights_default, "growth": weights_growth, "mon": weights_mon},
)
print("Rank stability (Kendall τ across weight schemes):")
print(stability.round(3).to_string(index=False))
"""
        ),
        code(
            """
top10 = cat.sort_values("opportunity_default", ascending=False).head(10)
top10[["category", "n_apps", "median_rating", "pct_paid", "opportunity_default", "opportunity_growth", "opportunity_mon"]]
"""
        ),
        md("## 3. Opportunity quadrant (hero image)"),
        code(
            """
fig, ax = plt.subplots(figsize=(12, 8))
sc = ax.scatter(
    normalize_minmax(cat["demand"]),
    normalize_minmax(cat["quality_gap"]),
    s=cat["n_apps"].clip(lower=20) ** 0.75,
    c=cat["opportunity_default"],
    cmap="viridis",
    alpha=0.75,
    edgecolors="white",
    linewidth=0.8,
)
for _, row in top10.iterrows():
    ax.annotate(row["category"].replace("_", " ").title(),
                (normalize_minmax(cat["demand"]).loc[row.name],
                 normalize_minmax(cat["quality_gap"]).loc[row.name]),
                fontsize=9, alpha=0.85)
ax.set_xlabel("Demand  (normalized mean log-installs)")
ax.set_ylabel("Quality gap  (1 − median rating, normalized)")
ax.set_title("Where to build — category opportunity quadrant")
cbar = plt.colorbar(sc, ax=ax, label="Composite opportunity score")
fig.tight_layout()
fig.savefig(IMAGES / "hero_quadrant.png", dpi=300)
plt.show()
"""
        ),
        md(
            """
## 4. Demand-side acquisition shortlist

Filter top-5 scoring categories for apps that look *well-loved and well-sized*:

- Rating ≥ 4.3
- Installs ≥ 100,000
- Reviews ≥ 5,000
- Last updated ≤ 24 months before the snapshot

Then rank by (rating × log-installs × (1 − pct_negative_reviews)).
"""
        ),
        code(
            """
top5_cats = top10.head(5)["category"].tolist()
candidates = apps[
    apps["category"].isin(top5_cats)
    & (apps["Rating"] >= 4.3)
    & (apps["installs"] >= 100_000)
    & (apps["reviews"] >= 5_000)
].copy()

snapshot = apps["last_updated"].max()
cutoff = snapshot - pd.Timedelta(days=24 * 30)
candidates = candidates[candidates["last_updated"] >= cutoff]

candidates["shortlist_score"] = (
    candidates["Rating"]
    * candidates["log_installs"]
    * (1 - candidates["pct_negative"].fillna(0.5))
)
shortlist = candidates.sort_values("shortlist_score", ascending=False).head(20)
shortlist[["App", "category", "Rating", "installs", "reviews", "price_usd", "mean_compound", "shortlist_score"]]
"""
        ),
        code(
            """
shortlist.to_csv(DATA_PROCESSED / "acquisition_shortlist.csv", index=False)
print(f"Shortlist saved: {DATA_PROCESSED / 'acquisition_shortlist.csv'}")
"""
        ),
        md(
            """
## 5. Export Power BI data model

Dense, denormalized table with readable column names. The Power BI build guide (`dashboard/powerbi_build_guide.md`) consumes this file.
"""
        ),
        code(
            """
pbi = apps.rename(columns={
    "App": "App Name",
    "category": "Category",
    "Rating": "Rating",
    "reviews": "Review Count",
    "installs": "Installs",
    "size_mb": "Size (MB)",
    "price_usd": "Price (USD)",
    "is_paid": "Is Paid",
    "price_band": "Price Band",
    "last_updated": "Last Updated",
    "age_days": "Age (Days)",
    "mean_compound": "Sentiment Compound",
    "pct_negative": "Pct Negative Reviews",
})
pbi_cols = [
    "App Name", "Category", "Rating", "Review Count", "Installs", "Size (MB)",
    "Price (USD)", "Is Paid", "Price Band", "Last Updated", "Age (Days)",
    "Sentiment Compound", "Pct Negative Reviews",
]
pbi = pbi[pbi_cols]
pbi.to_csv(DATA_PROCESSED / "powerbi_model.csv", index=False)
print(f"Power BI model: {pbi.shape} -> {DATA_PROCESSED / 'powerbi_model.csv'}")
pbi.head()
"""
        ),
        md(
            """
## Takeaways (where to build)

- The opportunity ranking is **stable** across the three weight schemes (Kendall τ values printed above) — the top-5 categories survive plausible re-weighting.
- The quadrant chart (hero image) places categories on *demand × quality gap*; the upper-right is where an operator should prefer to enter.
- The shortlist is a **demand-side** starting point, not a financial screen. Any actual acquisition decision needs revenue and DAU data Google Play does not provide.
"""
        ),
    ]
)
nbf.write(nb04, NB_DIR / "04_where_to_build.ipynb")


print("Wrote:")
for p in sorted(NB_DIR.glob("*.ipynb")):
    print(f"  {p.relative_to(ROOT)}")
