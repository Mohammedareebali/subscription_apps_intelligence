-- Business question:
--   Top 5 apps in each category on a composite "liked & big" score
--   (rating × log(installs + 1)). Keep only apps with >=5k reviews to
--   reject rating-inflation from small samples.
--
-- Technique: window ROW_NUMBER() partitioned by category, with QUALIFY.

SELECT
    category,
    App,
    Rating,
    installs,
    reviews,
    ROUND(Rating * LN(installs + 1), 3) AS liked_and_big,
    ROW_NUMBER() OVER (
        PARTITION BY category
        ORDER BY Rating * LN(installs + 1) DESC
    ) AS rnk
FROM apps
WHERE Rating IS NOT NULL
  AND reviews >= 5000
QUALIFY rnk <= 5
ORDER BY category, rnk;
