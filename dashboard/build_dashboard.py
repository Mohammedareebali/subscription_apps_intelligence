"""Build a 3-page interactive Plotly HTML dashboard + nav index.

Each page answers one business question:
  1. Market Overview      — What does the Google Play market look like?
  2. Category Deep-Dive   — Which categories monetise best?
  3. Opportunity Finder   — Where should a new paid app be built?

Runs fully from processed parquet. Outputs are self-contained HTML files
that open in any browser — no install required.

Usage:
    python dashboard/build_dashboard.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.features import PRICE_BANDS  # noqa: E402
from src.scoring import composite_score, normalize_minmax  # noqa: E402

DATA = ROOT / "data" / "processed"
OUT = ROOT / "dashboard"
OUT.mkdir(exist_ok=True)

PLOTLY_CONFIG = {"displaylogo": False, "responsive": True}
TEMPLATE = "plotly_white"
BRAND = {
    "blue": "#2E86AB",
    "navy": "#1B3A57",
    "orange": "#F18F01",
    "red": "#C73E1D",
    "green": "#3B8132",
    "grey": "#6B6B6B",
    "bg": "#F5F7FA",
    "insight_bg": "#EEF4FA",
    "insight_border": "#2E86AB",
}


# ---------------------------------------------------------------------------
# Data load
# ---------------------------------------------------------------------------

def load_data():
    apps = pd.read_parquet(DATA / "apps_clean.parquet")
    shortlist = pd.read_csv(DATA / "acquisition_shortlist.csv")
    return apps, shortlist


def category_table(apps: pd.DataFrame) -> pd.DataFrame:
    cat = (
        apps.groupby("category")
        .agg(
            n_apps=("App", "size"),
            mean_log_installs=("log_installs", "mean"),
            median_rating=("Rating", "median"),
            pct_paid=("is_paid", "mean"),
            median_paid_price=(
                "price_usd",
                lambda s: s[s > 0].median() if (s > 0).any() else 0,
            ),
            mean_sentiment=("mean_compound", "mean"),
        )
        .reset_index()
    )
    cat["demand"] = cat["mean_log_installs"]
    cat["quality_gap"] = 1 - cat["median_rating"].fillna(cat["median_rating"].median())
    cat["supply_gap"] = 1 / np.log1p(cat["n_apps"])
    cat["monetization"] = cat["pct_paid"] * cat["median_paid_price"].fillna(0)
    cat = cat[cat["n_apps"] >= 20].reset_index(drop=True)
    weights = {"demand": 1.0, "quality_gap": 1.0, "supply_gap": 0.5, "monetization": 0.75}
    cat["opportunity_score"] = composite_score(cat, weights)
    return cat.sort_values("opportunity_score", ascending=False).reset_index(drop=True)


# ---------------------------------------------------------------------------
# Shared HTML shell
# ---------------------------------------------------------------------------

NAV = """
<nav style="background:#1B3A57;padding:16px 32px;font-family:-apple-system,Segoe UI,Roboto,sans-serif;box-shadow:0 2px 6px rgba(0,0,0,0.08);">
  <a href="index.html" style="color:#fff;text-decoration:none;font-weight:700;margin-right:32px;font-size:15px;letter-spacing:0.3px;">Subscription App Intelligence</a>
  <a href="01_market_overview.html" style="color:#cfd8dc;text-decoration:none;margin-right:24px;font-size:14px;">Market Overview</a>
  <a href="02_category_deepdive.html" style="color:#cfd8dc;text-decoration:none;margin-right:24px;font-size:14px;">Category Deep-Dive</a>
  <a href="03_opportunity_finder.html" style="color:#cfd8dc;text-decoration:none;font-size:14px;">Opportunity Finder</a>
