# ============================================================
# E-Commerce Sales & Customer Analytics — PHASE 1: DATA CLEANING
# Author: [Your Name]
# Dataset: Brazilian E-Commerce Public Dataset by Olist (Kaggle)
# Tools: Python, pandas, numpy
# ============================================================

# ── SETUP ────────────────────────────────────────────────────
import pandas as pd
import numpy as np
import os
from pathlib import Path

# Set display options for easier reading
pd.set_option('display.max_columns', None)
pd.set_option('display.float_format', '{:.2f}'.format)

print("✅ Libraries loaded successfully")


# ── STEP 1: LOAD ALL DATASETS ────────────────────────────────
# Download the dataset from Kaggle and place all CSV files
# in a folder called 'data/' in the same directory as this script.
# Kaggle link: https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce

DATA_PATH = Path(__file__).resolve().parent / "data"

orders       = pd.read_csv(DATA_PATH / "olist_orders_dataset.csv")
order_items  = pd.read_csv(DATA_PATH / "olist_order_items_dataset.csv")
customers    = pd.read_csv(DATA_PATH / "olist_customers_dataset.csv")
products     = pd.read_csv(DATA_PATH / "olist_products_dataset.csv")
payments     = pd.read_csv(DATA_PATH / "olist_order_payments_dataset.csv")
reviews      = pd.read_csv(DATA_PATH / "olist_order_reviews_dataset.csv")
sellers      = pd.read_csv(DATA_PATH / "olist_sellers_dataset.csv")
category_map = pd.read_csv(DATA_PATH / "product_category_name_translation.csv")

print("✅ All 8 datasets loaded")


# ── STEP 2: INITIAL EXPLORATION (run once to understand data) ─
def explore(df, name):
    """Quick profile of a dataframe."""
    print(f"\n{'='*50}")
    print(f"📦 {name.upper()}")
    print(f"   Shape     : {df.shape[0]:,} rows × {df.shape[1]} columns")
    print(f"   Nulls     : {df.isnull().sum().sum()} total missing values")
    print(f"   Duplicates: {df.duplicated().sum()} duplicate rows")
    print(f"   Columns   : {list(df.columns)}")

explore(orders,      "orders")
explore(order_items, "order_items")
explore(customers,   "customers")
explore(products,    "products")
explore(payments,    "payments")
explore(reviews,     "reviews")
explore(sellers,     "sellers")


# ── STEP 3: CLEAN ORDERS TABLE ───────────────────────────────
print("\n\n🔧 Cleaning: orders")

# 3a. Convert all timestamp columns from string to datetime
timestamp_cols = [
    'order_purchase_timestamp',
    'order_approved_at',
    'order_delivered_carrier_date',
    'order_delivered_customer_date',
    'order_estimated_delivery_date'
]
for col in timestamp_cols:
    orders[col] = pd.to_datetime(orders[col])

# 3b. Drop rows where order_status is not 'delivered'
#     (cancelled/unavailable orders skew revenue metrics)
print(f"   Order status counts:\n{orders['order_status'].value_counts()}")
orders_clean = orders[orders['order_status'] == 'delivered'].copy()
print(f"   Rows after filtering to 'delivered': {len(orders_clean):,}")

# 3c. Drop rows missing the actual delivery date (can't calculate delays)
missing_delivery = orders_clean['order_delivered_customer_date'].isnull().sum()
print(f"   Rows missing delivery date: {missing_delivery}")
orders_clean.dropna(subset=['order_delivered_customer_date'], inplace=True)

# 3d. Engineer: delivery delay in days (positive = late, negative = early)
orders_clean['delivery_delay_days'] = (
    orders_clean['order_delivered_customer_date'] -
    orders_clean['order_estimated_delivery_date']
).dt.days

# 3e. Engineer: order processing time (purchase → approval)
orders_clean['processing_time_hrs'] = (
    orders_clean['order_approved_at'] -
    orders_clean['order_purchase_timestamp']
).dt.total_seconds() / 3600

# 3f. Extract year and month for time series analysis later
orders_clean['order_year']  = orders_clean['order_purchase_timestamp'].dt.year
orders_clean['order_month'] = orders_clean['order_purchase_timestamp'].dt.month
orders_clean['order_yearmonth'] = orders_clean['order_purchase_timestamp'].dt.to_period('M').astype(str)

print(f"✅ Orders cleaned — {len(orders_clean):,} rows remain")
print(f"   New columns added: delivery_delay_days, processing_time_hrs, order_year, order_month, order_yearmonth")


# ── STEP 4: CLEAN ORDER ITEMS TABLE ─────────────────────────
print("\n🔧 Cleaning: order_items")

order_items_clean = order_items.copy()

# 4a. Convert shipping date
order_items_clean['shipping_limit_date'] = pd.to_datetime(order_items_clean['shipping_limit_date'])

# 4b. Check for price anomalies (zero or negative prices)
zero_price = (order_items_clean['price'] <= 0).sum()
print(f"   Rows with price <= 0: {zero_price}")
order_items_clean = order_items_clean[order_items_clean['price'] > 0]

# 4c. Aggregate to order level (some orders have multiple items)
order_items_agg = order_items_clean.groupby('order_id').agg(
    total_items    = ('order_item_id', 'count'),       # count item records per order
    total_revenue  = ('price', 'sum'),
    total_freight  = ('freight_value', 'sum'),
    unique_sellers = ('seller_id', 'nunique')
).reset_index()

print(f"✅ Order items aggregated — {len(order_items_agg):,} unique orders")


# ── STEP 5: CLEAN PRODUCTS TABLE ────────────────────────────
print("\n🔧 Cleaning: products")

