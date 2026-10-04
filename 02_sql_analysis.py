# ============================================================
# E-Commerce Sales & Customer Analytics — PHASE 2: SQL ANALYSIS
# Author: [Your Name]
# Tools: Python, SQLite (run SQL queries on your clean CSV)
# Run this AFTER Phase 1 — needs data/olist_master_clean.csv
# ============================================================

import pandas as pd
import sqlite3
from pathlib import Path

# ── SETUP: Load clean CSV into an in-memory SQL database ─────
# This lets you write real SQL without needing a separate DB server.
# In a real job, this data would already live in PostgreSQL / BigQuery / Snowflake.

BASE_DIR = Path(__file__).resolve().parent
DATA_PATH = BASE_DIR / "data" / "olist_master_clean.csv"

df = pd.read_csv(DATA_PATH)

conn = sqlite3.connect(":memory:")
df.to_sql("orders", conn, index=False, if_exists="replace")

# Load secondary table for JOINs
TRANSLATION_PATH = BASE_DIR / "data" / "product_category_name_translation.csv"
translation_df = pd.read_csv(TRANSLATION_PATH)
translation_df.to_sql("category_translation", conn, index=False, if_exists="replace")

def run_query(title, sql):
    """Run a SQL query and print the result nicely."""
    print(f"\n{'='*60}")
    print(f"📊 {title}")
    print('='*60)
    result = pd.read_sql_query(sql, conn)
    print(result.to_string(index=False))
    return result

print("✅ Data loaded into SQL — 96,470 rows ready to query")
print(f"   Columns available: {list(df.columns)}\n")


# ── QUESTION 1: Total Revenue, Orders & Avg Order Value ──────
# WHY: Every business wants a top-line summary first.
run_query(
    "Q1: Overall Business Summary",
    """
    SELECT
        COUNT(DISTINCT order_id)              AS total_orders,
        ROUND(SUM(total_revenue), 2)          AS total_revenue_R$,
        ROUND(AVG(total_revenue), 2)          AS avg_order_value_R$,
        ROUND(AVG(review_score), 2)           AS avg_review_score,
        ROUND(AVG(total_items), 2)            AS avg_items_per_order
    FROM orders
    """
)


# ── QUESTION 2: Revenue by State (Top 10) ────────────────────
# WHY: Shows geographic business distribution — useful for marketing & logistics.
run_query(
    "Q2: Top 10 States by Revenue",
    """
    SELECT
        customer_state                                AS state,
        COUNT(DISTINCT order_id)                      AS total_orders,
        ROUND(SUM(total_revenue), 2)                  AS total_revenue_R$,
        ROUND(SUM(total_revenue) * 100.0 /
              SUM(SUM(total_revenue)) OVER (), 1)     AS revenue_share_pct
    FROM orders
    GROUP BY customer_state
    ORDER BY total_revenue_R$ DESC
    LIMIT 10
    """
)


# ── QUESTION 3: Monthly Revenue Trend ────────────────────────
# WHY: Reveals growth trajectory — is the business scaling?
run_query(
    "Q3: Monthly Revenue Trend (2017–2018)",
    """
    SELECT
        order_yearmonth                       AS month,
        COUNT(DISTINCT order_id)              AS orders,
        ROUND(SUM(total_revenue), 2)          AS revenue_R$
    FROM orders
    WHERE order_year IN (2017, 2018)
    GROUP BY order_yearmonth
    ORDER BY order_yearmonth
    """
)


# ── QUESTION 4: Top 10 Product Categories by Revenue ─────────
# WHY: Identifies which categories drive the business.
run_query(
    "Q4: Top 10 Product Categories by Revenue",
    """
    SELECT
        product_category_name_english         AS category,
        COUNT(DISTINCT order_id)              AS total_orders,
        ROUND(SUM(total_revenue), 2)          AS total_revenue_R$,
        ROUND(AVG(total_revenue), 2)          AS avg_order_value_R$,
        ROUND(AVG(review_score), 2)           AS avg_review_score
    FROM orders
    WHERE product_category_name_english IS NOT NULL
    GROUP BY product_category_name_english
    ORDER BY total_revenue_R$ DESC
    LIMIT 10
    """
)