</nav>
"""


def wrap_page(title: str, body_html: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>{title}</title>
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>
  body {{ margin:0; background:{BRAND['bg']}; font-family:-apple-system,Segoe UI,Roboto,sans-serif; color:#222; line-height:1.5; }}
  .wrap {{ max-width:1320px; margin:0 auto; padding:32px 24px 48px; }}
  h1 {{ margin:0 0 6px 0; font-size:30px; font-weight:700; color:#1B3A57; }}
  h2 {{ margin:32px 0 12px 0; font-size:20px; font-weight:600; color:#1B3A57; }}
  h3 {{ margin:0 0 8px 0; font-size:16px; font-weight:600; color:#1B3A57; }}
  .question {{ color:{BRAND['grey']}; margin-bottom:28px; font-size:15px; font-style:italic; }}
  .kpi-grid {{ display:grid; grid-template-columns:repeat(4,1fr); gap:16px; margin-bottom:32px; }}
  .kpi {{ background:#fff; border-radius:10px; padding:20px; box-shadow:0 1px 3px rgba(0,0,0,0.06); }}
  .kpi .label {{ color:{BRAND['grey']}; font-size:12px; text-transform:uppercase; letter-spacing:0.8px; font-weight:600; }}
  .kpi .value {{ font-size:30px; font-weight:700; color:#1B3A57; margin-top:6px; line-height:1.1; }}
  .kpi .sub {{ font-size:12px; color:{BRAND['grey']}; margin-top:4px; }}
  .card {{ background:#fff; border-radius:10px; padding:20px; box-shadow:0 1px 3px rgba(0,0,0,0.06); margin-bottom:24px; }}
  .card h3 {{ margin-bottom:4px; }}
  .card .chart-sub {{ color:{BRAND['grey']}; font-size:13px; margin-bottom:10px; }}
  .insight {{ background:{BRAND['insight_bg']}; border-left:4px solid {BRAND['insight_border']};
             border-radius:6px; padding:16px 20px; margin:0 0 24px 0; }}
  .insight .label {{ font-size:11px; font-weight:700; color:{BRAND['insight_border']};
                    text-transform:uppercase; letter-spacing:1px; }}
  .insight p {{ margin:4px 0 0 0; font-size:14.5px; color:#1B3A57; }}
  .grid-2 {{ display:grid; grid-template-columns:1fr 1fr; gap:24px; margin-bottom:24px; }}
  table.data {{ width:100%; border-collapse:collapse; font-size:13px; }}
  table.data th {{ background:#F5F7FA; color:#1B3A57; padding:10px 12px; text-align:left;
                  font-weight:600; font-size:11px; letter-spacing:0.5px; text-transform:uppercase; border-bottom:2px solid #E0E6ED; }}
  table.data td {{ padding:10px 12px; border-bottom:1px solid #F0F2F5; }}
  table.data tr:hover {{ background:#FAFBFC; }}
  .rank-badge {{ display:inline-block; width:26px; height:26px; line-height:26px; text-align:center;
                background:#1B3A57; color:#fff; border-radius:50%; font-weight:700; font-size:12px; }}
  .rank-badge.gold {{ background:#F18F01; }}
</style>
</head>
<body>
{NAV}
<div class="wrap">
{body_html}
</div>
</body>
</html>"""


def fig_to_div(fig: go.Figure, height: int = 400) -> str:
    fig.update_layout(
        template=TEMPLATE,
        margin=dict(l=50, r=30, t=30, b=50),
        height=height,
        font=dict(family="-apple-system,Segoe UI,Roboto,sans-serif", size=12, color="#222"),
    )
    return fig.to_html(include_plotlyjs="cdn", full_html=False, config=PLOTLY_CONFIG)


def kpi_card(label: str, value: str, sub: str = "") -> str:
    sub_html = f'<div class="sub">{sub}</div>' if sub else ""
    return f'<div class="kpi"><div class="label">{label}</div><div class="value">{value}</div>{sub_html}</div>'


def insight(text: str) -> str:
    return f'<div class="insight"><div class="label">Key Insight</div><p>{text}</p></div>'


# ---------------------------------------------------------------------------
# Page 1 — Market Overview  (What does the app market look like?)
# ---------------------------------------------------------------------------

