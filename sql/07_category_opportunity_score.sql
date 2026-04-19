-- Business question:
--   Rank every category on a composite opportunity score, with the
--   component signals broken out so the ranking is explainable.
--
-- Technique: CTE chain + min-max normalization in SQL.

WITH cat_raw AS (
    SELECT
        category,
        COUNT(*)                AS n_apps,
        AVG(log_installs)       AS demand,
        1 - MEDIAN(Rating)      AS quality_gap,
        1.0 / LN(COUNT(*) + 1)  AS supply_gap,
        AVG(CAST(is_paid AS DOUBLE))
            * COALESCE(MEDIAN(CASE WHEN is_paid = 1 THEN price_usd END), 0) AS monetization
    FROM apps
    WHERE Rating IS NOT NULL
    GROUP BY category
    HAVING COUNT(*) >= 20
),
bounds AS (
    SELECT
        MIN(demand) AS dm_lo, MAX(demand) AS dm_hi,
        MIN(quality_gap) AS qg_lo, MAX(quality_gap) AS qg_hi,
        MIN(supply_gap) AS sg_lo, MAX(supply_gap) AS sg_hi,
        MIN(monetization) AS mo_lo, MAX(monetization) AS mo_hi
    FROM cat_raw
),
scored AS (
    SELECT
        c.category,
        c.n_apps,
        (c.demand        - b.dm_lo) / NULLIF(b.dm_hi - b.dm_lo, 0) AS demand_n,
        (c.quality_gap   - b.qg_lo) / NULLIF(b.qg_hi - b.qg_lo, 0) AS quality_gap_n,
        (c.supply_gap    - b.sg_lo) / NULLIF(b.sg_hi - b.sg_lo, 0) AS supply_gap_n,
        (c.monetization  - b.mo_lo) / NULLIF(b.mo_hi - b.mo_lo, 0) AS monetization_n
    FROM cat_raw c CROSS JOIN bounds b
)
SELECT
    category,
    n_apps,
    ROUND(demand_n, 3)       AS demand,
    ROUND(quality_gap_n, 3)  AS quality_gap,
    ROUND(supply_gap_n, 3)   AS supply_gap,
    ROUND(monetization_n, 3) AS monetization,
    ROUND(
        (1.0   * demand_n
         + 1.0 * quality_gap_n
         + 0.5 * supply_gap_n
         + 0.75 * monetization_n) / 3.25,
        3
    ) AS opportunity_score
FROM scored
ORDER BY opportunity_score DESC;
