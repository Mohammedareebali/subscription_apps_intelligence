# Power BI build guide

This is the handoff from the Python analysis to a Power BI dashboard. Claude Code cannot author `.pbix` files directly, so this guide is the most mechanical possible step-by-step. Budget **~60–90 minutes** from empty Power BI Desktop to a published `.pbix`.

## Inputs

- `../data/processed/powerbi_model.csv` — one row per app, denormalized with readable column names. Produced by `notebooks/04_where_to_build.ipynb`.

## What you will build

Three pages, four visuals per page, one slicer bar shared across pages.

| Page | Purpose | Key visuals |
|---|---|---|
| 01 — Market Overview | 30-second snapshot of the 10k-app corpus | KPI cards, category bar, rating histogram, free-vs-paid donut |
| 02 — Category Deep-Dive | Pick a category and inspect its pricing + quality distribution | Scatter (rating × installs), price-band bar, top-10 app table, sentiment gauge |
| 03 — Opportunity Finder | Where to enter the market (hero page) | Quadrant scatter, opportunity-score bar, filter-driven shortlist table, KPI callouts |

Dashboard colour palette: default Power BI theme (do not bikeshed — recruiters notice polish, not palettes).

## Step 1 — Load the data

1. Open Power BI Desktop → **Get Data → Text/CSV** → select `powerbi_model.csv`.
2. In the preview, confirm:
   - `Is Paid` imports as **Whole Number** (0/1) — change if it defaults to Text.
   - `Last Updated` imports as **Date**.
   - All other numeric columns are **Decimal Number** or **Whole Number**.
3. Click **Load** (not Transform — the CSV is already clean).

## Step 2 — Create measures (paste these verbatim)

**Home → New Measure** and paste each of the following, one measure per entry:

```DAX
Avg Rating =
AVERAGE ( 'powerbi_model'[Rating] )
```

```DAX
Install-Weighted Rating =
DIVIDE (
    SUMX ( 'powerbi_model', 'powerbi_model'[Rating] * 'powerbi_model'[Installs] ),
    SUM ( 'powerbi_model'[Installs] )
)
```

```DAX
App Count = COUNTROWS ( 'powerbi_model' )
```

```DAX
Paid Share =
DIVIDE (
    CALCULATE ( COUNTROWS ( 'powerbi_model' ), 'powerbi_model'[Is Paid] = 1 ),
    COUNTROWS ( 'powerbi_model' )
)
```

```DAX
Median Paid Price =
CALCULATE (
    MEDIANX ( 'powerbi_model', 'powerbi_model'[Price (USD)] ),
    'powerbi_model'[Is Paid] = 1
)
```

```DAX
Avg Sentiment =
AVERAGE ( 'powerbi_model'[Sentiment Compound] )
```

```DAX
Opportunity Score =
VAR _demand =
    DIVIDE (
        AVERAGEX ( VALUES ( 'powerbi_model'[Category] ), [Install-Weighted Rating] ),
        MAXX ( ALL ( 'powerbi_model'[Category] ), [Install-Weighted Rating] )
    )
VAR _qualityGap = 1 - DIVIDE ( [Avg Rating], 5 )
VAR _supplyGap = DIVIDE ( 1, LN ( [App Count] + 1 ) )
VAR _mon = [Paid Share] * [Median Paid Price]
RETURN
    DIVIDE ( _demand + _qualityGap + 0.5 * _supplyGap + 0.0075 * _mon, 3.25 )
```

## Step 3 — Page 1: Market Overview

Top strip — KPI cards:
- `App Count`
- `Avg Rating`
- `Paid Share` (format %)
- `Avg Sentiment`

Below, in a 2×2 grid:
1. **Bar chart** — Axis: `Category`; Value: `App Count`; sort descending; top 15.
2. **Histogram / column** — Axis: `Rating` (use default binning); Value: `App Count`.
3. **Donut chart** — Legend: `Is Paid` (rename values 0→Free, 1→Paid); Value: `App Count`.
4. **Line/area** — Axis: `Last Updated` (by year-month); Value: `App Count` (shows the data's 2018 tail).

Slicer (pinned top-right of every page): `Category`, `Price Band`.

## Step 4 — Page 2: Category Deep-Dive

1. **Scatter** — X: `Installs` (log scale on); Y: `Rating`; Size: `Review Count`; Details: `App Name`.
2. **Bar** — Axis: `Price Band` (custom order: Free → $10+); Value: `App Count`, filtered to `Is Paid = 1`.
3. **Table** — Columns: `App Name`, `Rating`, `Installs`, `Price (USD)`, `Sentiment Compound`. Top N = 10 by `Install-Weighted Rating`.
4. **Gauge** — Value: `Avg Sentiment`; min = -1, max = +1, target = 0.

Sync the page slicer to Page 1 (View → Sync slicers → select both pages).

## Step 5 — Page 3: Opportunity Finder (hero page)

1. **Scatter (the quadrant)** — X: `Install-Weighted Rating`; Y: `1 - Avg Rating / 5` (create a quick measure); Size: `App Count`; Details: `Category`. This is the page's headline visual.
2. **Bar** — Axis: `Category`; Value: `Opportunity Score`; sort descending; top 15.
3. **Table** — the acquisition shortlist: filter to `Rating >= 4.3 AND Installs >= 100000 AND Review Count >= 5000`; columns `App Name, Category, Rating, Installs, Review Count, Last Updated, Sentiment Compound`.
4. **KPI callouts** — `Opportunity Score` for the currently selected category.

## Step 6 — Publish and commit

1. **File → Save As** → `dashboard/portfolio_dashboard.pbix` (commit to git — `.pbix` is binary but small).
2. Screenshots for `dashboard/screenshots/`:
   - `01_overview.png`  (page 1, full-window)
   - `02_category.png`  (page 2 with a high-signal category selected — try FINANCE or EDUCATION)
   - `03_opportunity.png`  (page 3, hero page)
3. Update the top-level `README.md` Dashboard section so it references the correct screenshot paths.

## Troubleshooting

- **`Rating` missing in visuals** → ensure blank-rating rows aren't being filtered out upstream; they carry other signals (installs, reviews) that matter for `App Count`.
- **`Is Paid` showing as `True/False`** → in Data view, change column type to **Whole Number**, then re-create the donut legend.
- **Slicer not syncing** → View → Sync slicers → tick both `Visible` and `Synced` for every page.
- **PDF export blurry** → File → Export → Export to PDF (use this for LinkedIn posts; the PNG screenshots are for the README).
