-- Materialize the processed parquet files as views so the rest of the SQL
-- reads naturally. DuckDB's parquet reader is zero-copy, so these views
-- cost effectively nothing.

CREATE OR REPLACE VIEW apps AS
SELECT *
FROM read_parquet('data/processed/apps_clean.parquet');

CREATE OR REPLACE VIEW reviews AS
SELECT *
FROM read_parquet('data/processed/reviews_clean.parquet');

CREATE OR REPLACE VIEW reviews_agg AS
SELECT *
FROM read_parquet('data/processed/reviews_agg.parquet');

SELECT 'apps' AS tbl, COUNT(*) AS n FROM apps
UNION ALL SELECT 'reviews', COUNT(*) FROM reviews
UNION ALL SELECT 'reviews_agg', COUNT(*) FROM reviews_agg;
