-- Business question:
--   Among "winner" paid apps (rating >= 4.3 AND installs >= category median),
--   what does the price distribution look like?
--
-- Technique: percentile aggregations with PERCENTILE_CONT on a filtered pool.

WITH cat_medians AS (
    SELECT category, MEDIAN(installs) AS median_installs
    FROM apps
    WHERE is_paid = 1
    GROUP BY category
),
winners AS (
    SELECT a.*
    FROM apps a
    JOIN cat_medians m USING (category)
    WHERE a.is_paid = 1
      AND a.Rating >= 4.3
      AND a.installs >= m.median_installs
)
SELECT
    COUNT(*) AS n_winners,
    ROUND(PERCENTILE_CONT(0.10) WITHIN GROUP (ORDER BY price_usd), 2) AS p10_price,
    ROUND(PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY price_usd), 2) AS p25_price,
    ROUND(PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY price_usd), 2) AS median_price,
    ROUND(PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY price_usd), 2) AS p75_price,
    ROUND(PERCENTILE_CONT(0.90) WITHIN GROUP (ORDER BY price_usd), 2) AS p90_price,
    ROUND(AVG(price_usd), 2) AS mean_price
FROM winners;
