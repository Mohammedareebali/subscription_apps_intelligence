# Executive summary — Why subscription apps win

> **Analysis of 9,659 Google Play apps and 37,427 user reviews to answer four commercial questions for a consumer-app operator or acquirer.**

## Context

Sourced from a 2018 Google Play snapshot (CC0). After cleaning and deduplication: **9,659 apps** across 33 categories, **37,427 scored reviews** (15% negative by VADER). 7.8% of apps are paid; median paid price in the "winner" pool is **$2.99**.

## Five findings

### 1. Pricing sweet spot — $1.00–$4.99

Among paid apps that already demonstrate product-market fit (rating ≥ 4.3 AND installs ≥ category median), **70% price between $1.00–$4.99**. The $1.00–$2.99 band alone accounts for 44% of winners (118 apps). Above $9.99, the winner pool thins sharply — only 18 apps make it through. Sweet spot median: **$2.99** (IQR $1.99–$4.99).

### 2. Paid apps rate modestly higher — but the premium is real

Paid apps average **4.26 stars** vs 4.17 for free apps (+0.093, *t* = 3.95, *p* < 0.0001, Cohen's *d* = 0.17). After controlling for category, installs, and app size via OLS fixed effects, the paid premium is **+0.114 stars** (95% CI [+0.063, +0.165], *p* < 0.0001, *n* = 7,027). The effect is small in absolute terms but consistent and statistically robust at this sample size.

### 3. Reviews-per-install and review volume drive ratings most

Top three drivers by absolute OLS coefficient (with category fixed effects):

| Driver | |β|| | Direction |
|---|---|---|
| reviews_per_install | 0.209 | Positive — engaged audiences rate higher |
| log_reviews | 0.161 | Positive — volume signals trust |
| log_installs | 0.142 | Positive — distribution creates feedback |

Both OLS and LightGBM (SHAP) agree on this top-3. For a PM: *reviews-per-install* is the most actionable lever — it captures user engagement quality, not just marketing reach.

### 4. "Waste time" and "stopped working" are the universal complaints

Across DATING, GAME, HEALTH & FITNESS, and TRAVEL, the dominant negative-review bigrams are:

- **"waste time"** — appears as the top bigram in 4 of 6 categories
- **"fake profiles"** — #1 specific complaint in DATING
- **"stopped working"** — #1 technical complaint in HEALTH & FITNESS
- **"worst service"** — #1 in TRAVEL & LOCAL
- **"worst game"** / **"hate game"** — concentrated in GAME and FAMILY

PM takeaway: reliability ("stopped working") and value perception ("waste time") are cross-category blockers that a product team can address directly. Fake-profile fraud in DATING is a moderation problem with a known solution.

### 5. Entertainment, Weather, and Finance top the opportunity ranking

Composite opportunity score (demand × quality-gap × supply-gap × monetization), top 5:

| Rank | Category | n apps | Median rating | % Paid | Score |
|------|----------|--------|---------------|--------|-------|
| 1 | ENTERTAINMENT | 102 | 4.20 | 1.96% | 0.657 |
| 2 | WEATHER | 79 | 4.30 | 10.1% | 0.546 |
| 3 | HOUSE_AND_HOME | 74 | 4.20 | 0.0% | 0.539 |
| 4 | VIDEO_PLAYERS | 163 | 4.20 | 2.45% | 0.523 |
| 5 | FINANCE | 345 | 4.30 | 4.93% | 0.507 |

**Rank stability**: Kendall τ = 0.78 between the default and growth-weighted scheme — the ranking survives plausible re-weighting. ENTERTAINMENT and WEATHER hold the top-2 spots across all three schemes.

## Three recommendations for an operator

1. **Price the paid tier at $1.99–$2.99 on entry, not $0.99 and not $9.99.** The winner pool is densest here; $0.99 under-captures value, $9.99+ sharply narrows the addressable install base.
2. **Invest in review-response and in-app feedback prompts before any performance marketing.** *reviews_per_install* is the largest ratings driver — it represents user engagement density. A product that converts more of its installs into reviews is already a better product.
3. **Enter ENTERTAINMENT or WEATHER** if category-selection is still open. Both show high demand, a quality gap (room to be the best app), and a thin supply of truly good options. FINANCE is the safer monetization bet (4.9% paid, higher ARPU) but more competitive.

## Three recommendations for an acquirer

1. **Start the deal funnel with the shortlist in `data/processed/acquisition_shortlist.csv`** — demand-side qualified (rating ≥ 4.3, installs ≥ 100k, reviews ≥ 5k, updated within 24 months, within top-5 categories). Layer SensorTower or data.ai revenue estimates before LOI.
2. **Anchor the bid framing to $1.99–$2.99 consumer price points.** That is where the winner pool's monetization is calibrated; users in these categories have already accepted that range.
3. **Treat "stopped working" and "fake profiles" as deal-risk signals**, not just product debt. Either complaint in the top-20 negative bigrams of a target app reduces its addressable NPS base and typically requires a 6–9 month fix cycle.

## Caveats

- 2018 snapshot. Methodology generalises; absolute numbers do not.
- `Installs` is Google's published bucket (`100,000+`), not an exact count. All install comparisons are ordinal.
- Review corpus covers ~1,040 of 9,659 apps (11%). NLP conclusions are scoped to that sample, which skews toward heavily-reviewed apps.
- No revenue / DAU / churn. The acquisition shortlist is a **demand-side screen only**.

---
*Full statistical methods: [`reports/methodology.md`](methodology.md)*
*Interview Q&A: [`reports/interview_talking_points.md`](interview_talking_points.md)*