# ── QUESTION 5: Late Delivery Rate by State (Using CTE) ───────
# WHY: Logistics performance varies by region — key ops insight.
run_query(
    "Q5: Late Delivery Rate by State (Top 10 Worst)",
    """
    WITH StateStats AS (
        SELECT
            customer_state,
            COUNT(*) AS total_orders,
            SUM(CASE WHEN delivery_delay_days > 0 THEN 1 ELSE 0 END) AS late_orders,
            AVG(CASE WHEN delivery_delay_days > 0 THEN delivery_delay_days END) AS avg_delay_days
        FROM orders
        GROUP BY customer_state
    )
    SELECT
        customer_state AS state,
        total_orders,
        late_orders,
        ROUND(late_orders * 100.0 / total_orders, 1) AS late_rate_pct,
        ROUND(avg_delay_days, 1) AS avg_delay_days
    FROM StateStats
    WHERE total_orders > 100
    ORDER BY late_rate_pct DESC
    LIMIT 10
    """
)


# ── QUESTION 6: Review Score by Product Category ─────────────
# WHY: Identifies categories with quality or fulfillment problems.
run_query(
    "Q6: Lowest-Rated Product Categories (min 200 orders)",
    """
    SELECT
        product_category_name_english         AS category,
        COUNT(*)                              AS total_orders,
        ROUND(AVG(review_score), 2)           AS avg_review_score,
        SUM(CASE WHEN review_score <= 2
            THEN 1 ELSE 0 END)               AS bad_reviews,
        ROUND(SUM(CASE WHEN review_score <= 2 THEN 1 ELSE 0 END)
            * 100.0 / COUNT(*), 1)           AS bad_review_pct
    FROM orders
    WHERE product_category_name_english IS NOT NULL
      AND review_score IS NOT NULL
    GROUP BY product_category_name_english
    HAVING total_orders >= 200
    ORDER BY avg_review_score ASC
    LIMIT 10
    """
)


# ── QUESTION 7: Payment Method Breakdown ─────────────────────
# WHY: Helps finance team understand how customers prefer to pay.
run_query(
    "Q7: Payment Method Analysis",
    """
    SELECT
        payment_types                                         AS payment_method,
        COUNT(*)                                              AS total_orders,
        ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 1)   AS order_share_pct,
        ROUND(AVG(payment_value), 2)                          AS avg_payment_R$,
        ROUND(AVG(payment_installments), 1)                   AS avg_installments
    FROM orders
    WHERE payment_types IS NOT NULL
      AND payment_types NOT LIKE '%,%'
    GROUP BY payment_types
    ORDER BY total_orders DESC
    """
)


# ── QUESTION 8: Delivery Performance Summary ─────────────────
# WHY: Operations teams care deeply about SLA (service level agreement) compliance.
run_query(
    "Q8: Delivery Performance — On Time vs Late",
    """
    SELECT
        CASE
            WHEN delivery_delay_days < -7  THEN 'Very Early (7+ days)'
            WHEN delivery_delay_days < 0   THEN 'Early (1–7 days)'
            WHEN delivery_delay_days = 0   THEN 'On Time'
            WHEN delivery_delay_days <= 7  THEN 'Late (1–7 days)'
            ELSE                                'Very Late (7+ days)'
        END                                               AS delivery_bucket,
        COUNT(*)                                          AS orders,
        ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 1) AS pct_of_total,
        ROUND(AVG(review_score), 2)                       AS avg_review_score
    FROM orders
    WHERE delivery_delay_days IS NOT NULL
    GROUP BY delivery_bucket
    ORDER BY MIN(delivery_delay_days)
    """
)


