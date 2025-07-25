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
                print(f"[WARN] Nulls found in column {col} after type conversion.")
    return df

# Load the main record (VIN-indexed DataFrame)
def load_main_record():
    print("[MAIN] Loading main record...")
    if os.path.exists(MAIN_RECORD_PATH):
        df = pd.read_parquet(MAIN_RECORD_PATH)
        if 'vin' in df.columns:
            df = df.set_index('vin', drop=False)
        print(f"[MAIN] Main record loaded. Rows: {len(df)}")
        return df
    else:
        print("[MAIN] No main record found. Initializing empty DataFrame.")
        return pd.DataFrame(columns=ESSENTIAL_COLUMNS).set_index('vin', drop=False)

# Save the main record
def save_main_record(df):
    os.makedirs(os.path.dirname(MAIN_RECORD_PATH), exist_ok=True)
    df = enforce_types(df)
    df.reset_index(drop=True).to_parquet(MAIN_RECORD_PATH, index=False)
    print(f"[MAIN] Main record saved. Rows: {len(df)}")

# Deduplicate a DataFrame by VIN, keeping the latest status_date
# Assumes status_date is a string in YYYY-MM-DD or similar format

def deduplicate_by_vin(df):
    if 'status_date' in df.columns:
        df['status_date'] = pd.to_datetime(df['status_date'], errors='coerce')
        df = df.reset_index(drop=True)
        print(f"[MAIN] Reset index before deduplication. Shape: {df.shape}")
        df = df.sort_values(['vin', 'status_date'], ascending=[True, False])
        df = df.drop_duplicates('vin', keep='first')
    else:
        df = df.reset_index(drop=True)
        print(f"[MAIN] Reset index before deduplication. Shape: {df.shape}")
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
    import time
    t0 = time.time()
    main_df = load_main_record()
    print(f"[MAIN] Main record shape: {main_df.shape}")
    t1 = time.time()
    print(f"[MAIN] Loading today's data from: {today_path}")
    if os.path.isdir(today_path) or today_path.endswith('.parquet/'):
        print(f"[MAIN] Processing Parquet chunks in batches (max_workers={max_workers})...")
        batch_num = 0
        total_rows = 0
        for batch_chunks in parallel_chunk_process(today_path, lambda f: pd.read_parquet(f), max_workers=max_workers):
            batch_num += 1
            batch_df = pd.concat(batch_chunks, ignore_index=True)
            print(f"[MAIN] Batch {batch_num}: Loaded {len(batch_df)} rows from {len(batch_chunks)} chunks.")
            batch_df = deduplicate_by_vin(batch_df)
            print(f"[MAIN] Batch {batch_num}: Deduplicated to {len(batch_df)} rows.")
            # Merge batch with main_df (vectorized)
            batch_df = batch_df.set_index('vin', drop=False)
            combined = pd.concat([main_df, batch_df], axis=0)
            combined['status_date'] = pd.to_datetime(combined['status_date'], errors='coerce')
            combined = combined.reset_index(drop=True)
            print(f"[MAIN] Reset index before sorting/merge. Shape: {combined.shape}")
            combined = combined.sort_values(['vin', 'status_date'], ascending=[True, False])
            combined = combined.drop_duplicates('vin', keep='first')
            main_df = combined
            total_rows += len(batch_df)
            print(f"[MAIN] Batch {batch_num}: Main record updated. Current shape: {main_df.shape}")
        print(f"[MAIN] All batches processed. Total rows processed: {total_rows}")
    else:
        print(f"[MAIN] Loading CSV in chunks...")
        chunk_list = []
        for i, chunk in enumerate(load_inventory_csv(today_path, chunksize=chunksize)):
            print(f"[MAIN] Loaded CSV chunk {i+1}, rows: {len(chunk)}")
            chunk_list.append(chunk)
        all_today = pd.concat(chunk_list, ignore_index=True)
        print(f"[MAIN] All CSV chunks concatenated. Shape: {all_today.shape}")
        print(f"[MAIN] Deduplicating today's data by VIN (latest status_date)...")
        all_today = deduplicate_by_vin(all_today)
        print(f"[MAIN] Deduplication complete. Shape: {all_today.shape}")
        print(f"[MAIN] Merging today's data with main record (vectorized)...")
        all_today = all_today.set_index('vin', drop=False)
        combined = pd.concat([main_df, all_today], axis=0)
        combined['status_date'] = pd.to_datetime(combined['status_date'], errors='coerce')
        combined = combined.reset_index(drop=True)
        print(f"[MAIN] Reset index before sorting/merge. Shape: {combined.shape}")
        combined = combined.sort_values(['vin', 'status_date'], ascending=[True, False])
        combined = combined.drop_duplicates('vin', keep='first')
        main_df = combined
        print(f"[MAIN] Merge complete. Combined shape: {main_df.shape}")
    t4 = time.time()
    save_main_record(main_df)
    print(f"[MAIN] Update complete. Time breakdown (s): load_main={t1-t0:.2f}, process={t4-t1:.2f}, save={time.time()-t4:.2f}")
    return main_df 