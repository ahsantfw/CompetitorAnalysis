import pandas as pd
import os
import sys, os
print(sys.path)
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.config import ESSENTIAL_COLUMNS, COLUMN_DTYPES

MAIN_RECORD_PATH = "state/main_record.parquet"

def enforce_types(df):
    for col, dtype in COLUMN_DTYPES.items():
        if col in df.columns:
            if dtype is int:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(-1).astype(int)
            elif dtype is float:
                df[col] = pd.to_numeric(df[col], errors='coerce')
            else:
                df[col] = df[col].astype(dtype, errors='ignore')
            # Print warning if any values could not be converted
            if df[col].isnull().any():
                print(f"Warning: Nulls found in column {col} after type conversion.")
    return df

# Load the main record (VIN-indexed DataFrame)
def load_main_record():
    if os.path.exists(MAIN_RECORD_PATH):
        df = pd.read_parquet(MAIN_RECORD_PATH)
        if 'vin' in df.columns:
            df = df.set_index('vin', drop=False)
        return df
    else:
        return pd.DataFrame(columns=ESSENTIAL_COLUMNS).set_index('vin', drop=False)

# Save the main record
def save_main_record(df):
    df = enforce_types(df)
    df.reset_index(drop=True).to_parquet(MAIN_RECORD_PATH, index=False)

# Update main record with today's chunk (in-place, chunked)
def update_main_record_chunk(main_df, today_chunk):
    today_chunk = today_chunk.set_index('vin', drop=False)
    # Update existing VINs
    overlap = main_df.index.intersection(today_chunk.index)
    main_df.loc[overlap] = today_chunk.loc[overlap]
    # Add new VINs
    new_vins = today_chunk.index.difference(main_df.index)
    if len(new_vins) > 0:
        main_df = pd.concat([main_df, today_chunk.loc[new_vins]], axis=0)
    return main_df

# Full update for a day's feed (chunked)
def update_main_record_from_feed(today_path, chunksize=100_000):
    main_df = load_main_record()
    from core.loader import load_inventory_csv
    for chunk in load_inventory_csv(today_path, chunksize=chunksize):
        main_df = update_main_record_chunk(main_df, chunk)
    save_main_record(main_df)
    return main_df 