def page_market_overview(apps: pd.DataFrame) -> str:
    n_apps = len(apps)
    avg_rating = apps["Rating"].mean()
    pct_paid = apps["is_paid"].mean() * 100
    avg_sentiment = apps["mean_compound"].mean()
    n_categories = apps["category"].nunique()

    kpis = "".join([
        kpi_card("Apps analysed", f"{n_apps:,}", f"{n_categories} categories"),
        kpi_card("Free vs paid", "92.2% / 7.8%", "freemium dominates"),
        kpi_card("Average rating", f"{avg_rating:.2f}", "out of 5 stars"),
        kpi_card("Review sentiment", f"+{avg_sentiment:.2f}", "VADER compound"),
    ])

    # HERO: top 15 categories by app count
    top_cats = apps["category"].value_counts().head(15).reset_index()
    top_cats.columns = ["category", "count"]
    top_cats["category"] = top_cats["category"].str.replace("_", " ").str.title()
    fig_bar = px.bar(
        top_cats.sort_values("count"),
        x="count", y="category", orientation="h",
        color="count", color_continuous_scale="Blues",
    )
    fig_bar.update_layout(showlegend=False, coloraxis_showscale=False,
                          yaxis_title="", xaxis_title="Number of apps")

    # SUPPORT 1: rating distribution
    fig_hist = px.histogram(
        apps.dropna(subset=["Rating"]),
        x="Rating", nbins=30,
        color_discrete_sequence=[BRAND["blue"]],
    )
    fig_hist.update_layout(xaxis_title="App rating", yaxis_title="Apps", bargap=0.05)

    # SUPPORT 2: sentiment by category (top 10 only, tighter)
    sent = (apps.dropna(subset=["mean_compound"])
            .groupby("category")["mean_compound"]
            .agg(["mean", "size"])
            .query("size >= 20")
            .sort_values("mean", ascending=True)
            .tail(10).reset_index())
    sent["category"] = sent["category"].str.replace("_", " ").str.title()
    fig_sent = px.bar(
        sent, x="mean", y="category", orientation="h",
        color="mean", color_continuous_scale="RdYlGn", range_color=(-0.2, 0.6),
    )
    fig_sent.update_layout(coloraxis_showscale=False,
                           xaxis_title="Average VADER sentiment", yaxis_title="")

    body = f"""
    <h1>What the Google Play market looks like</h1>
    <div class="question">Market scale, pricing model, and quality signals across 9,659 apps</div>

    <div class="kpi-grid">{kpis}</div>

    {insight("Freemium dominates Google Play — only 7.8% of apps are paid. Any new entrant defaulting to a paid tier needs to justify that choice against a 92% free-app baseline.")}

    <div class="card">
      <h3>The biggest categories by app count</h3>
      <div class="chart-sub">Family, Games, and Tools lead — but volume doesn't equal opportunity (see page 3)</div>
      {fig_to_div(fig_bar, 480)}
    </div>

    <div class="grid-2">
      <div class="card">
        <h3>How users rate apps</h3>
        <div class="chart-sub">Ratings cluster around 4.3 — a high bar for new entrants</div>
        {fig_to_div(fig_hist, 360)}
      </div>
      <div class="card">
        <h3>Most positively reviewed categories</h3>
        <div class="chart-sub">Average sentiment from VADER analysis of user reviews</div>
        {fig_to_div(fig_sent, 360)}
      </div>
    </div>
    """
    return wrap_page("Market Overview · Subscription App Intelligence", body)


# ---------------------------------------------------------------------------
# Page 2 — Category Deep-Dive  (Which categories monetise best?)
# ---------------------------------------------------------------------------

