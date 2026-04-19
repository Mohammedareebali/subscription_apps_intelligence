-- Business question:
--   Where is the paid-app rating premium largest, by category?
--   Report mean rating for paid vs free, the gap, and sample sizes.
--
-- Technique: CTE chain, conditional aggregation.

WITH paid_stats AS (
    SELECT category, AVG(Rating) AS paid_mean, COUNT(*) AS n_paid
    FROM apps
    WHERE is_paid = 1 AND Rating IS NOT NULL
    GROUP BY category
),
free_stats AS (
    SELECT category, AVG(Rating) AS free_mean, COUNT(*) AS n_free
    FROM apps
    WHERE is_paid = 0 AND Rating IS NOT NULL
    GROUP BY category
),
joined AS (
    SELECT
        p.category,
        p.paid_mean,
        f.free_mean,
        p.paid_mean - f.free_mean AS paid_premium,
        p.n_paid,
        f.n_free
    FROM paid_stats p
    JOIN free_stats f USING (category)
    WHERE p.n_paid >= 30 AND f.n_free >= 30
)
SELECT
    category,
    ROUND(paid_mean, 3)    AS paid_mean,
    ROUND(free_mean, 3)    AS free_mean,
    ROUND(paid_premium, 3) AS paid_premium,
    n_paid,
    n_free
FROM joined
ORDER BY paid_premium DESC;