# ── QUESTION 9: High Value Orders Analysis ───────────────────
# WHY: Premium customers behave differently — do they rate higher? Get faster delivery?
run_query(
    "Q9: Order Value Segments — Do Premium Customers Get Better Service?",
    """
    SELECT
        CASE
            WHEN total_revenue < 50   THEN '1. Low (<R$50)'
            WHEN total_revenue < 150  THEN '2. Mid (R$50–150)'
            WHEN total_revenue < 500  THEN '3. High (R$150–500)'
            ELSE                           '4. Premium (R$500+)'
        END                                               AS order_segment,
        COUNT(*)                                          AS total_orders,
        ROUND(AVG(review_score), 2)                       AS avg_review_score,
        ROUND(AVG(delivery_delay_days) * -1, 1)           AS avg_days_early,
        ROUND(AVG(total_items), 1)                        AS avg_items
    FROM orders
    GROUP BY order_segment
    ORDER BY order_segment
    """
)


# ── QUESTION 10: Best & Worst Month for Business (2017) ──────
# WHY: Reveals seasonality — important for inventory and staffing planning.
# Using 2017 only to ensure complete months are compared fairly.
run_query(
    "Q10: Best and Worst Months in 2017 (by Order Volume)",
    """
    SELECT
        CASE order_month
            WHEN 1  THEN 'January'   WHEN 2  THEN 'February'
            WHEN 3  THEN 'March'     WHEN 4  THEN 'April'
            WHEN 5  THEN 'May'       WHEN 6  THEN 'June'
            WHEN 7  THEN 'July'      WHEN 8  THEN 'August'
            WHEN 9  THEN 'September' WHEN 10 THEN 'October'
            WHEN 11 THEN 'November'  WHEN 12 THEN 'December'
        END                                               AS month_name,
        order_month,
        COUNT(*)                                          AS total_orders,
        ROUND(SUM(total_revenue), 2)                      AS total_revenue_R$,
        ROUND(AVG(review_score), 2)                       AS avg_review_score
    FROM orders
    WHERE order_year = 2017
    GROUP BY order_month
    ORDER BY total_orders DESC
    """
)


# ── QUESTION 11: Category Translation Analysis (JOIN) ────────
# WHY: Demonstrates joining the denormalized orders table with a dimension table.
run_query(
    "Q11: Top 5 Categories (Portuguese & English) by Revenue",
    """
    SELECT
        t.product_category_name               AS category_pt,
        o.product_category_name_english       AS category_en,
        COUNT(DISTINCT o.order_id)            AS total_orders,
        ROUND(SUM(o.total_revenue), 2)        AS total_revenue_R$
    FROM orders o
    INNER JOIN category_translation t
        ON o.product_category_name_english = t.product_category_name_english
    WHERE o.product_category_name_english IS NOT NULL
    GROUP BY o.product_category_name_english, t.product_category_name
    ORDER BY total_revenue_R$ DESC
    LIMIT 5
    """
)

conn.close()

print("""
╔══════════════════════════════════════════════════════════╗
║          PHASE 2 COMPLETE — SQL ANALYSIS SUMMARY        ║
╠══════════════════════════════════════════════════════════╣
║  ✔ Q1:  Overall business KPIs                           ║
║  ✔ Q2:  Revenue by state (geographic distribution)      ║
║  ✔ Q3:  Monthly revenue trend (growth over time)        ║
║  ✔ Q4:  Top product categories by revenue               ║
║  ✔ Q5:  Late delivery rate by state (using CTE)         ║
║  ✔ Q6:  Lowest rated product categories                 ║
║  ✔ Q7:  Payment method breakdown                        ║
║  ✔ Q8:  Delivery performance buckets                    ║
║  ✔ Q9:  Premium vs low-value order comparison           ║
║  ✔ Q10: Seasonality (2017 only)                         ║
║  ✔ Q11: Category revenue (JOIN with translation table)  ║
╚══════════════════════════════════════════════════════════╝
""")
