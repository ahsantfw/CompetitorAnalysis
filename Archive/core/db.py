from sqlalchemy import create_engine, MetaData, Table, Column, String, Integer, Float, Date, DateTime
from core.config import SQLALCHEMY_DATABASE_URL
import datetime
import pandas as pd
from sqlalchemy.sql import quoted_name

engine = create_engine(SQLALCHEMY_DATABASE_URL)

# Minimal schema for production
metadata = MetaData()

# Dealers table (master dealer info)
dealers = Table('dealers', metadata,
    Column('dealer_id', String(32), primary_key=True),
    Column('name', String(64)),
    Column('address', String(None)),
    Column('city', String(32)),
    Column('state', String(32)),
    Column('zip', String(32)),
    Column('created_at', DateTime),
    Column('updated_at', DateTime)
)

# Minimal, business-critical columns for raw sales
sales_raw = Table(
    quoted_name('sales_raw', True), metadata,
    Column(quoted_name('id', True), String(64), primary_key=True),  # from CSV, not auto-increment
    Column(quoted_name('vin', True), String(64)),
    Column(quoted_name('status_date', True), DateTime),
    Column(quoted_name('mc_dealer_id', True), Integer),
    Column(quoted_name('seller_name', True), String(128)),
    Column(quoted_name('make', True), String(64)),
    Column(quoted_name('model', True), String(64)),
    Column(quoted_name('year', True), Integer),
    Column(quoted_name('inventory_type', True), String(8)),
    Column(quoted_name('price', True), Float),
    Column(quoted_name('msrp', True), Float),
    Column(quoted_name('mc_dealership_group_name', True), String(128)),
    Column(quoted_name('dealer_type', True), String(16)),
    Column(quoted_name('city', True), String(32)),
    Column(quoted_name('state', True), String(32)),
    Column(quoted_name('zip', True), Integer),
    Column(quoted_name('address', True), String(None)),
    Column(quoted_name('source', True), String(128)),
    Column(quoted_name('scraped_at', True), DateTime),
    Column(quoted_name('dom', True), Integer),
    Column(quoted_name('dom_active', True), Integer)
)

# Summary tables: remove unrelated columns, keep only analysis/dashboard fields

# Dealer sales summary table
# Replace composite PK with simple autoincrement id

dealer_sales_summary = Table(
    quoted_name('dealer_sales_summary', True), metadata,
    Column(quoted_name('id', True), Integer, primary_key=True, autoincrement=True),
    Column(quoted_name('dealer_id', True), Integer),
    Column(quoted_name('period_start', True), DateTime),
    Column(quoted_name('total_sales', True), Integer),
    Column(quoted_name('new_sales', True), Integer),
    Column(quoted_name('period_end', True), DateTime),
    Column(quoted_name('last_updated', True), DateTime)
)

# Dealer sales by model table
# Replace composite PK with simple autoincrement id

dealer_sales_by_model = Table(
    quoted_name('dealer_sales_by_model', True), metadata,
    Column(quoted_name('id', True), Integer, primary_key=True, autoincrement=True),
    Column(quoted_name('dealer_id', True), Integer),
    Column(quoted_name('period_start', True), DateTime),
    Column(quoted_name('make', True), String(64)),
    Column(quoted_name('model', True), String(64)),
    Column(quoted_name('inventory_type', True), String(8)),
    Column(quoted_name('sales_count', True), Integer),
    Column(quoted_name('period_end', True), DateTime),
    Column(quoted_name('last_updated', True), DateTime)
)

def get_db_conn():
    return engine

def bulk_insert(table_name, df):
    """Bulk insert DataFrame into specified table"""
    if df.empty:
        print(f"No data to insert into {table_name}")
        return
    try:
        df.to_sql(table_name, engine, if_exists='append', index=False, chunksize=5000)
        print(f"Successfully inserted {len(df)} rows into {table_name}")
    except Exception as e:
        print(f"Error inserting into {table_name}: {str(e)}")
        try:
            df.to_sql(table_name, engine, if_exists='append', index=False, chunksize=5000)
            print(f"Successfully inserted {len(df)} rows into {table_name} (fallback method)")
        except Exception as e2:
            print(f"Error with fallback method: {str(e2)}")
            raise

def create_tables_if_not_exists():
    """Create all tables if they don't exist"""
    metadata.create_all(engine, checkfirst=True)

