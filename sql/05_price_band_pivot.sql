-- Business question:
--   Rating × price-band heat-map-ready table. Rows are categories (top 10
--   by app count), columns are price bands, values are mean ratings.
--
-- Technique: PIVOT.

WITH top_cats AS (
    SELECT category
    FROM apps
    GROUP BY category
    ORDER BY COUNT(*) DESC
    LIMIT 10
),
base AS (
    SELECT
        a.category,
        a.price_band,
        a.Rating
    FROM apps a
    JOIN top_cats t USING (category)
    WHERE a.Rating IS NOT NULL
)
PIVOT base
    ON price_band IN ('Free', '$0.01-0.99', '$1.00-2.99', '$3.00-4.99', '$5.00-9.99', '$10.00+')
    USING ROUND(AVG(Rating), 2) AS mean_rating
    GROUP BY category
ORDER BY category;
