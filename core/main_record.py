import pandas as pd
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.config import ESSENTIAL_COLUMNS, COLUMN_DTYPES
from core.loader import load_inventory_csv, load_parquet_dataset, parallel_chunk_process

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
    os.makedirs(os.path.dirname(MAIN_RECORD_PATH), exist_ok=True)
    df = enforce_types(df)
    df.reset_index(drop=True).to_parquet(MAIN_RECORD_PATH, index=False)

# Deduplicate a DataFrame by VIN, keeping the latest status_date
# Assumes status_date is a string in YYYY-MM-DD or similar format

def deduplicate_by_vin(df):
    if 'status_date' in df.columns:
        df['status_date'] = pd.to_datetime(df['status_date'], errors='coerce')
        df = df.sort_values(['vin', 'status_date'], ascending=[True, False])
        df = df.drop_duplicates('vin', keep='first')
    else:
        df = df.drop_duplicates('vin', keep='first')
    return df

# Update main record with today's chunk (in-place, chunked)
def update_main_record_chunk(main_df, today_chunk):
    today_chunk = deduplicate_by_vin(today_chunk)
    today_chunk = today_chunk.set_index('vin', drop=False)
    # For overlapping VINs, keep the record with the latest status_date
    overlap = main_df.index.intersection(today_chunk.index)
    for vin in overlap:
        # Compare status_date, update only if new is newer
        try:
            main_date = pd.to_datetime(main_df.at[vin, 'status_date'], errors='coerce')
            today_date = pd.to_datetime(today_chunk.at[vin, 'status_date'], errors='coerce')
            if today_date > main_date:
                main_df.loc[vin] = today_chunk.loc[vin]
        except Exception:
            # If any error, just update
            main_df.loc[vin] = today_chunk.loc[vin]
    # Add new VINs
    new_vins = today_chunk.index.difference(main_df.index)
    if len(new_vins) > 0:
        main_df = pd.concat([main_df, today_chunk.loc[new_vins]], axis=0)
    return main_df

# Full update for a day's feed (chunked, parallel for Parquet)
def update_main_record_from_feed(today_path, chunksize=100_000, max_workers=4):
    main_df = load_main_record()
    if os.path.isdir(today_path) or today_path.endswith('.parquet/'):
        # Parallel processing for Parquet dataset
        def process_chunk(chunk_path):
            chunk = pd.read_parquet(chunk_path)
            return chunk
        chunk_list = parallel_chunk_process(today_path, process_chunk, max_workers=max_workers)
        # Concatenate all chunks, deduplicate by VIN (latest status_date)
        if chunk_list:
            all_today = pd.concat(chunk_list, ignore_index=True)
            all_today = deduplicate_by_vin(all_today)
            all_today = all_today.set_index('vin', drop=False)
            # Merge with main_df: update only if new is newer
            overlap = main_df.index.intersection(all_today.index)
            for vin in overlap:
                try:
                    main_date = pd.to_datetime(main_df.at[vin, 'status_date'], errors='coerce')
                    today_date = pd.to_datetime(all_today.at[vin, 'status_date'], errors='coerce')
                    if today_date > main_date:
                        main_df.loc[vin] = all_today.loc[vin]
                except Exception:
                    main_df.loc[vin] = all_today.loc[vin]
            # Add new VINs
            new_vins = all_today.index.difference(main_df.index)
            if len(new_vins) > 0:
                main_df = pd.concat([main_df, all_today.loc[new_vins]], axis=0)
    else:
        # Sequential for CSV
        for chunk in load_inventory_csv(today_path, chunksize=chunksize):
            main_df = update_main_record_chunk(main_df, chunk)
    save_main_record(main_df)
    return main_df 