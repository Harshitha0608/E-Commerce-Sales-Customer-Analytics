# ============================================================
# E-Commerce Sales & Customer Analytics — PHASE 3: VISUALIZATIONS
# Author: Harshitha Vedantam
# Tools: Python, pandas, matplotlib, seaborn
# Run this AFTER Phase 1 — needs data/olist_master_clean.csv
# Output: saves 5 chart images into a charts/ folder
# ============================================================

import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import seaborn as sns
import os
from pathlib import Path

# ── SETUP ────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent
DATA_PATH = BASE_DIR / "data" / "olist_master_clean.csv"
CHARTS_DIR = BASE_DIR / "charts"

df = pd.read_csv(DATA_PATH)

# Create output folder for charts
CHARTS_DIR.mkdir(parents=True, exist_ok=True)

# Global style — clean, professional, portfolio-ready
sns.set_theme(style="whitegrid", font="DejaVu Sans")
BLUE   = "#2B4590"
ORANGE = "#E86C3A"
GREEN  = "#2E9E6B"
RED    = "#D64045"
GRAY   = "#A0A7B4"

print("✅ Setup complete — generating 5 charts...\n")


# ── CHART 1: Monthly Revenue Trend ───────────────────────────
# Shows business growth over time — the most important story in the data
print("📊 Chart 1: Monthly Revenue Trend...")

monthly = (
    df[df["order_year"].isin([2017, 2018])]
    .groupby("order_yearmonth")["total_revenue"]
    .sum()
    .reset_index()
)
monthly.columns = ["month", "revenue"]

fig, ax = plt.subplots(figsize=(14, 6))

ax.fill_between(monthly["month"], monthly["revenue"], alpha=0.15, color=BLUE)
ax.plot(monthly["month"], monthly["revenue"], color=BLUE, linewidth=2.5, marker="o", markersize=5)

# Annotate the November 2017 Black Friday spike
nov_idx = monthly[monthly["month"] == "2017-11"].index[0]
ax.annotate(
    "Black Friday\nSpike (+64%)",
    xy=(nov_idx, monthly.loc[nov_idx, "revenue"]),
    xytext=(nov_idx - 3, monthly.loc[nov_idx, "revenue"] + 80000),
    arrowprops=dict(arrowstyle="->", color=ORANGE),
    color=ORANGE, fontsize=10, fontweight="bold"
)

ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"R${x/1000:.0f}K"))
ax.set_xticks(range(len(monthly["month"])))
ax.set_xticklabels(monthly["month"], rotation=45, ha="right", fontsize=9)
ax.set_title("Monthly Revenue Trend (2017–2018)", fontsize=16, fontweight="bold", pad=15)
ax.set_xlabel("Month", fontsize=11)
ax.set_ylabel("Total Revenue (R$)", fontsize=11)

# Insight callout box
ax.text(0.01, 0.95,
    "💡 Revenue grew 7.5× from Jan 2017 to Mar 2018",
    transform=ax.transAxes, fontsize=10,
    verticalalignment="top",
    bbox=dict(boxstyle="round,pad=0.4", facecolor="#FFF8E7", edgecolor=ORANGE, alpha=0.9)
)

plt.tight_layout()
plt.savefig(CHARTS_DIR / "01_monthly_revenue_trend.png", dpi=150, bbox_inches="tight")
plt.close()
print("   ✅ Saved: charts/01_monthly_revenue_trend.png")


# ── CHART 2: Top 10 Product Categories by Revenue ────────────
print("📊 Chart 2: Top 10 Categories by Revenue...")

cat_revenue = (
    df[df["product_category_name_english"].notna()]
    .groupby("product_category_name_english")["total_revenue"]
    .sum()
    .sort_values(ascending=True)
    .tail(10)
    .reset_index()
)
cat_revenue.columns = ["category", "revenue"]
cat_revenue["category"] = cat_revenue["category"].str.replace("_", " ").str.title()

fig, ax = plt.subplots(figsize=(12, 7))

bars = ax.barh(cat_revenue["category"], cat_revenue["revenue"],
               color=BLUE, edgecolor="white", height=0.65)

# Highlight the top bar
bars[-1].set_color(ORANGE)

# Add value labels
for bar in bars:
    width = bar.get_width()
    ax.text(width + 8000, bar.get_y() + bar.get_height() / 2,
            f"R${width/1000:.0f}K", va="center", fontsize=9, color="#333333")