def page_category_deepdive(apps: pd.DataFrame, cat: pd.DataFrame) -> str:
    # Headline KPIs for paid apps
    paid = apps[apps["is_paid"] == 1]
    median_paid_price = paid["price_usd"].median()
    pct_1_5_band = ((paid["price_usd"] >= 1) & (paid["price_usd"] <= 4.99)).mean() * 100
    paid_rating = paid["Rating"].mean()
    free_rating = apps[apps["is_paid"] == 0]["Rating"].mean()

    kpis = "".join([
        kpi_card("Paid apps", f"{len(paid):,}", "7.8% of the market"),
        kpi_card("Median paid price", f"${median_paid_price:.2f}", "typical charge"),
        kpi_card("In $1–$4.99 band", f"{pct_1_5_band:.0f}%", "the sweet spot"),
        kpi_card("Paid rating edge", f"+{paid_rating - free_rating:.2f}★", f"{paid_rating:.2f} vs {free_rating:.2f}"),
    ])

    # HERO: rating × installs scatter (top 8 categories for readability)
    top_cats = cat.sort_values("n_apps", ascending=False).head(8)["category"].tolist()
    plot_apps = apps[apps["category"].isin(top_cats)].dropna(subset=["Rating", "log_installs"])
    plot_apps = plot_apps.copy()
    plot_apps["category_label"] = plot_apps["category"].str.replace("_", " ").str.title()

    fig_scatter = px.scatter(
        plot_apps,
        x="log_installs", y="Rating",
        size="reviews", color="category_label",
        hover_name="App",
        hover_data={"reviews": ":,d", "price_usd": ":.2f",
                    "log_installs": False, "category_label": False},
        size_max=32, opacity=0.55,
    )
    fig_scatter.update_layout(
        xaxis_title="Reach (log of installs)",
        yaxis_title="User rating",
        legend_title="Category",
    )

    # SUPPORT 1: price band bar — winner pool (notebook 02 methodology)
    # rating ≥ 4.3 AND installs ≥ category median (median taken across paid apps only)
    paid_rated = apps[(apps["is_paid"] == 1) & apps["Rating"].notna()].copy()
    cat_median_installs = paid_rated.groupby("category")["installs"].transform("median")
    winners = paid_rated[(paid_rated["Rating"] >= 4.3) & (paid_rated["installs"] >= cat_median_installs)]
    band_order = [label for label, _, _ in PRICE_BANDS if label != "Free"]
    band_counts = winners["price_band"].value_counts().reindex(band_order).fillna(0).reset_index()
    band_counts.columns = ["price_band", "count"]
    total = band_counts["count"].sum() or 1
    band_counts["pct"] = (band_counts["count"] / total * 100).fillna(0).round().astype(int)
    fig_price = px.bar(
        band_counts, x="price_band", y="count",
        color="count", color_continuous_scale="Oranges",
        text=band_counts["pct"].astype(str) + "%",
    )
    fig_price.update_traces(textposition="outside")
    fig_price.update_layout(coloraxis_showscale=False,
                            xaxis_title="Price band", yaxis_title="Paid apps")

    # SUPPORT 2: top 10 apps by install-weighted rating (trimmed from 15)
    top_apps = (apps.dropna(subset=["Rating", "installs"])
                .assign(weighted=lambda d: d["Rating"] * d["log_installs"])
                .nlargest(10, "weighted")
                [["App", "category", "Rating", "Installs"]])
    rows = "".join([
        f"<tr><td><span class='rank-badge{' gold' if i<3 else ''}'>{i+1}</span></td>"
        f"<td>{r['App']}</td><td>{r['category'].replace('_',' ').title()}</td>"
        f"<td><strong>{r['Rating']:.1f}</strong></td><td>{r['Installs']}</td></tr>"
        for i, (_, r) in enumerate(top_apps.iterrows())
    ])
    table_html = f"""
    <table class="data">
      <thead><tr><th>#</th><th>App</th><th>Category</th><th>Rating</th><th>Installs</th></tr></thead>
      <tbody>{rows}</tbody>
    </table>
    """

    body = f"""
    <h1>Where paid apps actually win</h1>
    <div class="question">Pricing behaviour, ratings edge, and the apps setting the benchmark</div>

    <div class="kpi-grid">{kpis}</div>

    {insight("Paid apps cluster at $1.99–$4.99 — and rate <strong>+0.11★ higher</strong> than free apps even after controlling for category, installs and size (OLS fixed effects, p&lt;0.0001). The premium is modest but real.")}

    <div class="card">
      <h3>Ratings vs reach — top 8 categories by volume</h3>
      <div class="chart-sub">Hover any dot for the app. Bubble size = review count.</div>
      {fig_to_div(fig_scatter, 520)}
    </div>

    <div class="grid-2">
      <div class="card">
        <h3>What winning paid apps charge</h3>
        <div class="chart-sub">≈70% of paid apps price between $1 and $4.99 — the sweet spot</div>
        {fig_to_div(fig_price, 360)}
      </div>
      <div class="card">
        <h3>Top 10 apps by install-weighted rating</h3>
        <div class="chart-sub">The benchmark — what a new entrant is competing against</div>
        {table_html}
      </div>
    </div>
    """
    return wrap_page("Category Deep-Dive · Subscription App Intelligence", body)


# ---------------------------------------------------------------------------
# Page 3 — Opportunity Finder  (Where should a new paid app be built?)
# ---------------------------------------------------------------------------

