-- Business question:
--   Which categories have the largest gap between star ratings and review
--   sentiment? A large gap suggests either rating-inflation (stars don't
--   reflect text) or rating-deflation (text is fine, stars aren't).
--
-- Technique: join, aggregate, derived measure.

WITH joined AS (
    SELECT
        a.category,
        a.App,
        a.Rating,
        r.vader_compound
    FROM apps a
    JOIN reviews r USING (App)
    WHERE a.Rating IS NOT NULL
)
SELECT
    category,
    COUNT(*)                                             AS n_reviews,
    COUNT(DISTINCT App)                                  AS n_apps_with_reviews,
    ROUND(AVG(Rating), 3)                                AS mean_star_rating,
    ROUND(AVG(vader_compound), 3)                        AS mean_sentiment,
    ROUND(AVG(Rating) / 5.0 - (AVG(vader_compound) + 1) / 2.0, 3)
                                                         AS star_vs_sentiment_gap
FROM joined
GROUP BY category
HAVING COUNT(*) >= 200
ORDER BY star_vs_sentiment_gap DESC;
