-- Business question:
--   Which categories are well-rated *where installs actually concentrate*?
--   Simple averages treat a 100-install app the same as a 10M-install app;
--   we want an install-weighted view, then rank categories.
--
-- Technique: weighted aggregation + window rank.

WITH weighted AS (
    SELECT
        category,
        COUNT(*)                                                      AS n_apps,
        AVG(Rating)                                                   AS mean_rating,
        SUM(installs * Rating) / NULLIF(SUM(installs), 0)             AS install_weighted_rating,
        SUM(installs)                                                 AS total_installs
    FROM apps
    WHERE Rating IS NOT NULL
    GROUP BY category
    HAVING COUNT(*) >= 30
)
SELECT
    category,
    n_apps,
    ROUND(mean_rating, 3)                           AS mean_rating,
    ROUND(install_weighted_rating, 3)               AS install_weighted_rating,
    total_installs,
    RANK() OVER (ORDER BY install_weighted_rating DESC)   AS rank_install_weighted,
    RANK() OVER (ORDER BY mean_rating DESC)               AS rank_simple_mean
FROM weighted
ORDER BY install_weighted_rating DESC
LIMIT 20;