def page_opportunity(cat: pd.DataFrame, shortlist: pd.DataFrame) -> str:
    c = cat.copy()
    c["demand_n"] = normalize_minmax(c["demand"])
    c["qgap_n"] = normalize_minmax(c["quality_gap"])
    c["label"] = c["category"].str.replace("_", " ").str.title()

    # Headline KPIs
    top_cat = c.iloc[0]
    kpis = "".join([
        kpi_card("Top opportunity", top_cat["label"], f"score {top_cat['opportunity_score']:.2f}"),
        kpi_card("Categories ranked", f"{len(c)}", "≥ 20 apps each"),
        kpi_card("Rank stability", "τ = 0.78", "Kendall across 3 weight schemes"),
        kpi_card("Shortlist size", f"{len(shortlist)}", "demand-side screen"),
    ])

    # HERO: quadrant
    fig_q = px.scatter(
        c,
        x="demand_n", y="qgap_n",
        size=c["n_apps"].clip(lower=20),
        color="opportunity_score", color_continuous_scale="Viridis",
        hover_name="label",
        hover_data={"n_apps": True, "median_rating": ":.2f", "pct_paid": ":.1%",
                    "opportunity_score": ":.2f", "demand_n": False, "qgap_n": False},
        text=c.apply(lambda r: r["label"] if r["opportunity_score"] >= c["opportunity_score"].quantile(0.8) else "", axis=1),
        size_max=52,
    )
    fig_q.update_traces(textposition="top center", textfont=dict(size=11, color="#1B3A57"))
    fig_q.update_layout(
        xaxis_title="Market size  →  (bigger user base)",
        yaxis_title="Quality gap  →  (room to be the best app)",
        coloraxis_colorbar=dict(title="Score"),
    )

    # SUPPORT 1: top 10 bar (trimmed from 15)
    top10 = c.sort_values("opportunity_score", ascending=True).tail(10)
    fig_bar = px.bar(
        top10, x="opportunity_score", y="label", orientation="h",
        color="opportunity_score", color_continuous_scale="Viridis",
        text=top10["opportunity_score"].round(2),
    )
    fig_bar.update_traces(textposition="outside")
    fig_bar.update_layout(coloraxis_showscale=False, yaxis_title="", xaxis_title="Opportunity score")

    # SUPPORT 2: shortlist top 10 with rank badges
    s = (shortlist[["App", "category", "Rating", "Installs", "shortlist_score"]]
         .head(10).copy())
    s["category"] = s["category"].str.replace("_", " ").str.title()
    rows = "".join([
        f"<tr><td><span class='rank-badge{' gold' if i<3 else ''}'>{i+1}</span></td>"
        f"<td>{r['App']}</td><td>{r['category']}</td>"
        f"<td><strong>{r['Rating']:.1f}</strong></td><td>{r['Installs']}</td>"
        f"<td>{r['shortlist_score']:.1f}</td></tr>"
        for i, (_, r) in enumerate(s.iterrows())
    ])
    table_html = f"""
    <table class="data">
      <thead><tr><th>#</th><th>App</th><th>Category</th><th>Rating</th><th>Installs</th><th>Score</th></tr></thead>
      <tbody>{rows}</tbody>
    </table>
    """

    body = f"""
    <h1>Best categories to launch new paid apps</h1>
    <div class="question">Ranked by demand, quality gap, competition thinness and monetization — stable across 3 weight schemes</div>

    <div class="kpi-grid">{kpis}</div>

    {insight(f"<strong>{top_cat['label']}, Weather, and House &amp; Home</strong> rank top — strong user demand combined with a meaningful quality gap and thin competition. The ranking survives re-weighting (Kendall τ = 0.78), so the top 5 aren't artefacts of a single weighting choice.")}

    <div class="card">
      <h3>Where to build — the opportunity quadrant</h3>
      <div class="chart-sub">Upper-right quadrant = big market × room to win. Bubble size = app count in category. Colour = composite score.</div>
      {fig_to_div(fig_q, 560)}
    </div>

    <div class="grid-2">
      <div class="card">
        <h3>Top 10 categories to enter</h3>
        <div class="chart-sub">Composite opportunity score (0–1 scale)</div>
        {fig_to_div(fig_bar, 440)}
      </div>
      <div class="card">
        <h3>Top 10 acquisition shortlist</h3>
        <div class="chart-sub">Demand-side screen: rating ≥ 4.3, installs ≥ 100k, reviews ≥ 5k</div>
        {table_html}
      </div>
    </div>

    <div style="color:{BRAND['grey']};font-size:12px;margin-top:-8px;">
      <strong>Caveat:</strong> Google Play has no revenue / DAU / churn data. Before any LOI, layer SensorTower or data.ai revenue estimates on this shortlist.
    </div>
    """
    return wrap_page("Opportunity Finder · Subscription App Intelligence", body)


