"""Build a 3-page interactive Plotly HTML dashboard + nav index.

Runs fully from processed parquet. Outputs are self-contained HTML files
that open in any browser — no Power BI / no install required.

Usage:
    python dashboard/build_dashboard.py

Outputs:
    dashboard/index.html
    dashboard/01_market_overview.html
    dashboard/02_category_deepdive.html
    dashboard/03_opportunity_finder.html
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

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
<nav style="background:#1B3A57;padding:14px 28px;font-family:-apple-system,Segoe UI,Roboto,sans-serif;">
  <a href="index.html" style="color:#fff;text-decoration:none;font-weight:700;margin-right:28px;">&#9776; Subscription Apps Dashboard</a>
  <a href="01_market_overview.html" style="color:#cfd8dc;text-decoration:none;margin-right:20px;">1 · Market Overview</a>
  <a href="02_category_deepdive.html" style="color:#cfd8dc;text-decoration:none;margin-right:20px;">2 · Category Deep-Dive</a>
  <a href="03_opportunity_finder.html" style="color:#cfd8dc;text-decoration:none;">3 · Opportunity Finder</a>
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
  body {{ margin:0; background:{BRAND['bg']}; font-family:-apple-system,Segoe UI,Roboto,sans-serif; color:#222; }}
  .wrap {{ max-width:1400px; margin:0 auto; padding:24px; }}
  h1 {{ margin:0 0 4px 0; font-size:26px; }}
  .sub {{ color:#6B6B6B; margin-bottom:20px; }}
  .kpi-grid {{ display:grid; grid-template-columns:repeat(4,1fr); gap:14px; margin-bottom:22px; }}
  .kpi {{ background:#fff; border-radius:10px; padding:18px; box-shadow:0 1px 3px rgba(0,0,0,0.06); }}
  .kpi .label {{ color:#6B6B6B; font-size:12px; text-transform:uppercase; letter-spacing:0.5px; }}
  .kpi .value {{ font-size:28px; font-weight:700; color:#1B3A57; margin-top:4px; }}
  .card {{ background:#fff; border-radius:10px; padding:14px; box-shadow:0 1px 3px rgba(0,0,0,0.06); margin-bottom:18px; }}
  table.data {{ width:100%; border-collapse:collapse; font-size:13px; }}
  table.data th {{ background:#1B3A57; color:#fff; padding:8px; text-align:left; }}
  table.data td {{ padding:6px 8px; border-bottom:1px solid #eee; }}
  table.data tr:hover {{ background:#f0f4f8; }}
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
    fig.update_layout(template=TEMPLATE, margin=dict(l=40, r=20, t=40, b=40), height=height)
    return fig.to_html(include_plotlyjs="cdn", full_html=False, config=PLOTLY_CONFIG)


def kpi_card(label: str, value: str) -> str:
    return f'<div class="kpi"><div class="label">{label}</div><div class="value">{value}</div></div>'


# ---------------------------------------------------------------------------
# Page 1 — Market Overview
# ---------------------------------------------------------------------------

def page_market_overview(apps: pd.DataFrame) -> str:
    n_apps = len(apps)
    avg_rating = apps["Rating"].mean()
    pct_paid = apps["is_paid"].mean() * 100
    avg_sentiment = apps["mean_compound"].mean()

    kpis = "".join([
        kpi_card("Apps analysed", f"{n_apps:,}"),
        kpi_card("Avg rating", f"{avg_rating:.2f} / 5"),
        kpi_card("Paid share", f"{pct_paid:.1f}%"),
        kpi_card("Avg sentiment", f"+{avg_sentiment:.2f}"),
    ])

    # Bar: top 15 categories by app count
    top_cats = apps["category"].value_counts().head(15).reset_index()
    top_cats.columns = ["category", "count"]
    top_cats["category"] = top_cats["category"].str.replace("_", " ").str.title()
    fig_bar = px.bar(
        top_cats.sort_values("count"),
        x="count", y="category", orientation="h",
        color="count", color_continuous_scale="Blues",
        title="Top 15 categories by app count",
    )
    fig_bar.update_layout(showlegend=False, coloraxis_showscale=False, yaxis_title="", xaxis_title="Apps")

    # Histogram: rating, coloured by paid
    fig_hist = px.histogram(
        apps.dropna(subset=["Rating"]),
        x="Rating", color="price_band",
        nbins=30, barmode="overlay", opacity=0.7,
        color_discrete_map={"Free": BRAND["blue"], "$0.99-$2.99": BRAND["orange"],
                            "$3-$4.99": BRAND["red"], "$5-$9.99": BRAND["green"],
                            "$10+": BRAND["navy"]},
        title="Rating distribution by price band",
    )
    fig_hist.update_layout(xaxis_title="Rating", yaxis_title="Apps", legend_title="")

    # Donut: free vs paid
    paid_split = apps["price_band"].eq("Free").map({True: "Free", False: "Paid"}).value_counts()
    fig_donut = go.Figure(data=[go.Pie(
        labels=paid_split.index, values=paid_split.values, hole=0.55,
        marker=dict(colors=[BRAND["blue"], BRAND["orange"]]),
    )])
    fig_donut.update_layout(title="Free vs Paid", showlegend=True)

    # Sentiment by category (top 10 with reviews scored)
    sent = (apps.dropna(subset=["mean_compound"])
            .groupby("category")["mean_compound"]
            .agg(["mean", "size"])
            .query("size >= 20")
            .sort_values("mean", ascending=True)
            .tail(12).reset_index())
    sent["category"] = sent["category"].str.replace("_", " ").str.title()
    fig_sent = px.bar(
        sent, x="mean", y="category", orientation="h",
        color="mean", color_continuous_scale="RdYlGn", range_color=(-0.2, 0.6),
        title="Avg review sentiment — top 12 categories",
    )
    fig_sent.update_layout(coloraxis_showscale=False, xaxis_title="VADER compound", yaxis_title="")

    body = f"""
    <h1>1 · Market Overview</h1>
    <div class="sub">9,659 Google Play apps · 33 categories · 7.8% paid. A bird's-eye view of the market.</div>
    <div class="kpi-grid">{kpis}</div>
    <div style="display:grid;grid-template-columns:2fr 1fr;gap:18px;">
      <div class="card">{fig_to_div(fig_bar, 480)}</div>
      <div class="card">{fig_to_div(fig_donut, 480)}</div>
    </div>
    <div class="card">{fig_to_div(fig_hist, 380)}</div>
    <div class="card">{fig_to_div(fig_sent, 420)}</div>
    """
    return wrap_page("Market Overview · Subscription Apps Dashboard", body)


# ---------------------------------------------------------------------------
# Page 2 — Category Deep-Dive
# ---------------------------------------------------------------------------

def page_category_deepdive(apps: pd.DataFrame, cat: pd.DataFrame) -> str:
    # Scatter: rating x log_installs, size by reviews, color by category
    top_cats = cat.sort_values("n_apps", ascending=False).head(10)["category"].tolist()
    plot_apps = apps[apps["category"].isin(top_cats)].dropna(subset=["Rating", "log_installs"])
    plot_apps = plot_apps.copy()
    plot_apps["category_label"] = plot_apps["category"].str.replace("_", " ").str.title()

    fig_scatter = px.scatter(
        plot_apps,
        x="log_installs", y="Rating", size="reviews", color="category_label",
        hover_name="App", hover_data={"reviews": ":,d", "price_usd": ":.2f"},
        title="Rating vs log(installs) — top 10 categories by app count",
        size_max=30, opacity=0.65,
    )
    fig_scatter.update_layout(xaxis_title="log(Installs)", yaxis_title="Rating", legend_title="")

    # Price band bar (paid only)
    paid = apps[apps["is_paid"] == 1]
    band_order = ["$0.99-$2.99", "$3-$4.99", "$5-$9.99", "$10+"]
    band_counts = paid["price_band"].value_counts().reindex(band_order).fillna(0).reset_index()
    band_counts.columns = ["price_band", "count"]
    fig_price = px.bar(
        band_counts, x="price_band", y="count",
        color="count", color_continuous_scale="Oranges",
        title="Paid apps by price band",
    )
    fig_price.update_layout(coloraxis_showscale=False, xaxis_title="", yaxis_title="Apps")

    # Top-10 apps by install-weighted rating
    top_apps = (apps.dropna(subset=["Rating", "installs"])
                .assign(weighted=lambda d: d["Rating"] * d["log_installs"])
                .nlargest(15, "weighted")
                [["App", "category", "Rating", "Installs", "reviews"]])
    rows = "".join([
        f"<tr><td>{r['App']}</td><td>{r['category'].replace('_',' ').title()}</td>"
        f"<td>{r['Rating']:.1f}</td><td>{r['Installs']}</td><td>{int(r['reviews']):,}</td></tr>"
        for _, r in top_apps.iterrows()
    ])
    table_html = f"""
    <table class="data">
      <thead><tr><th>App</th><th>Category</th><th>Rating</th><th>Installs</th><th>Reviews</th></tr></thead>
      <tbody>{rows}</tbody>
    </table>
    """

    # Sentiment gauge (overall)
    avg_sent = apps["mean_compound"].mean()
    fig_gauge = go.Figure(go.Indicator(
        mode="gauge+number",
        value=avg_sent,
        number={"valueformat": "+.2f"},
        title={"text": "Avg review sentiment (VADER compound)"},
        gauge={
            "axis": {"range": [-1, 1]},
            "bar": {"color": BRAND["navy"]},
            "steps": [
                {"range": [-1, -0.3], "color": "#f7c8c1"},
                {"range": [-0.3, 0.3], "color": "#f2f2f2"},
                {"range": [0.3, 1], "color": "#c9e4c5"},
            ],
        },
    ))

    body = f"""
    <h1>2 · Category Deep-Dive</h1>
    <div class="sub">Ratings-vs-reach scatter across the 10 largest categories, paid pricing distribution, and the heaviest-hitting apps by install-weighted rating.</div>
    <div class="card">{fig_to_div(fig_scatter, 560)}</div>
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:18px;">
      <div class="card">{fig_to_div(fig_price, 380)}</div>
      <div class="card">{fig_to_div(fig_gauge, 380)}</div>
    </div>
    <div class="card"><h3 style="margin-top:0">Top 15 apps — install-weighted rating</h3>{table_html}</div>
    """
    return wrap_page("Category Deep-Dive · Subscription Apps Dashboard", body)


# ---------------------------------------------------------------------------
# Page 3 — Opportunity Finder
# ---------------------------------------------------------------------------

def page_opportunity(cat: pd.DataFrame, shortlist: pd.DataFrame) -> str:
    c = cat.copy()
    c["demand_n"] = normalize_minmax(c["demand"])
    c["qgap_n"] = normalize_minmax(c["quality_gap"])
    c["label"] = c["category"].str.replace("_", " ").str.title()

    # Hero quadrant
    fig_q = px.scatter(
        c,
        x="demand_n", y="qgap_n",
        size=c["n_apps"].clip(lower=20),
        color="opportunity_score", color_continuous_scale="Viridis",
        hover_name="label",
        hover_data={"n_apps": True, "median_rating": ":.2f", "pct_paid": ":.1%",
                    "opportunity_score": ":.2f", "demand_n": False, "qgap_n": False},
        text=c.apply(lambda r: r["label"] if r["opportunity_score"] >= c["opportunity_score"].quantile(0.75) else "", axis=1),
        title="Where to build — category opportunity quadrant",
        size_max=48,
    )
    fig_q.update_traces(textposition="top center", textfont=dict(size=10))
    fig_q.update_layout(
        xaxis_title="Demand  (normalized mean log-installs)",
        yaxis_title="Quality gap  (1 − median rating, normalized)",
        coloraxis_colorbar=dict(title="Score"),
    )

    # Bar: top 15 by opportunity score
    top15 = c.sort_values("opportunity_score", ascending=True).tail(15)
    fig_bar = px.bar(
        top15, x="opportunity_score", y="label", orientation="h",
        color="opportunity_score", color_continuous_scale="Viridis",
        title="Top 15 categories by composite opportunity score",
    )
    fig_bar.update_layout(coloraxis_showscale=False, yaxis_title="", xaxis_title="Score")

    # Shortlist table
    s = shortlist[["App", "category", "Rating", "Installs", "reviews", "shortlist_score"]].copy()
    s["category"] = s["category"].str.replace("_", " ").str.title()
    rows = "".join([
        f"<tr><td>{r['App']}</td><td>{r['category']}</td>"
        f"<td>{r['Rating']:.1f}</td><td>{r['Installs']}</td>"
        f"<td>{int(r['reviews']):,}</td><td>{r['shortlist_score']:.1f}</td></tr>"
        for _, r in s.iterrows()
    ])
    table_html = f"""
    <table class="data">
      <thead><tr><th>App</th><th>Category</th><th>Rating</th><th>Installs</th><th>Reviews</th><th>Score</th></tr></thead>
      <tbody>{rows}</tbody>
    </table>
    """

    body = f"""
    <h1>3 · Opportunity Finder</h1>
    <div class="sub">Composite score = demand × quality-gap × supply-gap × monetization. Ranking is stable across 3 weight schemes (Kendall τ = 0.78).</div>
    <div class="card">{fig_to_div(fig_q, 600)}</div>
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:18px;">
      <div class="card">{fig_to_div(fig_bar, 520)}</div>
      <div class="card"><h3 style="margin-top:0">Acquisition shortlist (demand-side screen)</h3>{table_html}</div>
    </div>
    <div class="sub" style="margin-top:10px;font-size:12px;">
      <strong>Caveat:</strong> shortlist filters on rating ≥ 4.3, installs ≥ 100k, reviews ≥ 5k, updated ≤ 24 months. Google Play has no revenue / DAU / churn — layer SensorTower or data.ai estimates before any LOI.
    </div>
    """
    return wrap_page("Opportunity Finder · Subscription Apps Dashboard", body)


# ---------------------------------------------------------------------------
# Index page
# ---------------------------------------------------------------------------

def page_index() -> str:
    body = """
    <h1 style="font-size:32px;">Subscription Apps Intelligence Dashboard</h1>
    <div class="sub" style="font-size:15px;">Growth · Pricing · Product · Category opportunity — across 9,659 Google Play apps and 37,427 user reviews.</div>
    <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:18px;margin-top:24px;">
      <a href="01_market_overview.html" style="text-decoration:none;color:inherit;">
        <div class="card" style="cursor:pointer;">
          <div style="font-size:13px;color:#2E86AB;font-weight:700;">PAGE 1</div>
          <h3 style="margin:6px 0;">Market Overview</h3>
          <p style="color:#6B6B6B;">Category counts, rating distribution, free vs paid split, sentiment by category.</p>
        </div>
      </a>
      <a href="02_category_deepdive.html" style="text-decoration:none;color:inherit;">
        <div class="card" style="cursor:pointer;">
          <div style="font-size:13px;color:#F18F01;font-weight:700;">PAGE 2</div>
          <h3 style="margin:6px 0;">Category Deep-Dive</h3>
          <p style="color:#6B6B6B;">Rating × installs scatter, pricing-band bar, top install-weighted apps, sentiment gauge.</p>
        </div>
      </a>
      <a href="03_opportunity_finder.html" style="text-decoration:none;color:inherit;">
        <div class="card" style="cursor:pointer;">
          <div style="font-size:13px;color:#3B8132;font-weight:700;">PAGE 3</div>
          <h3 style="margin:6px 0;">Opportunity Finder</h3>
          <p style="color:#6B6B6B;">Hero quadrant chart, top-15 opportunity ranking, demand-side acquisition shortlist.</p>
        </div>
      </a>
    </div>
    <div class="card" style="margin-top:24px;">
      <h3 style="margin-top:0;">About this dashboard</h3>
      <p>Built with Python + Plotly. All charts are interactive: hover for tooltips, click legend items to filter, drag to zoom. Generated by <code>dashboard/build_dashboard.py</code>, fully reproducible from the processed parquet files in <code>data/processed/</code>.</p>
      <p style="color:#6B6B6B;font-size:13px;">Data: Kaggle Google Play snapshot (2018, CC0). Methodology: <a href="../reports/methodology.md">reports/methodology.md</a>. Findings: <a href="../reports/executive_summary.md">reports/executive_summary.md</a>.</p>
    </div>
    """
    return wrap_page("Subscription Apps Dashboard", body)


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