products_clean = products.copy()

# 5a. Translate category names to English
products_clean = products_clean.merge(category_map, on='product_category_name', how='left')

# 5b. Fill missing English names with the original Portuguese name
products_clean['product_category_name_english'] = (
    products_clean['product_category_name_english'].fillna(products_clean['product_category_name'])
)

# 5c. Drop columns irrelevant to our analysis (physical dimensions)
drop_cols = ['product_name_lenght', 'product_description_lenght',
             'product_photos_qty', 'product_weight_g',
             'product_length_cm', 'product_height_cm', 'product_width_cm']
products_clean.drop(columns=drop_cols, inplace=True, errors='ignore')

print(f"✅ Products cleaned — {len(products_clean):,} rows")
print(f"   Unique categories (English): {products_clean['product_category_name_english'].nunique()}")


# ── STEP 6: CLEAN PAYMENTS TABLE ────────────────────────────
print("\n🔧 Cleaning: payments")

# 6a. Some orders have multiple payment methods — aggregate to order level
payments_agg = payments.groupby('order_id').agg(
    payment_value        = ('payment_value', 'sum'),
    payment_installments = ('payment_installments', 'max'),
    payment_types        = ('payment_type', lambda x: ','.join(x.unique()))
).reset_index()

# 6b. Simplify: mark whether boleto (bank slip) was used (common in Brazil)
payments_agg['used_boleto'] = payments_agg['payment_types'].str.contains('boleto').astype(int)

print(f"✅ Payments aggregated — {len(payments_agg):,} unique orders")


# ── STEP 7: CLEAN REVIEWS TABLE ─────────────────────────────
print("\n🔧 Cleaning: reviews")

reviews_clean = reviews[['order_id', 'review_score', 'review_creation_date']].copy()

# 7a. Some orders have multiple reviews (re-surveys) — keep most recent
reviews_clean['review_creation_date'] = pd.to_datetime(reviews_clean['review_creation_date'])
reviews_clean.sort_values('review_creation_date', ascending=False, inplace=True)
reviews_clean.drop_duplicates(subset='order_id', keep='first', inplace=True)

# 7b. Classify satisfaction level
def classify_satisfaction(score):
    if score >= 4: return 'Satisfied'
    elif score == 3: return 'Neutral'
    else: return 'Dissatisfied'

reviews_clean['satisfaction'] = reviews_clean['review_score'].apply(classify_satisfaction)

print(f"✅ Reviews cleaned — {len(reviews_clean):,} unique orders")
print(f"   Score distribution:\n{reviews_clean['review_score'].value_counts().sort_index()}")


# ── STEP 8: BUILD THE MASTER DATAFRAME ──────────────────────
print("\n🔧 Building master DataFrame...")

# Join everything around the orders table as the anchor
master = orders_clean \
    .merge(customers,       on='customer_id',  how='left') \
    .merge(order_items_agg, on='order_id',     how='left') \
    .merge(payments_agg,    on='order_id',     how='left') \
    .merge(reviews_clean[['order_id', 'review_score', 'satisfaction']],
                            on='order_id',     how='left')

# Add product category (via order_items → products, taking first product per order)
first_item = order_items_clean.drop_duplicates(subset='order_id')[['order_id', 'product_id']]
first_item = first_item.merge(
    products_clean[['product_id', 'product_category_name_english']],
    on='product_id', how='left'
)
master = master.merge(first_item[['order_id', 'product_category_name_english']],
                      on='order_id', how='left')

print(f"✅ Master DataFrame built: {master.shape[0]:,} rows × {master.shape[1]} columns")


# ── STEP 9: FINAL QUALITY CHECK ──────────────────────────────
print("\n📊 Final quality check:")
print(f"   Total rows       : {len(master):,}")
print(f"   Total columns    : {master.shape[1]}")
print(f"   Missing values   :\n{master.isnull().sum()[master.isnull().sum() > 0]}")
print(f"   Date range       : {master['order_purchase_timestamp'].min().date()} → "
      f"{master['order_purchase_timestamp'].max().date()}")
print(f"   Avg review score : {master['review_score'].mean():.2f}")
print(f"   Avg order revenue: R$ {master['total_revenue'].mean():.2f}")
print(f"   Late deliveries  : {(master['delivery_delay_days'] > 0).sum():,} "
      f"({(master['delivery_delay_days'] > 0).mean()*100:.1f}%)")


# ── STEP 10: EXPORT CLEAN DATA ───────────────────────────────
output_path = DATA_PATH / "olist_master_clean.csv"
master.to_csv(output_path, index=False)
print(f"\n✅ Clean master file saved to: {output_path}")
print("   → Use this file for all subsequent phases (SQL, EDA, Dashboard)")


# ── SUMMARY OF WHAT WAS DONE ─────────────────────────────────
print("""
╔══════════════════════════════════════════════════════════╗
║           PHASE 1 COMPLETE — CLEANING SUMMARY           ║
╠══════════════════════════════════════════════════════════╣
║  ✔ Loaded 8 CSV tables from the Olist dataset           ║
║  ✔ Filtered to 'delivered' orders only                  ║
║  ✔ Converted all timestamps to datetime dtype           ║
║  ✔ Engineered delivery_delay_days & processing_time_hrs ║
║  ✔ Aggregated order_items and payments to order level   ║
║  ✔ Translated product categories to English             ║
║  ✔ Deduplicated reviews, classified satisfaction        ║
║  ✔ Built and exported a single analysis-ready CSV       ║
╚══════════════════════════════════════════════════════════╝
""")