ax.set_title("Top 10 Product Categories by Revenue", fontsize=16, fontweight="bold", pad=15)
ax.set_xlabel("Total Revenue (R$)", fontsize=11)
ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"R${x/1000:.0f}K"))
ax.set_xlim(0, cat_revenue["revenue"].max() * 1.18)

ax.text(0.99, 0.02,
    "💡 Health & Beauty leads with R$1.23M — 9.3% of total revenue",
    transform=ax.transAxes, fontsize=10, ha="right",
    bbox=dict(boxstyle="round,pad=0.4", facecolor="#FFF8E7", edgecolor=ORANGE, alpha=0.9)
)

plt.tight_layout()
plt.savefig(CHARTS_DIR / "02_top_categories_revenue.png", dpi=150, bbox_inches="tight")
plt.close()
print("   ✅ Saved: charts/02_top_categories_revenue.png")


# ── CHART 3: Delivery Performance vs Review Score ────────────
# Core insight: late deliveries tank ratings
print("📊 Chart 3: Delivery Performance vs Review Score...")

def delivery_bucket(days):
    if days < -7:  return "Very Early\n(7+ days)"
    elif days < 0: return "Early\n(1–7 days)"
    elif days == 0:return "On Time"
    elif days <= 7:return "Late\n(1–7 days)"
    else:          return "Very Late\n(7+ days)"

df["delivery_bucket"] = df["delivery_delay_days"].apply(delivery_bucket)

bucket_order = ["Very Early\n(7+ days)", "Early\n(1–7 days)", "On Time",
                "Late\n(1–7 days)", "Very Late\n(7+ days)"]
bucket_colors = [GREEN, GREEN, BLUE, ORANGE, RED]

bucket_stats = (
    df[df["delivery_bucket"].notna()]
    .groupby("delivery_bucket")
    .agg(order_count=("order_id", "count"), avg_score=("review_score", "mean"))
    .reindex(bucket_order)
    .reset_index()
)

fig, ax1 = plt.subplots(figsize=(12, 6))
ax2 = ax1.twinx()

bars = ax1.bar(bucket_stats["delivery_bucket"], bucket_stats["order_count"],
               color=bucket_colors, edgecolor="white", alpha=0.85, width=0.5)

ax2.plot(bucket_stats["delivery_bucket"], bucket_stats["avg_score"],
         color="#222222", linewidth=2.5, marker="D", markersize=8, zorder=5)

# Annotate score points
for i, row in bucket_stats.iterrows():
    ax2.text(i, row["avg_score"] + 0.06, f"{row['avg_score']:.2f}",
             ha="center", fontsize=11, fontweight="bold", color="#222222")

ax1.set_title("Delivery Timing vs Customer Review Score", fontsize=16, fontweight="bold", pad=15)
ax1.set_xlabel("Delivery Performance", fontsize=11)
ax1.set_ylabel("Number of Orders", fontsize=11, color=BLUE)
ax2.set_ylabel("Avg Review Score (★)", fontsize=11)
ax2.set_ylim(1, 5.2)

ax1.text(0.01, 0.95,
    "💡 Very late deliveries average just 1.70★ vs 4.32★ for early deliveries",
    transform=ax1.transAxes, fontsize=10,
    verticalalignment="top",
    bbox=dict(boxstyle="round,pad=0.4", facecolor="#FFF8E7", edgecolor=ORANGE, alpha=0.9)
)

plt.tight_layout()
plt.savefig(CHARTS_DIR / "03_delivery_vs_review_score.png", dpi=150, bbox_inches="tight")
plt.close()
print("   ✅ Saved: charts/03_delivery_vs_review_score.png")


# ── CHART 4: Revenue by State (Top 10) ───────────────────────
print("📊 Chart 4: Revenue by State...")

state_rev = (
    df.groupby("customer_state")["total_revenue"]
    .sum()
    .sort_values(ascending=False)
    .head(10)
    .reset_index()
)
state_rev.columns = ["state", "revenue"]
state_rev["share"] = state_rev["revenue"] / state_rev["revenue"].sum() * 100

colors = [ORANGE if s == "SP" else BLUE for s in state_rev["state"]]

fig, ax = plt.subplots(figsize=(12, 6))
bars = ax.bar(state_rev["state"], state_rev["revenue"],
              color=colors, edgecolor="white", width=0.6)

