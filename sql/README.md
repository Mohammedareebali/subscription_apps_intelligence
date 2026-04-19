# SQL layer

DuckDB queries over the processed parquet files in `../data/processed/`. Each query answers a discrete business question, is ANSI-friendly where possible, and uses at least one technique a data-team would expect: CTEs, window functions, percentile aggregations, pivots, or anti-joins.

## Run

```bash
cd ..  # project root
duckdb < sql/00_setup.sql  # creates views
duckdb < sql/01_top_categories_by_install_weighted_rating.sql
# …etc.
```

Or from a single session:

```bash
duckdb -c ".read sql/00_setup.sql" -c ".read sql/01_top_categories_by_install_weighted_rating.sql"
```

## Queries

| # | File | Business question | Techniques |
|---|------|-------------------|------------|
| 00 | `00_setup.sql` | Materialize parquet files as views | DDL |
| 01 | `01_top_categories_by_install_weighted_rating.sql` | Which categories are well-rated *where it matters* (install-weighted)? | Window `RANK()`, weighted aggregation |
| 02 | `02_pricing_sweet_spot.sql` | Among successful paid apps, what price deciles concentrate quality? | `PERCENTILE_CONT`, filter + segment |
| 03 | `03_paid_vs_free_by_category.sql` | Where is the paid premium largest? | CTE chain, within-group aggregation |
| 04 | `04_top_apps_within_category.sql` | Rank top-N apps within each category on a composite score | Window `ROW_NUMBER() OVER (PARTITION BY …)`, `QUALIFY` |
| 05 | `05_price_band_pivot.sql` | Rating × price-band matrix to eyeball the sweet spot | `PIVOT` |
| 06 | `06_acquisition_shortlist.sql` | Which apps pass a rule-based demand-side shortlist? | CTE chain, multi-condition filter |
| 07 | `07_category_opportunity_score.sql` | SQL implementation of the composite opportunity score | CTE chain, min-max normalization |
| 08 | `08_sentiment_rollup_by_category.sql` | Which categories have the largest gap between star ratings and review sentiment? | JOIN, aggregation, derived measure |
