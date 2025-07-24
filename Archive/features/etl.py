import sys
import pandas as pd
from core.loader import load_csv_chunked
from core.db import create_tables_if_not_exists, bulk_insert
from core.sales import precompute_dealer_stats
import uuid
import sqlalchemy
from core.db import engine

# Usage: python features/etl.py data/inventory_2025_07.csv

SALES_RAW_COLUMNS = [
    'id',
    'vin',
    'status_date',
    'mc_dealer_id',
    'seller_name',
    'make',
    'model',
    'year',
    'inventory_type',
    'price',
    'msrp',
    'mc_dealership_group_name',
    'dealer_type',
    'city', 'state', 'zip', 'address',
    'source', 'scraped_at', 'dom', 'dom_active'
]

TRUNCATE_MAP = {
    'id': 64,
    'vin': 64,
    'mc_dealer_id': None,
    'seller_name': 128,
    'make': 64,
    'model': 64,
    'year': None,
    'inventory_type': 8,
    'price': None,
    'msrp': None,
    'mc_dealership_group_name': 128,
    'dealer_type': 16,
    'city': 32, 'state': 32, 'zip': None,
    'address': None,
    'source': 128, 'dom': None, 'dom_active': None
}


def align_and_cast(df):
    # Ensure all required columns are present and in the correct order
    for col in SALES_RAW_COLUMNS:
        if col not in df.columns:
            df[col] = None
    df = df[SALES_RAW_COLUMNS]
        # Filter for new cars only
    if 'inventory_type' in df.columns:
        df = df[df['inventory_type'].str.lower() == 'new']
    # Fix null/empty ids by generating a UUID
    df['id'] = df['id'].fillna('').replace('', None)
    df['id'] = df['id'].apply(lambda x: x if x else str(uuid.uuid4())[:64])
    # Truncate string columns to schema length
    for col in SALES_RAW_COLUMNS:
        maxlen = TRUNCATE_MAP.get(col, 32)
        if maxlen is not None and df[col].dtype == 'object':
            df[col] = df[col].astype(str).where(df[col].notnull(), None)
            df[col] = df[col].apply(lambda x: x[:maxlen] if isinstance(x, str) else x)
    # Cast types for numerics
    for col in ['mc_dealer_id', 'zip', 'year', 'dom', 'dom_active', 'price', 'msrp']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
    # Dates: parse ISO8601 strings to datetime
    for col in ['status_date', 'scraped_at']:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors='coerce', utc=True)
            # Remove timezone and microseconds for SQL Server compatibility
            df[col] = df[col].dt.tz_localize(None)
            df[col] = df[col].dt.floor('S')
    # Ensure all integer columns are int or None
    for col in ['mc_dealer_id', 'zip', 'year', 'dom', 'dom_active']:
        if col in df.columns:
            df[col] = df[col].apply(lambda x: int(x) if pd.notnull(x) else None)
    # Ensure all string columns are None if missing
    for col in df.select_dtypes(include='object').columns:
        df[col] = df[col].where(df[col].notnull(), None)
    # Ensure all float columns are None if missing
    for col in df.select_dtypes(include='float').columns:
        df[col] = df[col].where(df[col].notnull(), None)
    # Final check: columns must match schema exactly
    return df

def drop_existing_tables():
    """Drop existing tables to recreate with correct schema"""
    from core.db import engine, metadata
    from sqlalchemy import text
    with engine.connect() as conn:
        # Drop tables in reverse order of dependencies
        tables_to_drop = ['dealer_sales_by_model', 'dealer_sales_summary', 'dealers']
        for table in tables_to_drop:
            try:
                conn.execute(text(f"DROP TABLE IF EXISTS {table}"))
                print(f"Dropped table: {table}")
            except Exception as e:
                print(f"Could not drop {table}: {str(e)}")
        conn.commit()

# def drop_sales_raw_table():
#     from core.db import engine
#     with engine.connect() as conn:
#         try:
#             conn.execute(text("DROP TABLE IF EXISTS sales_raw"))
#             print("Dropped table: sales_raw")
#         except Exception as e:
#             print(f"Could not drop sales_raw: {str(e)}")
#         conn.commit()

def main(sales_csv):
    print('Dropping existing tables...')
    # drop_existing_tables()
    
    print('Creating tables if not exist...')
    create_tables_if_not_exists()

    print(f'Loading sales data from {sales_csv}...')
    df = load_csv_chunked(sales_csv, date_col='status_date')
    print(f'Loaded {len(df):,} rows.')

    print('Aligning columns and types...')
    df = align_and_cast(df)
    print('DataFrame columns before insert:')
    print(df.columns)
    print(df.dtypes)

    # Debug: Check DataFrame vs DB columns
    import sqlalchemy
    inspector = sqlalchemy.inspect(engine)
    cols = inspector.get_columns('sales_raw')
    db_cols = [c['name'] for c in cols]
    print('DB columns:', db_cols)
    print('DF col count:', len(df.columns), 'DB col count:', len(db_cols))
    print('DF columns repr:', [repr(col) for col in df.columns])
    print('DB columns repr:', [repr(col) for col in db_cols])
    if list(df.columns) != db_cols:
        assert False, f"DataFrame columns do not match DB schema!\nDF: {list(df.columns)}\nDB: {db_cols}"
    # Check for null or duplicate IDs
    if df['id'].isnull().any():
        raise ValueError("Null value found in 'id' column (primary key)!")
    if df['id'].duplicated().any():
        raise ValueError("Duplicate value found in 'id' column (primary key)!")

    # Convert Int64 columns to native int or None for SQL Server compatibility
    for col in df.columns:
        if pd.api.types.is_integer_dtype(df[col]) and str(df[col].dtype) == 'Int64':
            df[col] = df[col].astype(object).where(df[col].notnull(), None)

    # # Limit to first 10 rows for testing
    # df = df.head(50000)

    # print('Inserting raw sales to DB...')
    # bulk_insert('sales_raw', df)

    print('Aggregating dealer stats...')
    summary, by_model = precompute_dealer_stats(df)
    print('Inserting dealer sales summary...')
    bulk_insert('dealer_sales_summary', summary)
    print('Inserting dealer sales by model...')
    bulk_insert('dealer_sales_by_model', by_model)
    print('ETL complete.')

    print('Creating indexes for faster queries...')
    create_indexes()

def create_indexes():
    """Create indexes for faster dashboard and API queries"""
    from core.db import engine
    from sqlalchemy import text
    
    with engine.connect() as conn:
        # Index for dealer sales summary queries
        conn.execute(text("""
            IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'idx_dealer_period')
            CREATE INDEX idx_dealer_period ON dealer_sales_summary (dealer_id, period_start)
        """))
        # Index for dealer sales by model queries
        conn.execute(text("""
            IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'idx_dealer_model_period')
            CREATE INDEX idx_dealer_model_period ON dealer_sales_by_model (dealer_id, period_start, make, model)
        """))
        # Index for raw sales queries
        conn.execute(text("""
            IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'idx_sales_dealer_date')
            CREATE INDEX idx_sales_dealer_date ON sales_raw (mc_dealer_id, status_date)
        """))
        conn.commit()

if __name__ == '__main__':
    sales_csv = sys.argv[1] if len(sys.argv) > 1 else 'data/inventory_2025_07.csv'
    main(sales_csv)
