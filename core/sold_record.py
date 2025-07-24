import pandas as pd
import os
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.config import ESSENTIAL_COLUMNS, COLUMN_DTYPES

SOLD_RECORD_PATH = "state/sold_record.parquet"

def enforce_types(df):
    for col, dtype in COLUMN_DTYPES.items():
        if col in df.columns:
            if dtype is int:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(-1).astype(int)
            elif dtype is float:
                df[col] = pd.to_numeric(df[col], errors='coerce')
            else:
                df[col] = df[col].astype(dtype, errors='ignore')
            if df[col].isnull().any():
                print(f"Warning: Nulls found in column {col} after type conversion.")
    return df

# Load the sold record
def load_sold_record():
    if os.path.exists(SOLD_RECORD_PATH):
        return pd.read_parquet(SOLD_RECORD_PATH)
    else:
        return pd.DataFrame(columns=ESSENTIAL_COLUMNS + ['sold_date'])

def save_sold_record(df):
    df = enforce_types(df)
    df.to_parquet(SOLD_RECORD_PATH, index=False)

# Update sold record: find VINs in main_df but not in today_df, mark as sold
def update_sold_record(main_df, today_df, today_date):
    today_vins = set(today_df['vin'])
    main_vins = set(main_df['vin'])
    sold_vins = main_vins - today_vins
    if not sold_vins:
        return load_sold_record()
    sold_rows = main_df[main_df['vin'].isin(sold_vins)].copy()
    sold_rows['sold_date'] = today_date
    sold_record = load_sold_record()
    sold_record = pd.concat([sold_record, sold_rows], ignore_index=True)
    save_sold_record(sold_record)
    return sold_record 