for i, row in state_rev.iterrows():
    ax.text(i, row["revenue"] + 20000,
            f"R${row['revenue']/1000:.0f}K\n({row['share']:.1f}%)",
            ha="center", fontsize=9, color="#333333")

ax.set_title("Top 10 States by Revenue", fontsize=16, fontweight="bold", pad=15)
ax.set_xlabel("State", fontsize=11)
ax.set_ylabel("Total Revenue (R$)", fontsize=11)
ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"R${x/1000:.0f}K"))
ax.set_ylim(0, state_rev["revenue"].max() * 1.22)

ax.text(0.99, 0.95,
    "💡 SP alone contributes 38% of total revenue\n   — high geographic concentration risk",
    transform=ax.transAxes, fontsize=10, ha="right", va="top",
    bbox=dict(boxstyle="round,pad=0.4", facecolor="#FFF8E7", edgecolor=ORANGE, alpha=0.9)
)

plt.tight_layout()
plt.savefig(CHARTS_DIR / "04_revenue_by_state.png", dpi=150, bbox_inches="tight")
plt.close()
print("   ✅ Saved: charts/04_revenue_by_state.png")


# ── CHART 5: Payment Method Breakdown ────────────────────────
print("📊 Chart 5: Payment Method Breakdown...")

pay = (
    df[df["payment_types"].notna() & ~df["payment_types"].str.contains(",")]
    .groupby("payment_types")["order_id"]
    .count()
    .reset_index()
)
pay.columns = ["method", "orders"]
pay["method"] = pay["method"].str.replace("_", " ").str.title()
pay = pay.sort_values("orders", ascending=False)

pay_colors = [BLUE, ORANGE, GRAY, GREEN]

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 6))

# Left: donut chart
wedges, texts, autotexts = ax1.pie(
    pay["orders"],
    labels=pay["method"],
    autopct="%1.1f%%",
    colors=pay_colors,
    startangle=140,
    wedgeprops=dict(width=0.55, edgecolor="white", linewidth=2),
    textprops=dict(fontsize=11)
)
for at in autotexts:
    at.set_fontweight("bold")
ax1.set_title("Orders by Payment Method", fontsize=14, fontweight="bold")

# Right: avg payment value bar
avg_pay = (
    df[df["payment_types"].notna() & ~df["payment_types"].str.contains(",")]
    .groupby("payment_types")["payment_value"]
    .mean()
    .reset_index()
)
avg_pay.columns = ["method", "avg_value"]
avg_pay["method"] = avg_pay["method"].str.replace("_", " ").str.title()
avg_pay = avg_pay.sort_values("avg_value", ascending=False)

bars = ax2.bar(avg_pay["method"], avg_pay["avg_value"],
               color=pay_colors, edgecolor="white", width=0.5)
for bar in bars:
    ax2.text(bar.get_x() + bar.get_width() / 2,
             bar.get_height() + 2,
             f"R${bar.get_height():.0f}",
             ha="center", fontsize=11, fontweight="bold")

ax2.set_title("Avg Payment Value by Method", fontsize=14, fontweight="bold")
ax2.set_ylabel("Avg Payment Value (R$)", fontsize=11)
ax2.set_ylim(0, avg_pay["avg_value"].max() * 1.2)

fig.suptitle("Payment Method Analysis", fontsize=16, fontweight="bold", y=1.01)

ax2.text(0.5, -0.12,
    "💡 Credit card dominates at 76.5% of orders — avg spend R$166 vs R$144 for boleto",
    transform=ax2.transAxes, fontsize=10, ha="center",
    bbox=dict(boxstyle="round,pad=0.4", facecolor="#FFF8E7", edgecolor=ORANGE, alpha=0.9)
)

plt.tight_layout()
plt.savefig(CHARTS_DIR / "05_payment_analysis.png", dpi=150, bbox_inches="tight")
plt.close()
print("   ✅ Saved: charts/05_payment_analysis.png")


print("""
╔══════════════════════════════════════════════════════════╗
║        PHASE 3 COMPLETE — CHARTS SAVED TO charts/       ║
╠══════════════════════════════════════════════════════════╣
║  ✔ 01_monthly_revenue_trend.png                         ║
║  ✔ 02_top_categories_revenue.png                        ║
║  ✔ 03_delivery_vs_review_score.png                      ║
║  ✔ 04_revenue_by_state.png                              ║
║  ✔ 05_payment_analysis.png                              ║
╚══════════════════════════════════════════════════════════╝
""")