# ---------------------------------------------------------------------------
# Index page
# ---------------------------------------------------------------------------

def page_index() -> str:
    body = f"""
    <h1 style="font-size:36px;">Subscription App Intelligence</h1>
    <div class="question" style="font-size:16px;">
      Pricing sweet spots, rating drivers, and growth opportunities across 9,659 Google Play apps.
    </div>

    {insight("70% of top-performing paid apps price between $1–$4.99 · Reviews-per-install is the #1 driver of ratings · Entertainment, Weather and Finance rank as top under-served categories.")}

    <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:20px;margin-top:8px;">
      <a href="01_market_overview.html" style="text-decoration:none;color:inherit;">
        <div class="card" style="cursor:pointer;border-top:4px solid {BRAND['blue']};">
          <div style="font-size:11px;color:{BRAND['blue']};font-weight:700;letter-spacing:1px;">PAGE 1</div>
          <h3 style="margin:8px 0 6px;font-size:18px;">Market Overview</h3>
          <div style="color:{BRAND['grey']};font-size:13px;margin-bottom:10px;font-style:italic;">What does the Google Play market look like?</div>
          <p style="color:#444;font-size:13.5px;margin:0;">Market scale, category mix, rating distribution, and user sentiment benchmarks.</p>
        </div>
      </a>
      <a href="02_category_deepdive.html" style="text-decoration:none;color:inherit;">
        <div class="card" style="cursor:pointer;border-top:4px solid {BRAND['orange']};">
          <div style="font-size:11px;color:{BRAND['orange']};font-weight:700;letter-spacing:1px;">PAGE 2</div>
          <h3 style="margin:8px 0 6px;font-size:18px;">Category Deep-Dive</h3>
          <div style="color:{BRAND['grey']};font-size:13px;margin-bottom:10px;font-style:italic;">Which categories monetise best?</div>
          <p style="color:#444;font-size:13.5px;margin:0;">Pricing bands, ratings edge, and the top apps a new entrant is competing against.</p>
        </div>
      </a>
      <a href="03_opportunity_finder.html" style="text-decoration:none;color:inherit;">
        <div class="card" style="cursor:pointer;border-top:4px solid {BRAND['green']};">
          <div style="font-size:11px;color:{BRAND['green']};font-weight:700;letter-spacing:1px;">PAGE 3</div>
          <h3 style="margin:8px 0 6px;font-size:18px;">Opportunity Finder</h3>
          <div style="color:{BRAND['grey']};font-size:13px;margin-bottom:10px;font-style:italic;">Where should a new paid app be built?</div>
          <p style="color:#444;font-size:13.5px;margin:0;">Quadrant chart, top-10 category ranking, and demand-side acquisition shortlist.</p>
        </div>
      </a>
    </div>

    <div class="card" style="margin-top:24px;">
      <h3>About this dashboard</h3>
      <p style="color:#444;margin:6px 0;">Built with Python + Plotly. Every chart is interactive: hover for tooltips, click legend items to filter, drag to zoom. Generated by <code>dashboard/build_dashboard.py</code>, fully reproducible from the processed parquet in <code>data/processed/</code>.</p>
      <p style="color:{BRAND['grey']};font-size:13px;margin:8px 0 0;">Data: Kaggle Google Play snapshot (2018, CC0). Methodology: <a href="../reports/methodology.md">reports/methodology.md</a>. Findings: <a href="../reports/executive_summary.md">reports/executive_summary.md</a>.</p>
    </div>
    """
    return wrap_page("Subscription App Intelligence Dashboard", body)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    apps, shortlist = load_data()
    cat = category_table(apps)

    (OUT / "index.html").write_text(page_index())
    (OUT / "01_market_overview.html").write_text(page_market_overview(apps))
    (OUT / "02_category_deepdive.html").write_text(page_category_deepdive(apps, cat))
    (OUT / "03_opportunity_finder.html").write_text(page_opportunity(cat, shortlist))

    print(f"Wrote 4 HTML files to {OUT}")
    for p in sorted(OUT.glob("*.html")):
        size_kb = p.stat().st_size / 1024
        print(f"  {p.name}  ({size_kb:.1f} KB)")


if __name__ == "__main__":
    main()
