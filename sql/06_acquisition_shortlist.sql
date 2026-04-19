-- Business question:
--   Demand-side acquisition shortlist: apps that are well-loved, well-sized,
--   recently maintained, and live in a high-opportunity category.
--
--   Caveat: Google Play has no revenue/DAU/churn; this is a demand-side
--   screen, not a financial one.
--
-- Technique: multi-CTE filter chain.

WITH cat_scores AS (
    SELECT
        category,
        AVG(log_installs)      AS demand,
        1 - MEDIAN(Rating)     AS quality_gap,
        1.0 / LN(COUNT(*) + 1) AS supply_gap,
        AVG(CAST(is_paid AS DOUBLE))
            * COALESCE(MEDIAN(CASE WHEN is_paid = 1 THEN price_usd END), 0) AS monetization
    FROM apps
    WHERE Rating IS NOT NULL
    GROUP BY category
    HAVING COUNT(*) >= 20
),
ranked_cats AS (
    SELECT category, demand + quality_gap + 0.5 * supply_gap + 0.75 * monetization AS opportunity
    FROM cat_scores
),
top_cats AS (
    SELECT category
    FROM ranked_cats
    ORDER BY opportunity DESC
    LIMIT 5
),
snapshot AS (SELECT MAX(last_updated) AS dt FROM apps),
candidates AS (
    SELECT
        a.App,
        a.category,
        a.Rating,
        a.installs,
        a.reviews,
        a.price_usd,
        a.last_updated,
        a.mean_compound,
        a.pct_negative
    FROM apps a
    JOIN top_cats USING (category)
    CROSS JOIN snapshot s
    WHERE a.Rating >= 4.3
      AND a.installs >= 100000
      AND a.reviews >= 5000
      AND a.last_updated >= (s.dt - INTERVAL 24 MONTH)
)
SELECT
    App,
    category,
    Rating,
    installs,
    reviews,
    price_usd,
    last_updated,
    ROUND(Rating * LN(installs + 1) * (1 - COALESCE(pct_negative, 0.5)), 3) AS shortlist_score
FROM candidates
ORDER BY shortlist_score DESC
LIMIT 20;
